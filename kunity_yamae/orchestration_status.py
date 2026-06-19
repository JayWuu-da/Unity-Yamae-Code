from __future__ import annotations

import time
import uuid
from collections.abc import Mapping, Sequence
from typing import TypeAlias

from .observability import JsonlTraceSink
from .tool_registry import ToolRegistry

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | dict[str, "JsonValue"] | list["JsonValue"]


def skipped_step_v2(
    registry: ToolRegistry,
    trace: JsonlTraceSink,
    run_id: str,
    trace_id: str,
    tool_name: str,
    tool_input: dict[str, JsonValue],
    depends_on: tuple[str, ...],
    blocked: list[str],
    started: str,
    started_ticks: float,
    completed_at: str,
) -> dict[str, JsonValue]:
    tool = registry.get(tool_name)
    duration_ms = int((time.monotonic() - started_ticks) * 1000)
    span_id = f"span-{uuid.uuid4().hex}"
    result: dict[str, JsonValue] = {
        "schema": "unity-harness.tool-call-result.v2",
        "tool": tool_name,
        "status": "failed",
        "permission": tool.spec.permission,
        "permission_outcome": "not_requested",
        "evidence_tier": "unavailable",
        "observability_events": ["tool.started", "tool.skipped"],
        "result": {},
        "errors": [f"dependency failed or skipped: {', '.join(blocked)}"],
    }
    _ = trace.record_tool_event(
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=None,
        event="tool.skipped",
        status="skipped",
        tool=tool_name,
        duration_ms=duration_ms,
        evidence_tier="unavailable",
        attributes={"permission_outcome": "not_requested"},
    )
    return {
        "id": span_id,
        "tool": tool_name,
        "status": "skipped",
        "depends_on": list(depends_on),
        "started_at": started,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "permission_outcome": "not_requested",
        "evidence_tier": "unavailable",
        "input": tool_input,
        "result": result,
    }


def aggregate_run_status(steps: Sequence[Mapping[str, JsonValue]]) -> str:
    required_tools = {
        "harness.risk.classify",
        "harness.context.select",
        "unity.verify.plan",
        "unity.inspect.editor_probe.plan",
        "harness.memory.record",
    }
    for step in steps:
        if step["tool"] in required_tools and step["status"] in {"failed", "skipped"}:
            return "failed"
    if any(step["status"] == "unavailable" for step in steps):
        return "completed_with_warnings"
    return "completed"
