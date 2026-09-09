"""Mobile and efficiency tools kept outside the core catalog's size boundary."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .mobile_knowledge import build_mobile_context
from .mobile_routing import route_mobile_task
from .risk import RiskClassifier
from .tool_registry import ToolRegistry, ToolSpec, completed_tool_result, failed_tool_result
from .worker_packet import prepare_worker_packet


def register_mobile_tools(registry: ToolRegistry, config: dict[str, Any], root: Path) -> None:
    def route(payload: dict[str, Any]) -> dict[str, Any]:
        task = str(payload.get("task", ""))
        risk = RiskClassifier(config).classify(task, {})
        selected = route_mobile_task(task, risk_score=risk["risk_score"],
                                     failure_count=payload.get("failure_count", 0))
        return {**selected.to_dict(), "risk_report": risk}

    def knowledge(payload: dict[str, Any]) -> dict[str, Any]:
        return build_mobile_context(str(payload.get("query") or payload.get("task") or ""),
                                    top_k=payload.get("top_k", 4))

    def prepare(payload: dict[str, Any]) -> dict[str, Any]:
        return prepare_worker_packet(root, payload, config)

    for name, description, handler in (
        ("harness.mobile.route", "Route a task without a redundant project scan.", route),
        ("harness.mobile.knowledge", "Retrieve relevant source-backed SDK guidance.", knowledge),
        ("harness.worker.prepare", "Compile explicit source ranges into a bounded Unity handoff.",
         prepare),
    ):
        spec = ToolSpec(name=name, version="1", description=description,
                        input_contract="unity-harness.tool-input.v1",
                        output_contract="unity-harness.tool-call-result.v1", permission="read",
                        side_effect_level="none", timeout_ms=30000, evidence_tier="static_scan",
                        guard_required=False, handler_kind="local", capability_tags=("harness",))
        registry.register(spec, _wrap(name, handler))


def _wrap(name, handler):
    def call(payload):
        try:
            value = handler(payload)
        except (ValueError, TypeError) as exc:
            return failed_tool_result(name, "static_scan", str(exc))
        return completed_tool_result(name, "static_scan", value)
    return call
