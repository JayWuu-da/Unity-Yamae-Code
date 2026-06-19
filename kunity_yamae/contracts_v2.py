from __future__ import annotations

from typing import Any

from .contract_errors import ContractError

VALID_EVIDENCE_TIERS_V2 = {
    "planned",
    "static_scan",
    "guarded",
    "unavailable",
    "editor_probe",
    "compile",
    "editmode",
    "playmode",
    "build",
    "player_live",
}
VALID_PERMISSIONS = {"read", "plan", "write_code", "write_assets", "run_unity", "player_debug"}
VALID_SIDE_EFFECTS = {"none", "low", "medium", "high"}
VALID_TOOL_STATUSES = {"completed", "failed", "unavailable"}
VALID_TOOL_LIFECYCLES = {"available", "planned", "experimental", "deprecated", "unavailable"}
VALID_ADAPTER_SCOPES = {"harness", "project", "editor", "player", "none"}
VALID_PERMISSION_OUTCOMES = {"allowed", "refused", "unavailable", "not_requested"}
VALID_RUN_STATUSES = {
    "planned",
    "running",
    "completed",
    "completed_with_warnings",
    "failed",
    "skipped",
    "unavailable",
}
VALID_EDITOR_OPERATIONS = {"plan", "probe", "verify", "inspect_report"}
VALID_PLAYER_OPERATIONS = {"status", "connect_plan", "request_response"}
TOOL_SPEC_TEXT_FIELDS = (
    "name",
    "version",
    "description",
    "input_contract",
    "output_contract",
    "handler_kind",
)


def validate_tool_spec_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.tool-spec.v2", "schema")
    _require_non_empty_fields(payload, TOOL_SPEC_TEXT_FIELDS)
    _require(payload.get("permission") in VALID_PERMISSIONS, "permission")
    _require(payload.get("side_effect_level") in VALID_SIDE_EFFECTS, "side_effect_level")
    _require_non_negative_int(payload, "timeout_ms")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS_V2, "evidence_tier")
    _require_bool(payload, "guard_required")
    _require_string_list(payload, "capability_tags")
    _require(payload.get("lifecycle") in VALID_TOOL_LIFECYCLES, "lifecycle")
    _require_bool(payload, "dry_run_supported")
    _require(payload.get("adapter_scope") in VALID_ADAPTER_SCOPES, "adapter_scope")
    _require_string_list(payload, "failure_modes")
    _require_string_list(payload, "observability_events")
    return payload


def validate_tool_registry_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.tool-registry.v2", "schema")
    for index, tool in enumerate(_require_list(payload, "tools")):
        validate_tool_spec_v2(_require_mapping(tool, f"tools.{index}"))
    return payload


def validate_tool_call_result_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.tool-call-result.v2", "schema")
    _require_non_empty_str(payload, "tool")
    _require(payload.get("status") in VALID_TOOL_STATUSES, "status")
    _require(payload.get("permission") in VALID_PERMISSIONS, "permission")
    _require(payload.get("permission_outcome") in VALID_PERMISSION_OUTCOMES, "permission_outcome")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS_V2, "evidence_tier")
    _require_string_list(payload, "observability_events")
    _require("result" in payload, "result")
    _require(isinstance(payload.get("errors"), list), "errors")
    return payload


def validate_orchestration_run_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.orchestration-run.v2", "schema")
    for field in ("run_id", "task", "started_at"):
        _require_non_empty_str(payload, field)
    _require(payload.get("status") in VALID_RUN_STATUSES, "status")
    _require_completed_at(payload, "completed_at")
    _require_non_negative_int(payload, "duration_ms")
    for index, step_value in enumerate(_require_list(payload, "steps")):
        step = _require_mapping(step_value, f"steps.{index}")
        prefix = f"steps.{index}"
        _require_non_empty_fields(step, ("id", "tool", "started_at"), prefix)
        _require(step.get("status") in VALID_RUN_STATUSES, f"{prefix}.status")
        _require_string_list(step, f"{prefix}.depends_on")
        _require_completed_at(step, f"{prefix}.completed_at")
        _require_non_negative_int(step, f"{prefix}.duration_ms")
        _require(
            step.get("permission_outcome") in VALID_PERMISSION_OUTCOMES,
            f"{prefix}.permission_outcome",
        )
        _require(step.get("evidence_tier") in VALID_EVIDENCE_TIERS_V2, f"{prefix}.evidence_tier")
        _require_mapping(step.get("input"), f"{prefix}.input")
        validate_tool_call_result_v2(_require_mapping(step.get("result"), f"{prefix}.result"))
    return payload


def validate_trace_event_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.trace-event.v1", "schema")
    _require_non_empty_fields(payload, ("run_id", "trace_id", "span_id", "event", "status"))
    _require(
        payload.get("parent_span_id") is None or isinstance(payload.get("parent_span_id"), str),
        "parent_span_id",
    )
    _require(payload.get("tool") is None or isinstance(payload.get("tool"), str), "tool")
    _require_non_negative_int(payload, "duration_ms")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS_V2, "evidence_tier")
    _require_mapping(payload.get("attributes"), "attributes")
    return payload


