from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_orchestration_plan_v1, validate_orchestration_run_v2
from .memory_store import HarnessMemoryStore
from .modes import select_mode
from .observability import JsonlTraceSink
from .tool_catalog import build_default_tool_registry


def build_orchestration_plan(
    project_path: Path,
    config: dict[str, Any],
    task: str,
    *,
    verify_dry_run: bool,
    editor_probe: bool = False,
) -> dict[str, Any]:
    registry = build_default_tool_registry(config, project_path)
    risk_input: dict[str, Any] = {"task": task}
    context_input: dict[str, Any] = {"task": task}
    verify_input: dict[str, Any] = {
        "compile_check": True,
        "editmode_tests": False,
        "playmode_tests": False,
        "custom_method": _probe_method(editor_probe),
    }
    memory_input: dict[str, Any] = {"task": task, "record": False}
    player_input: dict[str, Any] = {"task": task}
    risk_result = registry.call("harness.risk.classify", risk_input)
    context_result = registry.call("harness.context.select", context_input)
    verify_result = registry.call("unity.verify.plan", verify_input)
    memory_result = registry.call("harness.memory.record", memory_input)
    player_result = registry.call("unity.player.status", player_input)
    risk_report = risk_result["result"]
    selected_mode = select_mode(risk_report["risk_score"], config)
    verify_commands = verify_result["result"]["commands"] if verify_dry_run else []
    payload = {
        "schema": "unity-harness.orchestration-plan.v1",
        "status": "planned",
        "task": task,
        "risk_report": risk_report,
        "mode": selected_mode,
        "tool_plan": [
            _tool_plan_row("harness.risk.classify", risk_input, risk_result),
            _tool_plan_row("harness.context.select", context_input, context_result),
            _tool_plan_row("unity.verify.plan", verify_input, verify_result),
            _tool_plan_row("harness.memory.record", memory_input, memory_result),
            _tool_plan_row("unity.player.status", player_input, player_result),
        ],
        "patch_handoff": {
            "required": risk_report["risk_score"] > 0,
            "mutating_backend": "local-patch",
            "guarded_patch_required": True,
            "applied": False,
        },
        "verification_profile": {
            "dry_run": verify_dry_run,
            "editor_probe_planned": editor_probe,
            "unity_editor_verified": False,
            "commands": verify_commands,
        },
        "memory_policy": {"enabled": False, "store": ".unity-harness/state"},
        "observability": {"trace": ".unity-harness/traces/events.jsonl"},
        "evidence_tier": "planned",
    }
    return validate_orchestration_plan_v1(payload)


def run_orchestration_loop_v2(
    project_path: Path,
    config: dict[str, Any],
    task: str,
    *,
    verify_dry_run: bool,
    editor_probe: bool = False,
) -> dict[str, Any]:
    run_id = f"run-{uuid.uuid4().hex}"
    trace_id = f"trace-{uuid.uuid4().hex}"
    started = _utc_now()
    started_ticks = time.monotonic()
    registry = build_default_tool_registry(config, project_path)
    trace = JsonlTraceSink(project_path / ".unity-harness" / "traces")
    steps: list[dict[str, Any]] = []

    risk_input: dict[str, Any] = {"task": task}
    context_input: dict[str, Any] = {"task": task}
    verify_input: dict[str, Any] = {
        "compile_check": True,
        "editmode_tests": False,
        "playmode_tests": False,
        "custom_method": _probe_method(editor_probe),
    }
    editor_input: dict[str, Any] = {"method": _probe_method(True)}
    player_input: dict[str, Any] = {"task": task}

    for tool_name, tool_input, depends_on in (
        ("harness.risk.classify", risk_input, ()),
        ("harness.context.select", context_input, ("harness.risk.classify",)),
        ("unity.verify.plan", verify_input, ("harness.risk.classify",)),
        ("unity.inspect.editor_probe.plan", editor_input, ("unity.verify.plan",)),
        ("unity.player.status", player_input, ()),
    ):
        steps.append(
            _run_step_v2(
                registry,
                trace,
                run_id,
                trace_id,
                tool_name,
                tool_input,
                depends_on=depends_on,
            )
        )

    memory_input: dict[str, Any] = {
        "record": True,
        "run_id": run_id,
        "event": "orchestration_run",
        "summary": f"Non-mutating v2 orchestration loop for: {task}",
        "dedupe_key": run_id,
    }
    steps.append(
        _run_step_v2(
            registry,
            trace,
            run_id,
            trace_id,
            "harness.memory.record",
            memory_input,
            depends_on=tuple(step["tool"] for step in steps),
        )
    )
    metrics = trace.write_metrics_summary(run_id)
    summary = HarnessMemoryStore(project_path / ".unity-harness" / "state").write_episodic_summary(
        run_id,
        f"Executed {len(steps)} non-mutating v2 tool steps.",
    )
    payload = {
        "schema": "unity-harness.orchestration-run.v2",
        "run_id": run_id,
        "task": task,
        "status": "completed",
        "started_at": started,
        "completed_at": _utc_now(),
        "duration_ms": int((time.monotonic() - started_ticks) * 1000),
        "steps": steps,
        "artifacts": {
            "trace_events": ".unity-harness/traces/events.jsonl",
            "metrics_summary": ".unity-harness/traces/metrics-summary.json",
            "memory_summary": ".unity-harness/state/episodic-summary.json",
        },
        "metrics": metrics,
        "memory_summary": summary,
        "non_mutating": True,
        "verify_dry_run": verify_dry_run,
    }
    return validate_orchestration_run_v2(payload)


def _probe_method(editor_probe: bool) -> str | None:
    if editor_probe:
        return "KUnityYamae.EditorInspectionProbe.Run"
    return None


def _tool_plan_row(
    tool_name: str,
    tool_input: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "status": result["status"],
        "input": tool_input,
        "evidence_tier": result["evidence_tier"],
        "result": result,
    }


def _run_step_v2(
    registry,
    trace: JsonlTraceSink,
    run_id: str,
    trace_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    depends_on: tuple[str, ...],
) -> dict[str, Any]:
    started = _utc_now()
    started_ticks = time.monotonic()
    result = registry.call(tool_name, tool_input, "v2")
    duration_ms = int((time.monotonic() - started_ticks) * 1000)
    span_id = f"span-{uuid.uuid4().hex}"
    trace.record_tool_event(
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=None,
        event=f"tool.{result['status']}",
        status=result["status"],
        tool=tool_name,
        duration_ms=duration_ms,
        evidence_tier=result["evidence_tier"],
        attributes={"permission_outcome": result["permission_outcome"]},
    )
    return {
        "id": span_id,
        "tool": tool_name,
        "status": result["status"],
        "depends_on": list(depends_on),
        "started_at": started,
        "completed_at": _utc_now(),
        "duration_ms": duration_ms,
        "permission_outcome": result["permission_outcome"],
        "evidence_tier": result["evidence_tier"],
        "input": tool_input,
        "result": result,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
