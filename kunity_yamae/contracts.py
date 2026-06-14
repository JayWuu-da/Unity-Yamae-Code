from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ContractError(Exception):
    field: str

    def __str__(self) -> str:
        return f"Missing or invalid contract field: {self.field}"


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


def _require_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    return _require_mapping(value, field)


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ContractError(field)


def _require(condition: bool, field: str) -> None:
    if not condition:
        raise ContractError(field)
