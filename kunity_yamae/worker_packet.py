"""Compile a narrow Unity work order into one worker prompt without an LLM."""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .mobile_knowledge import retrieve_mobile_knowledge
from .mobile_routing import route_mobile_task
from .risk import RiskClassifier
from .worker_context import (
    digest,
    focused_editor_report,
    project_file,
    project_versions,
    read_bytes,
    read_slices,
)
from .worker_guidance import OBJECT_FIELDS, RECIPES, WORKER_PREFIX
from .worker_operations import plan_local_operation


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def render_worker_prompt(packet: dict[str, Any]) -> str:
    if packet.get("status") != "prepared":
        raise ValueError("only prepared packets can be sent to workers")
    return packet["prefix"] + "\nTASK_DATA\n" + compact_json(packet["payload"])


def _strings(value: object, field: str, maximum: int = 12) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{field} requires 1..{maximum} strings")
    if any(not isinstance(s, str) or not s.strip() or len(s) > 1000 for s in value):
        raise ValueError(f"{field} contains an invalid string")
    return list(dict.fromkeys(value))


def prepare_worker_packet(
    project_path: Path, request: dict[str, Any], config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A readiness gate, not a model runner or permission to mutate Unity."""
    config = config or {}
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    kind, task = request.get("kind"), request.get("task")
    if (not isinstance(kind, str) or kind not in RECIPES or not isinstance(task, str)
            or not task.strip() or len(task) > 3000):
        raise ValueError("valid kind and bounded task are required")
    acceptance = _strings(request.get("acceptance"), "acceptance")
    targets = _strings(request.get("write_paths"), "write_paths", 4)
    package_ids = request.get("package_ids", [])
    if not isinstance(package_ids, list) or len(package_ids) > 12 or any(
        not isinstance(p, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,100}", p)
        for p in package_ids
    ):
        raise ValueError("package_ids must contain bounded package identifiers")
    limit = config.get("efficiency", {}).get("max_prompt_bytes", 16000)
    if type(limit) is not int or not 1024 <= limit <= 128000:
        raise ValueError("max_prompt_bytes must be an integer between 1024 and 128000")
    # Routing scans no files; the existing classifier currently uses task/diff semantics.
    risk = RiskClassifier(config).classify(task + " " + " ".join(targets), {})
    route = route_mobile_task(task + " " + " ".join(targets), risk_score=risk["risk_score"],
                              failure_count=request.get("failure_count", 0))
    result = {"schema": "unity-harness.worker-packet.v1", "status": "needs_context",
              "route": route.to_dict(), "model_called": False, "applied": False,
              "unity_verified": False, "missing": []}
    if route.role in {"architect", "human"}:
        result["status"] = "escalated"
        return result
    try:
        if kind in {"prefab_bind", "ui_create"} and len(targets) != 1:
            raise ValueError("one asset per deterministic operation")
        for path in targets:
            resolved = project_file(project_path, path)
            parts = PurePosixPath(path).parts
            suffixes = {".cs"} if kind in {"code_patch", "async_patch"} else {".prefab", ".unity"}
            if (not parts or parts[0] not in {"Assets", "Packages"}
                    or resolved.suffix not in suffixes):
                raise ValueError("write scope is not supported by this recipe")
        snippets, hashes = read_slices(project_path, request.get("slices", []))
        versions, version_hashes = project_versions(project_path, package_ids)
        hashes.update(version_hashes)
        missing = result["missing"]
        if not versions["unity"]:
            missing.append("observed Unity version")
        if kind in {"code_patch", "async_patch"}:
            missing.extend(f"source range for {path}" for path in targets if path not in hashes)
        if kind == "async_patch" and request.get("lifetime") not in (
            "destroy", "disable", "pool", "session"
        ):
            missing.append("cancellation lifetime: destroy/disable/pool/session")
        for name, details in versions["packages"].items():
            if details["resolution"] == "unknown" and not any(
                row["path"].startswith(f"Packages/{name}/") for row in snippets
            ):
                missing.append(f"resolved version or installed source excerpt for {name}")
        editor = None
        if kind in {"prefab_bind", "ui_create"}:
            editor, editor_hashes = focused_editor_report(project_path, targets)
            hashes.update(editor_hashes)
            for path in targets:
                hashes[path] = digest(read_bytes(project_path, path))
            contract = request.get("object_contract", {})
            if not isinstance(contract, dict):
                raise ValueError("object_contract must be an object")
            missing.extend(f"object_contract.{field}" for field in OBJECT_FIELDS[kind]
                           if not isinstance(contract.get(field), str)
                           or not contract[field].strip())
            if kind == "prefab_bind" and "expected_old_value" not in contract:
                missing.append("object_contract.expected_old_value")
            if kind == "ui_create" and contract.get("ui_system") not in ("ugui", "uitoolkit"):
                missing.append("object_contract.ui_system must be ugui or uitoolkit")
            for path in targets:
                hashes[path + ".meta"] = digest(read_bytes(project_path, path + ".meta"))
            if kind == "ui_create" and isinstance(contract.get("template_asset"), str):
                template = contract["template_asset"]
                if (not template.startswith(("Assets/", "Packages/"))
                        or PurePosixPath(template).suffix not in {".prefab", ".uxml"}):
                    raise ValueError("UI template must be a project asset")
                hashes[template] = digest(read_bytes(project_path, template))
                hashes[template + ".meta"] = digest(read_bytes(project_path, template + ".meta"))
        if missing:
            return result
    except (OSError, UnicodeError, ValueError) as exc:
        # Do not echo file contents or absolute paths into a prompt or telemetry.
        result["missing"].append(
            f"bounded source/Editor evidence unavailable ({type(exc).__name__})")
        return result
    if kind in {"prefab_bind", "ui_create"}:
        if len(compact_json(contract).encode("utf-8")) > 4000:
            result["missing"].append("object_contract exceeds 4000 UTF-8 bytes")
            return result
        return plan_local_operation(
            kind, targets[0], contract, hashes, editor, result, task=task, acceptance=acceptance)
    query = task + " " + " ".join(package_ids)
    cards = retrieve_mobile_knowledge(query, top_k=2)
    knowledge = [{key: card[key] for key in
                  ("id", "version_scope", "stale", "sources", "local_policy")} for card in cards]
    payload = {"task": task, "kind": kind, "acceptance": acceptance, "write_paths": targets,
               "versions": versions, "sources": snippets, "base_sha256": hashes,
               "recipe": RECIPES[kind], "knowledge": knowledge,
               "lifetime": request.get("lifetime"), "editor_excerpt": editor,
               "object_contract": request.get("object_contract"),
               "verification_policy": "planned only; host guards and real Unity evidence required"}
    if len(compact_json(payload.get("object_contract")).encode()) > 4000:
        result["missing"].append("object_contract exceeds 4000 UTF-8 bytes; narrow the work order")
        return result
    result.update(status="prepared", prefix=WORKER_PREFIX, payload=payload)
    rendered = render_worker_prompt(result)
    size = len(rendered.encode("utf-8"))
    if size > limit:
        # Never truncate a required code range, acceptance criterion or safety condition.
        return {**{k: v for k, v in result.items() if k not in {"prefix", "payload"}},
                "status": "needs_context", "missing": ["split task or narrow explicit ranges"],
                "budget": {"prompt_bytes": size, "limit_bytes": limit, "truncated": False}}
    result["budget"] = {"prompt_bytes": size, "limit_bytes": limit, "truncated": False,
                        "token_count": None, "token_count_kind": "not_measured"}
    result["prefix_sha256"] = digest(WORKER_PREFIX.encode("utf-8"))
    return result


def check_packet_freshness(project_path: Path, packet: dict[str, Any]) -> list[str]:
    """Recheck *all* observed inputs just before guarded application or re-planning."""
    if packet.get("status") not in {"prepared", "planned_local"}:
        raise ValueError("packet is not prepared or planned locally")
    stale = []
    for path, expected in packet["payload"]["base_sha256"].items():
        try:
            current = digest(read_bytes(project_path, path))
        except FileNotFoundError:
            current = None
        except (OSError, ValueError):
            # An unreadable or newly symlinked path is not the same as an absent file.
            stale.append(path)
            continue
        if current != expected:
            stale.append(path)
    return stale
