from __future__ import annotations

from pathlib import Path
from typing import Any

from .context import ContextSelector
from .memory_store import HarnessMemoryStore
from .project_files import ProjectFileInventory
from .risk import RiskClassifier
from .scanner import UnityProjectScanner
from .tool_registry import (
    ToolRegistry,
    ToolSpec,
    completed_tool_result,
    unavailable_tool_result,
    unavailable_tool_result_with_payload,
)
from .unity_adapters import EditorAdapter, PlayerAdapter, default_player_adapter_config
from .verifier import UnityVerifier


def build_default_tool_registry(config: dict[str, Any], project_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    for spec, handler in (
        (
            _spec("harness.risk.classify", "Classify Unity task risk.", "read", "static_scan"),
            _risk(config, project_path),
        ),
        (
            _spec("unity.verify.plan", "Plan Unity verification commands.", "plan", "planned"),
            _verify(config, project_path),
        ),
        (
            _spec(
                "unity.inspect.static",
                "Inspect static Unity project facts.",
                "read",
                "static_scan",
            ),
            _inspect(config, project_path),
        ),
        (
            _spec(
                "unity.inspect.editor_probe.plan",
                "Plan an editor probe without running Unity.",
                "plan",
                "planned",
                adapter_scope="editor",
            ),
            _editor_probe_plan(project_path),
        ),
        (
            _spec(
                "repo.patch.evaluate",
                "Plan guarded patch evaluation handoff.",
                "plan",
                "guarded",
            ),
            _patch_evaluate,
        ),
        (
            _spec(
                "harness.context.select",
                "Plan context selection for a task.",
                "read",
                "static_scan",
            ),
            _context_select(config, project_path),
        ),
        (
            _spec(
                "harness.memory.record",
                "Report local harness memory adapter availability.",
                "plan",
                "unavailable",
                lifecycle="available",
            ),
            _memory_record(project_path),
        ),
        (
            _spec(
                "unity.player.status",
                "Report dev-build Player adapter availability.",
                "read",
                "unavailable",
                adapter_scope="player",
                lifecycle="available",
            ),
            _player_status(config, project_path),
        ),
    ):
        registry.register(spec, handler)
    return registry


def _spec(
    name: str,
    description: str,
    permission: str,
    evidence_tier: str,
    *,
    adapter_scope: str = "harness",
    lifecycle: str = "available",
) -> ToolSpec:
    return ToolSpec(
        name=name,
        version="1",
        description=description,
        input_contract="unity-harness.tool-input.v1",
        output_contract="unity-harness.tool-call-result.v1",
        permission=permission,
        side_effect_level="none",
        timeout_ms=30_000,
        evidence_tier=evidence_tier,
        guard_required=name == "repo.patch.evaluate",
        handler_kind="local",
        capability_tags=tuple(name.split(".")[:2]),
        lifecycle=lifecycle,
        adapter_scope=adapter_scope,
    )


def _risk(config: dict[str, Any], project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        task = str(payload.get("task", ""))
        profile = UnityProjectScanner(project_path, config).scan()
        risk_report = RiskClassifier(config).classify(task, profile)
        return completed_tool_result("harness.risk.classify", "static_scan", risk_report)

    return handler


def _verify(config: dict[str, Any], project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        commands = UnityVerifier(project_path, config).plan(
            compile_check=bool(payload.get("compile_check", True)),
            editmode_tests=bool(payload.get("editmode_tests", False)),
            playmode_tests=bool(payload.get("playmode_tests", False)),
            build_target=payload.get("build_target"),
            custom_method=payload.get("custom_method"),
        )
        return completed_tool_result("unity.verify.plan", "planned", {"commands": commands})

    return handler


def _inspect(config: dict[str, Any], project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        deep = bool(payload.get("deep", False))
        profile = UnityProjectScanner(project_path, config).scan(deep=deep)
        return completed_tool_result("unity.inspect.static", "static_scan", {"profile": profile})

    return handler


def _editor_probe_plan(project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        method = str(payload.get("method", "KUnityYamae.EditorInspectionProbe.Run"))
        adapter_result = EditorAdapter(project_path).plan_probe(method)
        return completed_tool_result(
            "unity.inspect.editor_probe.plan",
            "planned",
            adapter_result,
        )

    return handler


def _patch_evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    patch_file = payload.get("patch_file")
    return completed_tool_result(
        "repo.patch.evaluate",
        "guarded",
        {"patch_file": patch_file, "status": "planned", "applied": False},
    )


def _context_select(config: dict[str, Any], project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        task = str(payload.get("task", ""))
        profile = UnityProjectScanner(project_path, config).scan(deep=True)
        inventory = ProjectFileInventory.collect(project_path)
        risk_report = RiskClassifier(config).classify(task, profile)
        context = ContextSelector(project_path, config).select(
            task,
            risk_report,
            risk_report["mode"],
        )
        if not context["relevant_files"]:
            _add_matching_scripts(context, task, inventory)
        context["schema"] = "unity-harness.context-pack.v1"
        return completed_tool_result(
            "harness.context.select",
            "static_scan",
            context,
        )

    return handler


def _add_matching_scripts(
    context: dict[str, Any],
    task: str,
    inventory: ProjectFileInventory,
) -> None:
    task_words = _search_words(task)
    for script in inventory.scripts:
        relative_path = inventory.relative_path(script)
        if not (task_words & _search_words(script.stem)):
            continue
        content = script.read_text(encoding="utf-8")
        context["relevant_files"].append(relative_path)
        context["summaries"].append(
            {
                "path": relative_path,
                "type": "csharp",
                "lines": len(content.splitlines()),
                "preview": "\n".join(content.splitlines()[:50]),
            }
        )


def _search_words(text: str) -> set[str]:
    normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
    words = {token for token in normalized.split() if len(token) > 2}
    compact = normalized.replace(" ", "")
    if len(compact) > 2:
        words.add(compact)
    return words


def _memory_record(project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("record"):
            return unavailable_tool_result(
                "harness.memory.record",
                "Memory record adapter is explicit; pass record=true to write session memory.",
            )
        store = HarnessMemoryStore(project_path / ".unity-harness" / "state")
        event = store.record_event(
            run_id=str(payload.get("run_id", "manual-tool-call")),
            event=str(payload.get("event", "tool_result")),
            payload={
                "fact_kind": "tool",
                "source": "static_scan",
                "summary": str(payload.get("summary", "")),
            },
            provenance={"evidence_tier": "static_scan", "tool": "harness.memory.record"},
            dedupe_key=payload.get("dedupe_key"),
        )
        return completed_tool_result("harness.memory.record", "static_scan", event)

    return handler


def _player_status(config: dict[str, Any], project_path: Path):
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        adapter_config = default_player_adapter_config() | dict(config.get("player_adapter", {}))
        adapter_result = PlayerAdapter(project_path, adapter_config).status()
        return unavailable_tool_result_with_payload(
            "unity.player.status",
            adapter_result,
            "Player adapter is dev-build-only and is unavailable until explicitly implemented.",
        )

    return handler
