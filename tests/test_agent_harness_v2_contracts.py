import pytest

from kunity_yamae.contracts import (
    ContractError,
    validate_orchestration_plan_v1,
    validate_tool_call_result_v1,
    validate_tool_registry_v1,
    validate_tool_spec_v1,
    validate_unity_adapter_result_v1,
)


def test_accepts_valid_v2_contracts() -> None:
    spec = {
        "schema": "unity-harness.tool-spec.v1",
        "name": "unity.verify.plan",
        "version": "1",
        "description": "Plan Unity verification commands.",
        "input_contract": "unity-harness.tool-input.v1",
        "output_contract": "unity-harness.tool-call-result.v1",
        "permission": "plan",
        "side_effect_level": "none",
        "timeout_ms": 1000,
        "evidence_tier": "planned",
        "guard_required": False,
        "handler_kind": "local",
        "capability_tags": ["unity", "verification"],
    }
    result = {
        "schema": "unity-harness.tool-call-result.v1",
        "tool": "unity.verify.plan",
        "status": "completed",
        "evidence_tier": "planned",
        "result": {"commands": []},
        "errors": [],
    }
    plan = {
        "schema": "unity-harness.orchestration-plan.v1",
        "status": "planned",
        "task": "Fix sample button raycast",
        "risk_report": {},
        "mode": "standard",
        "tool_plan": [
            {
                "tool": "harness.context.select",
                "status": "completed",
                "input": {"task": "Fix sample button raycast"},
                "evidence_tier": "static_scan",
                "result": result,
            }
        ],
        "patch_handoff": {"required": False},
        "verification_profile": {"dry_run": True},
        "memory_policy": {"enabled": False},
        "observability": {"trace": "jsonl"},
        "evidence_tier": "planned",
    }
    adapter = {
        "schema": "unity-harness.unity-adapter-result.v1",
        "adapter": "player",
        "status": "unavailable",
        "evidence_tier": "unavailable",
        "facts": {},
        "errors": [],
    }

    assert validate_tool_spec_v1(spec) == spec
    assert validate_tool_registry_v1({"schema": "unity-harness.tool-registry.v1", "tools": [spec]})
    assert validate_tool_call_result_v1(result) == result
    assert validate_orchestration_plan_v1(plan) == plan
    assert validate_unity_adapter_result_v1(adapter) == adapter


def test_rejects_invalid_side_effect_level() -> None:
    spec = {
        "schema": "unity-harness.tool-spec.v1",
        "name": "unity.verify.plan",
        "version": "1",
        "description": "Plan Unity verification commands.",
        "input_contract": "unity-harness.tool-input.v1",
        "output_contract": "unity-harness.tool-call-result.v1",
        "permission": "plan",
        "side_effect_level": "dangerous",
        "timeout_ms": 1000,
        "evidence_tier": "planned",
        "guard_required": False,
        "handler_kind": "local",
        "capability_tags": ["unity"],
    }

    with pytest.raises(ContractError, match="side_effect_level"):
        validate_tool_spec_v1(spec)


def test_rejects_placeholder_orchestration_tool_plan_rows() -> None:
    plan = {
        "schema": "unity-harness.orchestration-plan.v1",
        "status": "planned",
        "task": "Fix sample button raycast",
        "risk_report": {},
        "mode": "standard",
        "tool_plan": [
            {
                "tool": "harness.context.select",
                "status": "completed",
                "evidence_tier": "static_scan",
                "result": {
                    "schema": "unity-harness.tool-call-result.v1",
                    "tool": "harness.context.select",
                    "status": "completed",
                    "evidence_tier": "static_scan",
                    "result": {},
                    "errors": [],
                },
            }
        ],
        "patch_handoff": {"required": False},
        "verification_profile": {"dry_run": True},
        "memory_policy": {"enabled": False},
        "observability": {"trace": "jsonl"},
        "evidence_tier": "planned",
    }

    with pytest.raises(ContractError, match="tool_plan.0.input"):
        validate_orchestration_plan_v1(plan)
