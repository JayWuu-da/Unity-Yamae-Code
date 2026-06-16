from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def evaluate_quality_gate(
    results: Sequence[Mapping[str, Any]],
    *,
    required_tiers: tuple[str, ...] = ("compile",),
    mode: str = "standard",
    evidence_claims: tuple[str, ...] = (),
) -> dict[str, Any]:
    required_tiers = _required_tiers(required_tiers, mode, evidence_claims)
    if not required_tiers:
        return _result("passed", True, [], [])
    if _is_dry_run_only(results):
        return _result("unavailable", False, [], ["verification was planned but not executed"])
    passed_names = {
        _canonical_tier(str(row.get("name")))
        for row in results
        if row.get("passed") is True
    }
    missing = [tier for tier in required_tiers if tier not in passed_names]
    failed = [
        str(row.get("name"))
        for row in results
        if row.get("passed") is False or str(row.get("status", "")).lower() in {"failed", "error"}
    ]
    if missing or failed:
        return _result("failed", False, missing, failed)
    return _result("passed", True, [], [])


def _is_dry_run_only(results: Sequence[Mapping[str, Any]]) -> bool:
    return bool(results) and all(
        row.get("passed") is not True
        and str(row.get("status", "")).lower() in {"planned", "dry_run", "not_run"}
        for row in results
    )


def _required_tiers(
    explicit: tuple[str, ...],
    mode: str,
    evidence_claims: tuple[str, ...],
) -> tuple[str, ...]:
    required = [] if mode == "static_only" else list(explicit)
    if mode in {"release", "migration"}:
        required.extend(["compile", "editmode", "playmode", "build"])
    if mode in {"asset_safe"}:
        required.append("compile")
    claim_map = {
        "inspector": "editor_probe",
        "prefab": "editor_probe",
        "scene": "editor_probe",
        "player": "player_live",
        "player_live": "player_live",
    }
    required.extend(claim_map[claim] for claim in evidence_claims if claim in claim_map)
    return tuple(dict.fromkeys(required))


def _canonical_tier(name: str) -> str:
    lowered = name.lower().replace("_", "-")
    if lowered in {"compile/import", "compile-import", "compile"}:
        return "compile"
    if "editmode" in lowered:
        return "editmode"
    if "playmode" in lowered:
        return "playmode"
    if "build" in lowered:
        return "build"
    if lowered in {"editor-probe", "editor probe", "inspect", "editor-inspect"}:
        return "editor_probe"
    return name


def _result(
    status: str,
    passed: bool,
    missing_required_tiers: list[str],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "schema": "unity-harness.quality-gate-result.v1",
        "status": status,
        "passed": passed,
        "missing_required_tiers": missing_required_tiers,
        "errors": errors,
    }
