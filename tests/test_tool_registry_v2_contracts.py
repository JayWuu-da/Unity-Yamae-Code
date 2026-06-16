import pytest

import kunity_yamae.contracts as contracts
from kunity_yamae.contracts import ContractError


def _valid_tool_spec_v2() -> dict[str, object]:
    return {
        "schema": "unity-harness.tool-spec.v2",
        "name": "harness.context.select",
        "version": "2",
        "description": "Select project context for a non-mutating task.",
        "input_contract": "unity-harness.tool-input.v2",
        "output_contract": "unity-harness.tool-call-result.v2",
        "permission": "read",
        "side_effect_level": "none",
        "timeout_ms": 1000,
        "evidence_tier": "static_scan",
        "guard_required": False,
        "handler_kind": "local",
        "capability_tags": ["context"],
        "lifecycle": "available",
        "dry_run_supported": True,
        "adapter_scope": "harness",
        "failure_modes": ["unavailable"],
        "observability_events": ["tool.started", "tool.completed"],
    }


def test_accepts_valid_tool_registry_v2() -> None:
    payload = {
        "schema": "unity-harness.tool-registry.v2",
        "tools": [_valid_tool_spec_v2()],
    }

    assert contracts.validate_tool_spec_v2(_valid_tool_spec_v2())["schema"].endswith(".v2")
    assert contracts.validate_tool_registry_v2(payload) == payload


def test_accepts_valid_tool_call_result_v2() -> None:
    payload = {
        "schema": "unity-harness.tool-call-result.v2",
        "tool": "harness.context.select",
        "status": "completed",
        "permission": "read",
        "permission_outcome": "allowed",
        "evidence_tier": "static_scan",
        "observability_events": ["tool.completed"],
        "result": {"selected_files": []},
        "errors": [],
    }

    assert contracts.validate_tool_call_result_v2(payload) == payload


def test_rejects_invalid_v2_lifecycle() -> None:
    payload = _valid_tool_spec_v2()
    payload["lifecycle"] = "prototype"

    with pytest.raises(ContractError, match="lifecycle"):
        contracts.validate_tool_spec_v2(payload)


def test_rejects_invalid_v2_permission() -> None:
    payload = _valid_tool_spec_v2()
    payload["permission"] = "mutate_project"

    with pytest.raises(ContractError, match="permission"):
        contracts.validate_tool_spec_v2(payload)
