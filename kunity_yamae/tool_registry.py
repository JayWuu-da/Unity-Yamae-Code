from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .contracts import (
    validate_tool_call_result_v1,
    validate_tool_call_result_v2,
    validate_tool_spec_v1,
    validate_tool_spec_v2,
)

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    version: str
    description: str
    input_contract: str
    output_contract: str
    permission: str
    side_effect_level: str
    timeout_ms: int
    evidence_tier: str
    guard_required: bool
    handler_kind: str
    capability_tags: tuple[str, ...]
    lifecycle: str = "available"
    dry_run_supported: bool = True
    adapter_scope: str = "harness"
    failure_modes: tuple[str, ...] = ()
    observability_events: tuple[str, ...] = ("tool.started", "tool.completed")

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "unity-harness.tool-spec.v1",
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "permission": self.permission,
            "side_effect_level": self.side_effect_level,
            "timeout_ms": self.timeout_ms,
            "evidence_tier": self.evidence_tier,
            "guard_required": self.guard_required,
            "handler_kind": self.handler_kind,
            "capability_tags": list(self.capability_tags),
        }
        return validate_tool_spec_v1(payload)

    def to_payload_v2(self) -> dict[str, Any]:
        payload = self.to_payload() | {
            "schema": "unity-harness.tool-spec.v2",
            "lifecycle": self.lifecycle,
            "dry_run_supported": self.dry_run_supported,
            "adapter_scope": self.adapter_scope,
            "failure_modes": list(self.failure_modes),
            "observability_events": list(self.observability_events),
        }
        return validate_tool_spec_v2(payload)


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise KeyError(f"duplicate tool: {spec.name}")
        validate_tool_spec_v1(spec.to_payload())
        self._tools[spec.name] = RegisteredTool(spec=spec, handler=handler)

    def get(self, name: str) -> RegisteredTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def list_payload(self, schema_version: str = "v1") -> dict[str, Any]:
        if schema_version == "v2":
            return {
                "schema": "unity-harness.tool-registry.v2",
                "tools": [self._tools[name].spec.to_payload_v2() for name in sorted(self._tools)],
            }
        return {
            "schema": "unity-harness.tool-registry.v1",
            "tools": [self._tools[name].spec.to_payload() for name in sorted(self._tools)],
        }

    def call(
        self,
        name: str,
        payload: dict[str, Any],
        schema_version: str = "v1",
    ) -> dict[str, Any]:
        tool = self.get(name)
        try:
            result = tool.handler(payload)
        except KeyError as exc:
            result = failed_tool_result(name, tool.spec.evidence_tier, str(exc))
        if schema_version == "v2":
            return _to_v2_result(tool.spec, result)
        return validate_tool_call_result_v1(result)


def completed_tool_result(name: str, evidence_tier: str, result: dict[str, Any]) -> dict[str, Any]:
    return validate_tool_call_result_v1(
        {
            "schema": "unity-harness.tool-call-result.v1",
            "tool": name,
            "status": "completed",
            "evidence_tier": evidence_tier,
            "result": result,
            "errors": [],
        }
    )


def failed_tool_result(name: str, evidence_tier: str, message: str) -> dict[str, Any]:
    return validate_tool_call_result_v1(
        {
            "schema": "unity-harness.tool-call-result.v1",
            "tool": name,
            "status": "failed",
            "evidence_tier": evidence_tier,
            "result": {},
            "errors": [message],
        }
    )


def unavailable_tool_result(name: str, message: str) -> dict[str, Any]:
    return validate_tool_call_result_v1(
        {
            "schema": "unity-harness.tool-call-result.v1",
            "tool": name,
            "status": "unavailable",
            "evidence_tier": "unavailable",
            "result": {},
            "errors": [message],
        }
    )


def unavailable_tool_result_with_payload(
    name: str,
    result: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    return validate_tool_call_result_v1(
        {
            "schema": "unity-harness.tool-call-result.v1",
            "tool": name,
            "status": "unavailable",
            "evidence_tier": "unavailable",
            "result": result,
            "errors": [message],
        }
    )


def failed_tool_result_v2(name: str, permission: str, message: str) -> dict[str, Any]:
    return validate_tool_call_result_v2(
        {
            "schema": "unity-harness.tool-call-result.v2",
            "tool": name,
            "status": "failed",
            "permission": permission,
            "permission_outcome": "refused",
            "evidence_tier": "unavailable",
            "observability_events": ["tool.started", "tool.failed"],
            "result": {},
            "errors": [message],
        }
    )


def _to_v2_result(spec: ToolSpec, result: dict[str, Any]) -> dict[str, Any]:
    status = str(result.get("status", "failed"))
    if status == "completed":
        outcome = "allowed"
    elif status == "unavailable":
        outcome = "unavailable"
    else:
        outcome = "refused"
    events = ["tool.started", f"tool.{status}"]
    return validate_tool_call_result_v2(
        {
            "schema": "unity-harness.tool-call-result.v2",
            "tool": spec.name,
            "status": status,
            "permission": spec.permission,
            "permission_outcome": outcome,
            "evidence_tier": result.get("evidence_tier", spec.evidence_tier),
            "observability_events": events,
            "result": result.get("result", {}),
            "errors": result.get("errors", []),
        }
    )
