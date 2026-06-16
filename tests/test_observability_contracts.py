import pytest

import kunity_yamae.contracts as contracts
from kunity_yamae.contracts import ContractError


def _valid_trace_event_v1() -> dict[str, object]:
    return {
        "schema": "unity-harness.trace-event.v1",
        "run_id": "run-contract-001",
        "trace_id": "trace-contract-001",
        "span_id": "span-context",
        "parent_span_id": None,
        "event": "tool.completed",
        "status": "completed",
        "tool": "harness.context.select",
        "duration_ms": 12,
        "evidence_tier": "static_scan",
        "attributes": {"step_id": "step-context"},
    }


def _valid_metrics_summary_v1() -> dict[str, object]:
    return {
        "schema": "unity-harness.metrics-summary.v1",
        "run_id": "run-contract-001",
        "counters": {"tool_calls": 1, "errors": 0},
        "durations_ms": {"total": 12},
        "status_counts": {"completed": 1},
    }


def test_accepts_trace_event_and_metrics_summary() -> None:
    trace = _valid_trace_event_v1()
    metrics = _valid_metrics_summary_v1()

    assert contracts.validate_trace_event_v1(trace) == trace
    assert contracts.validate_metrics_summary_v1(metrics) == metrics


def test_rejects_trace_event_without_trace_id() -> None:
    payload = _valid_trace_event_v1()
    del payload["trace_id"]

    with pytest.raises(ContractError, match="trace_id"):
        contracts.validate_trace_event_v1(payload)


def test_rejects_negative_metrics_counter() -> None:
    payload = _valid_metrics_summary_v1()
    counters = payload["counters"]
    assert isinstance(counters, dict)
    counters["errors"] = -1

    with pytest.raises(ContractError, match="counters.errors"):
        contracts.validate_metrics_summary_v1(payload)


def test_rejects_non_integer_trace_duration() -> None:
    payload = _valid_trace_event_v1()
    payload["duration_ms"] = 12.5

    with pytest.raises(ContractError, match="duration_ms"):
        contracts.validate_trace_event_v1(payload)
