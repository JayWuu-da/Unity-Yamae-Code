from typing import Any

from . import contracts_v2 as _contracts_v2
from .contract_errors import ContractError

validate_episodic_memory_summary_v1 = _contracts_v2.validate_episodic_memory_summary_v1
validate_memory_event_v2 = _contracts_v2.validate_memory_event_v2
validate_metrics_summary_v1 = _contracts_v2.validate_metrics_summary_v1
validate_orchestration_run_v2 = _contracts_v2.validate_orchestration_run_v2
validate_tool_call_result_v2 = _contracts_v2.validate_tool_call_result_v2
validate_tool_registry_v2 = _contracts_v2.validate_tool_registry_v2
validate_tool_spec_v2 = _contracts_v2.validate_tool_spec_v2
validate_trace_event_v1 = _contracts_v2.validate_trace_event_v1
validate_unity_adapter_result_v2 = _contracts_v2.validate_unity_adapter_result_v2

VALID_EVIDENCE_TIERS = {"planned", "static_scan", "guarded", "unavailable"}
VALID_PERMISSIONS = {"read", "plan", "write_code", "write_assets", "run_unity", "player_debug"}
VALID_SIDE_EFFECTS = {"none", "low", "medium", "high"}
VALID_TOOL_STATUSES = {"completed", "failed", "unavailable"}
TOOL_SPEC_TEXT_FIELDS = (
    "name",
    "version",
    "description",
    "input_contract",
    "output_contract",
    "handler_kind",
)
PLAN_MAPPING_FIELDS = (
    "risk_report",
    "patch_handoff",
    "verification_profile",
    "memory_policy",
    "observability",
)


def validate_integration_doctor_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(
        payload.get("schema") == "unity-harness.desktop-integration-doctor.v1",
        "schema",
    )
    integrations = _require_dict(payload, "integrations")
    for name, integration_value in integrations.items():
        integration = _require_mapping(integration_value, f"integrations.{name}")
        for field in (
            "kind",
            "entrypoint",
            "status",
        ):
            _require(field in integration, f"integrations.{name}.{field}")
    offline_handoffs = _require_dict(payload, "offline_handoffs")
    for name, handoff_value in offline_handoffs.items():
        handoff = _require_mapping(handoff_value, f"offline_handoffs.{name}")
        for field in ("status", "usage"):
            _require(field in handoff, f"offline_handoffs.{name}.{field}")
    return payload


def validate_run_result_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.run-result.v1", "schema")
    _require(payload.get("status") in {"planned", "completed", "failed"}, "status")
    _require(isinstance(payload.get("plan_only"), bool), "plan_only")
    _require(isinstance(payload.get("provider_requests"), int), "provider_requests")
    _require(isinstance(payload.get("stages"), list), "stages")
    return payload


def validate_tool_spec_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.tool-spec.v1", "schema")
    for field in TOOL_SPEC_TEXT_FIELDS:
        _require(isinstance(payload.get(field), str) and payload[field], field)
    _require(payload.get("permission") in VALID_PERMISSIONS, "permission")
    _require(payload.get("side_effect_level") in VALID_SIDE_EFFECTS, "side_effect_level")
    _require(isinstance(payload.get("timeout_ms"), int), "timeout_ms")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS, "evidence_tier")
    _require(isinstance(payload.get("guard_required"), bool), "guard_required")
    _require(isinstance(payload.get("capability_tags"), list), "capability_tags")
    return payload


def validate_tool_registry_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.tool-registry.v1", "schema")
    tools = _require_list(payload, "tools")
    for index, tool in enumerate(tools):
        validate_tool_spec_v1(_require_mapping(tool, f"tools.{index}"))
    return payload


def validate_tool_call_result_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.tool-call-result.v1", "schema")
    _require(isinstance(payload.get("tool"), str) and payload["tool"], "tool")
    _require(payload.get("status") in VALID_TOOL_STATUSES, "status")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS, "evidence_tier")
    _require("result" in payload, "result")
    _require(isinstance(payload.get("errors"), list), "errors")
    return payload


def validate_orchestration_plan_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.orchestration-plan.v1", "schema")
    _require(payload.get("status") == "planned", "status")
    _require(isinstance(payload.get("task"), str) and payload["task"], "task")
    for field in PLAN_MAPPING_FIELDS:
        _require_mapping(payload.get(field), field)
    _require(isinstance(payload.get("mode"), str) and payload["mode"], "mode")
    tool_plan = _require_list(payload, "tool_plan")
    for index, row_value in enumerate(tool_plan):
        row = _require_mapping(row_value, f"tool_plan.{index}")
        _require(isinstance(row.get("tool"), str) and row["tool"], f"tool_plan.{index}.tool")
        _require(
            row.get("status") in VALID_TOOL_STATUSES,
            f"tool_plan.{index}.status",
        )
        _require_mapping(row.get("input"), f"tool_plan.{index}.input")
        _require(
            row.get("evidence_tier") in VALID_EVIDENCE_TIERS,
            f"tool_plan.{index}.evidence_tier",
        )
        validate_tool_call_result_v1(
            _require_mapping(row.get("result"), f"tool_plan.{index}.result")
        )
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS, "evidence_tier")
    return payload


def validate_memory_event_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.memory-event.v1", "schema")
    _require(isinstance(payload.get("event"), str) and payload["event"], "event")
    _require_mapping(payload.get("payload"), "payload")
    return payload


def validate_unity_adapter_result_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.unity-adapter-result.v1", "schema")
    _require(isinstance(payload.get("adapter"), str) and payload["adapter"], "adapter")
    _require(payload.get("status") in VALID_TOOL_STATUSES, "status")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS, "evidence_tier")
    _require_mapping(payload.get("facts"), "facts")
    _require(isinstance(payload.get("errors"), list), "errors")
    return payload


def _require_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    return _require_mapping(value, field)


def _require_list(payload: dict[str, Any], field: str) -> list[Any]:
    value = _field_value(payload, field)
    if isinstance(value, list):
        return value
    raise ContractError(field)


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ContractError(field)


def _require(condition: bool, field: str) -> None:
    if not condition:
        raise ContractError(field)


def _field_value(payload: dict[str, Any], field: str) -> Any:
    if "." not in field:
        return payload.get(field)
    return payload.get(field.rsplit(".", 1)[-1])
