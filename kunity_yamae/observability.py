from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .contracts import validate_metrics_summary_v1, validate_trace_event_v1
from .path_locks import interprocess_lock_for_path, lock_for_path


class JsonlTraceSink:
    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir
        self.events_path = trace_dir / "events.jsonl"
        self.metrics_path = trace_dir / "metrics-summary.json"
        self._events: list[dict[str, Any]] = []
        self._file_lock = lock_for_path(self.events_path)

    def record_tool_event(
        self,
        *,
        run_id: str,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None,
        event: str,
        status: str,
        tool: str | None,
        duration_ms: int,
        evidence_tier: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        payload = validate_trace_event_v1(
            {
                "schema": "unity-harness.trace-event.v1",
                "run_id": run_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "event": event,
                "status": status,
                "tool": tool,
                "duration_ms": duration_ms,
                "evidence_tier": evidence_tier,
                "attributes": attributes,
            }
        )
        with self._file_lock:
            self._events.append(payload)
            with interprocess_lock_for_path(self.events_path):
                self.events_path.parent.mkdir(parents=True, exist_ok=True)
                with self.events_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload

    def write_metrics_summary(self, run_id: str) -> dict[str, Any]:
        counters: dict[str, int] = {}
        durations: dict[str, int] = {}
        statuses: dict[str, int] = {}
        for event in self._events:
            name = str(event["event"])
            status = str(event["status"])
            counters[name] = counters.get(name, 0) + 1
            durations[name] = durations.get(name, 0) + int(event["duration_ms"])
            statuses[status] = statuses.get(status, 0) + 1
        payload = validate_metrics_summary_v1(
            {
                "schema": "unity-harness.metrics-summary.v1",
                "run_id": run_id,
                "counters": counters,
                "durations_ms": durations,
                "status_counts": statuses,
            }
        )
        _atomic_write_text(self.metrics_path, json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    def _rewrite_events(self) -> None:
        lines = [json.dumps(event, ensure_ascii=False) for event in self._events]
        _atomic_write_text(self.events_path, "\n".join(lines) + ("\n" if lines else ""))


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    with interprocess_lock_for_path(path):
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
