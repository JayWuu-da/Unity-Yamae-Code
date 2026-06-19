import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kunity_yamae.memory_store import HarnessMemoryStore
from kunity_yamae.observability import JsonlTraceSink


def test_trace_sink_writes_trace_and_metrics_contracts(tmp_path) -> None:
    sink = JsonlTraceSink(tmp_path / ".unity-harness" / "traces")

    sink.record_tool_event(
        run_id="run-001",
        trace_id="trace-001",
        span_id="span-001",
        parent_span_id=None,
        event="tool.completed",
        status="completed",
        tool="harness.risk.classify",
        duration_ms=7,
        evidence_tier="static_scan",
        attributes={"permission": "read"},
    )
    metrics = sink.write_metrics_summary("run-001")

    trace_rows = [
        json.loads(line)
        for line in (tmp_path / ".unity-harness" / "traces" / "events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert trace_rows[0]["schema"] == "unity-harness.trace-event.v1"
    assert metrics["schema"] == "unity-harness.metrics-summary.v1"
    assert metrics["counters"]["tool.completed"] == 1
    assert metrics["status_counts"]["completed"] == 1


def test_trace_sink_handles_concurrent_distinct_events(tmp_path) -> None:
    sink = JsonlTraceSink(tmp_path / ".unity-harness" / "traces")

    def write_event(index: int) -> None:
        sink.record_tool_event(
            run_id="run-001",
            trace_id="trace-001",
            span_id=f"span-{index}",
            parent_span_id=None,
            event="tool.completed",
            status="completed",
            tool="harness.risk.classify",
            duration_ms=index,
            evidence_tier="static_scan",
            attributes={"index": index},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_event, range(64)))

    rows = [
        json.loads(line)
        for line in (tmp_path / ".unity-harness" / "traces" / "events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert len(rows) == 64


def test_trace_sink_handles_cross_instance_concurrent_distinct_events(tmp_path) -> None:
    trace_dir = tmp_path / ".unity-harness" / "traces"

    def write_event(index: int) -> None:
        JsonlTraceSink(trace_dir).record_tool_event(
            run_id="run-001",
            trace_id="trace-001",
            span_id=f"span-{index}",
            parent_span_id=None,
            event="tool.completed",
            status="completed",
            tool="harness.risk.classify",
            duration_ms=index,
            evidence_tier="static_scan",
            attributes={"index": index},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_event, range(64)))

    rows = [
        json.loads(line)
        for line in (trace_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 64


def test_trace_sink_handles_cross_process_concurrent_distinct_events(tmp_path) -> None:
    trace_dir = tmp_path / ".unity-harness" / "traces"
    script = (
        "import sys; "
        "from pathlib import Path; "
        "from kunity_yamae.observability import JsonlTraceSink; "
        "idx=int(sys.argv[2]); "
        "JsonlTraceSink(Path(sys.argv[1])).record_tool_event("
        "run_id='run-001', trace_id='trace-001', span_id=f'span-{idx}', "
        "parent_span_id=None, event='tool.completed', status='completed', "
        "tool='harness.risk.classify', duration_ms=idx, evidence_tier='static_scan', "
        "attributes={'index': idx})"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(trace_dir), str(index)],
            cwd=Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(32)
    ]
    failures = [process.communicate(timeout=30) for process in processes if process.wait(30) != 0]

    rows = [
        json.loads(line)
        for line in (trace_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert failures == []
    assert len(rows) == 32


def test_memory_store_records_deduped_events_without_raw_patch_body(tmp_path) -> None:
    state_dir = tmp_path / ".unity-harness" / "cache" / "state"
    store = HarnessMemoryStore(state_dir)
    event = store.record_event(
        run_id="run-001",
        event="tool_result",
        payload={"fact_kind": "tool", "source": "static_scan", "summary": "neutral result"},
        provenance={"evidence_tier": "static_scan", "tool": "harness.risk.classify"},
        dedupe_key="same-event",
    )
    duplicate = store.record_event(
        run_id="run-001",
        event="tool_result",
        payload={"fact_kind": "tool", "source": "static_scan", "summary": "neutral result"},
        provenance={"evidence_tier": "static_scan", "tool": "harness.risk.classify"},
        dedupe_key="same-event",
    )
    summary = store.write_episodic_summary("run-001", "Recorded one neutral tool result.")

    rows = [
        json.loads(line)
        for line in (state_dir / "memory-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert event == duplicate
    assert len(rows) == 1
    assert rows[0]["retention"]["store_raw_patch_bodies"] is False
    assert summary["schema"] == "unity-harness.episodic-memory-summary.v1"
    assert summary["event_count"] == 1
    assert (state_dir / "memory.db").exists()


def test_memory_store_dedupes_concurrent_writes_with_sqlite(tmp_path) -> None:
    state_dir = tmp_path / ".unity-harness" / "cache" / "state"
    store = HarnessMemoryStore(state_dir)

    def write_same_event() -> str:
        event = store.record_event(
            run_id="run-001",
            event="tool_result",
            payload={"fact_kind": "tool", "source": "static_scan", "summary": "neutral result"},
            provenance={"evidence_tier": "static_scan", "tool": "harness.risk.classify"},
            dedupe_key="same-event",
        )
        return str(event["dedupe_fingerprint"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        fingerprints = list(executor.map(lambda _index: write_same_event(), range(32)))

    rows = [
        json.loads(line)
        for line in (state_dir / "memory-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert set(fingerprints) == {"same-event"}
    assert len(rows) == 1


def test_memory_store_handles_concurrent_distinct_events(tmp_path) -> None:
    state_dir = tmp_path / ".unity-harness" / "cache" / "state"
    store = HarnessMemoryStore(state_dir)

    def write_event(index: int) -> str:
        event = store.record_event(
            run_id="run-001",
            event="tool_result",
            payload={"fact_kind": "tool", "source": "static_scan", "summary": f"result {index}"},
            provenance={"evidence_tier": "static_scan", "tool": "harness.risk.classify"},
            dedupe_key=f"event-{index}",
        )
        return str(event["dedupe_fingerprint"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        fingerprints = list(executor.map(write_event, range(64)))

    rows = [
        json.loads(line)
        for line in (state_dir / "memory-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(set(fingerprints)) == 64
    assert len(rows) == 64


def test_memory_store_handles_cross_instance_concurrent_distinct_events(tmp_path) -> None:
    state_dir = tmp_path / ".unity-harness" / "cache" / "state"

    def write_event(index: int) -> str:
        event = HarnessMemoryStore(state_dir).record_event(
            run_id="run-001",
            event="tool_result",
            payload={"fact_kind": "tool", "source": "static_scan", "summary": f"result {index}"},
            provenance={"evidence_tier": "static_scan", "tool": "harness.risk.classify"},
            dedupe_key=f"event-{index}",
        )
        return str(event["dedupe_fingerprint"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        fingerprints = list(executor.map(write_event, range(64)))

    rows = [
        json.loads(line)
        for line in (state_dir / "memory-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(set(fingerprints)) == 64
    assert len(rows) == 64
