import pytest

import kunity_yamae.contracts as contracts
from kunity_yamae.contracts import ContractError


def _valid_retention() -> dict[str, object]:
    return {
        "max_events": 1000,
        "max_chars": 20000,
        "store_raw_patch_bodies": False,
    }


def _valid_memory_event_v2() -> dict[str, object]:
    return {
        "schema": "unity-harness.memory-event.v2",
        "run_id": "run-contract-001",
        "event": "session.evidence_recorded",
        "storage_path": ".unity-harness/cache/session/events.jsonl",
        "payload": {"summary": "Recorded project-neutral scan evidence."},
        "provenance": {"evidence_tier": "static_scan", "source": "tool_result"},
        "dedupe_fingerprint": "memory-contract-001",
        "redaction": {"absolute_paths": "redacted"},
        "retention": _valid_retention(),
    }


def _valid_episodic_summary_v1() -> dict[str, object]:
    return {
        "schema": "unity-harness.episodic-memory-summary.v1",
        "run_id": "run-contract-001",
        "storage_path": ".unity-harness/reports/memory-summary.json",
        "summary": "Context scan completed with bounded evidence.",
        "event_count": 1,
        "provenance": {"evidence_tier": "static_scan", "source": "memory_event"},
        "retention": _valid_retention(),
    }


def test_accepts_session_memory_event_v2() -> None:
    payload = _valid_memory_event_v2()

    assert contracts.validate_memory_event_v2(payload) == payload


def test_accepts_episodic_memory_summary_v1() -> None:
    payload = _valid_episodic_summary_v1()

    assert contracts.validate_episodic_memory_summary_v1(payload) == payload


def test_rejects_memory_path_outside_harness_dirs() -> None:
    payload = _valid_memory_event_v2()
    payload["storage_path"] = "reports/session/events.jsonl"

    with pytest.raises(ContractError, match="storage_path"):
        contracts.validate_memory_event_v2(payload)


def test_rejects_inferred_unity_fact_without_provenance() -> None:
    payload = _valid_memory_event_v2()
    payload["payload"] = {"fact_kind": "unity", "source": "inferred", "claim": "Scene has listener"}
    payload["provenance"] = {}

    with pytest.raises(ContractError, match="provenance"):
        contracts.validate_memory_event_v2(payload)
