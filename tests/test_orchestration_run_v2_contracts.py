from typing import Any, cast

import pytest

import kunity_yamae.contracts as contracts
from kunity_yamae.contracts import ContractError


def _valid_tool_result_v2() -> dict[str, object]:
    return {
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


def _valid_orchestration_run_v2() -> dict[str, object]:
    return {
        "schema": "unity-harness.orchestration-run.v2",
        "run_id": "run-contract-001",
        "status": "completed",
        "task": "Inspect project-neutral context",
        "started_at": "2026-06-17T00:00:00Z",
        "completed_at": "2026-06-17T00:00:01Z",
        "duration_ms": 1000,
        "steps": [
            {
                "id": "step-context",
                "tool": "harness.context.select",
                "status": "completed",
                "depends_on": [],
                "started_at": "2026-06-17T00:00:00Z",
                "completed_at": "2026-06-17T00:00:01Z",
                "duration_ms": 1000,
                "permission_outcome": "allowed",
                "evidence_tier": "static_scan",
                "input": {"task": "Inspect project-neutral context"},
                "result": _valid_tool_result_v2(),
            }
        ],
    }


def test_accepts_valid_orchestration_run_v2() -> None:
    payload = _valid_orchestration_run_v2()

    assert contracts.validate_orchestration_run_v2(payload) == payload


def test_rejects_placeholder_step_rows() -> None:
    payload = _valid_orchestration_run_v2()
    steps = cast(list[dict[str, Any]], payload["steps"])
    step = steps[0]
    assert isinstance(step, dict)
    del step["input"]

    with pytest.raises(ContractError, match="steps.0.input"):
        contracts.validate_orchestration_run_v2(payload)


def test_rejects_invalid_permission_outcome() -> None:
    payload = _valid_orchestration_run_v2()
    steps = cast(list[dict[str, Any]], payload["steps"])
    step = steps[0]
    assert isinstance(step, dict)
    step["permission_outcome"] = "approved"

    with pytest.raises(ContractError, match="steps.0.permission_outcome"):
        contracts.validate_orchestration_run_v2(payload)