def validate_metrics_summary_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.metrics-summary.v1", "schema")
    _require_non_empty_str(payload, "run_id")
    _require_non_negative_int_mapping(payload, "counters")
    _require_non_negative_int_mapping(payload, "durations_ms")
    _require_non_negative_int_mapping(payload, "status_counts")
    return payload


def validate_memory_event_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.memory-event.v2", "schema")
    _require_non_empty_fields(payload, ("run_id", "event", "storage_path", "dedupe_fingerprint"))
    _require_allowed_memory_path(str(payload["storage_path"]), "storage_path")
    memory_payload = _require_mapping(payload.get("payload"), "payload")
    provenance = _require_mapping(payload.get("provenance"), "provenance")
    _require_mapping(payload.get("redaction"), "redaction")
    _require_retention_policy(payload, "retention")
    if memory_payload.get("fact_kind") == "unity" and memory_payload.get("source") == "inferred":
        _require(bool(provenance), "provenance")
    return payload


def validate_episodic_memory_summary_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.episodic-memory-summary.v1", "schema")
    _require_non_empty_fields(payload, ("run_id", "storage_path", "summary"))
    _require_allowed_memory_path(str(payload["storage_path"]), "storage_path")
    _require_non_negative_int(payload, "event_count")
    _require_mapping(payload.get("provenance"), "provenance")
    _require_retention_policy(payload, "retention")
    return payload


def validate_unity_adapter_result_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.unity-adapter-result.v2", "schema")
    _require(payload.get("adapter") in {"editor", "player"}, "adapter")
    _require(payload.get("status") in VALID_RUN_STATUSES, "status")
    _require(payload.get("evidence_tier") in VALID_EVIDENCE_TIERS_V2, "evidence_tier")
    _require_bool(payload, "unity_editor_verified")
    _require_mapping(payload.get("facts"), "facts")
    _require(isinstance(payload.get("errors"), list), "errors")
    if payload["adapter"] == "editor":
        _require(payload.get("operation") in VALID_EDITOR_OPERATIONS, "operation")
        if payload.get("operation") == "plan":
            _require(payload.get("unity_editor_verified") is False, "unity_editor_verified")
    if payload["adapter"] == "player":
        _require(payload.get("operation") in VALID_PLAYER_OPERATIONS, "operation")
        player = _require_mapping(payload.get("player"), "player")
        _require(player.get("enabled") is False, "player.enabled")
        _require(player.get("protocol") == "none", "player.protocol")
        _require(player.get("endpoint") == "", "player.endpoint")
        _require_non_negative_int(player, "player.timeout_ms")
        _require(player.get("dev_build_only") is True, "player.dev_build_only")
    return payload


def _require(condition: bool, field: str) -> None:
    if not condition:
        raise ContractError(field)


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ContractError(field)


def _require_list(payload: dict[str, Any], field: str) -> list[Any]:
    value = _field_value(payload, field)
    if isinstance(value, list):
        return value
    raise ContractError(field)


def _require_non_empty_str(payload: dict[str, Any], field: str) -> None:
    value = _field_value(payload, field)
    _require(isinstance(value, str) and bool(value), field)


def _require_non_empty_fields(
    payload: dict[str, Any], fields: tuple[str, ...], prefix: str = ""
) -> None:
    for field in fields:
        _require_non_empty_str(payload, f"{prefix}.{field}" if prefix else field)


def _require_bool(payload: dict[str, Any], field: str) -> None:
    _require(isinstance(_field_value(payload, field), bool), field)


def _require_non_negative_int(payload: dict[str, Any], field: str) -> None:
    value = _field_value(payload, field)
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, field)


def _require_completed_at(payload: dict[str, Any], field: str) -> None:
    value = _field_value(payload, field)
    _require(value is None or (isinstance(value, str) and bool(value)), field)


def _require_string_list(payload: dict[str, Any], field: str) -> None:
    _require(all(isinstance(value, str) for value in _require_list(payload, field)), field)


def _require_non_negative_int_mapping(payload: dict[str, Any], field: str) -> None:
    for key, value in _require_mapping(payload.get(field), field).items():
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            f"{field}.{key}",
        )


def _require_retention_policy(payload: dict[str, Any], field: str) -> None:
    retention = _require_mapping(payload.get(field), field)
    _require_non_negative_int(retention, f"{field}.max_events")
    _require_non_negative_int(retention, f"{field}.max_chars")
    _require(retention.get("store_raw_patch_bodies") is False, f"{field}.store_raw_patch_bodies")


def _require_allowed_memory_path(path: str, field: str) -> None:
    normalized = path.replace("\\", "/")
    allowed = (
        normalized.startswith(".unity-harness/cache/"),
        normalized.startswith(".unity-harness/reports/"),
        normalized.startswith(".unity-harness/last-"),
    )
    _require(not normalized.startswith("/") and ".." not in normalized.split("/"), field)
    _require(any(allowed), field)


def _field_value(payload: dict[str, Any], field: str) -> Any:
    if "." not in field:
        return payload.get(field)
    return payload.get(field.rsplit(".", 1)[-1])
