from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .contracts import validate_episodic_memory_summary_v1, validate_memory_event_v2
from .path_locks import interprocess_lock_for_path, lock_for_path


class HarnessMemoryStore:
    def __init__(
        self,
        state_dir: Path,
        *,
        storage_path_prefix: str = ".unity-harness/cache/state",
    ) -> None:
        self.state_dir = state_dir
        self.storage_path_prefix = storage_path_prefix.rstrip("/")
        self.events_path = state_dir / "memory-events.jsonl"
        self.summary_path = state_dir / "episodic-summary.json"
        self.db_path = state_dir / "memory.db"
        self._file_lock = lock_for_path(self.events_path)
        self._db_lock = lock_for_path(self.db_path)

    def record_event(
        self,
        *,
        run_id: str,
        event: str,
        payload: dict[str, Any],
        provenance: dict[str, Any],
        dedupe_key: str | None = None,
    ) -> dict[str, Any]:
        fingerprint = dedupe_key or _fingerprint(
            {"run_id": run_id, "event": event, "payload": payload}
        )
        event_payload = validate_memory_event_v2(
            {
                "schema": "unity-harness.memory-event.v2",
                "run_id": run_id,
                "event": event,
                "storage_path": f"{self.storage_path_prefix}/memory-events.jsonl",
                "dedupe_fingerprint": fingerprint,
                "payload": payload,
                "provenance": provenance,
                "redaction": {"raw_patch_body": "omitted"},
                "retention": {
                    "max_events": 1000,
                    "max_chars": 200000,
                    "store_raw_patch_bodies": False,
                },
            }
        )
        return self._insert_once(fingerprint, event_payload)

    def write_episodic_summary(self, run_id: str, summary: str) -> dict[str, Any]:
        payload = validate_episodic_memory_summary_v1(
            {
                "schema": "unity-harness.episodic-memory-summary.v1",
                "run_id": run_id,
                "storage_path": f"{self.storage_path_prefix}/episodic-summary.json",
                "summary": summary,
                "event_count": len(self._read_events()),
                "provenance": {"evidence_tier": "static_scan", "source": "memory_store"},
                "retention": {
                    "max_events": 1000,
                    "max_chars": 200000,
                    "store_raw_patch_bodies": False,
                },
            }
        )
        _atomic_write_json(self.summary_path, payload)
        return payload

    def _find_existing(self, fingerprint: str) -> dict[str, Any] | None:
        with self._db_lock:
            self._ensure_db_unlocked()
            with sqlite3.connect(self.db_path, timeout=30) as connection:
                row = connection.execute(
                    "select payload from memory_events where dedupe_fingerprint = ?",
                    (fingerprint,),
                ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def _read_events(self) -> list[dict[str, Any]]:
        with self._db_lock:
            self._ensure_db_unlocked()
            with sqlite3.connect(self.db_path, timeout=30) as connection:
                rows = connection.execute(
                    "select payload from memory_events order by rowid"
                ).fetchall()
        if rows:
            return [json.loads(row[0]) for row in rows]
        if not self.events_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _insert_once(self, fingerprint: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload, ensure_ascii=False)
        with self._db_lock:
            self._ensure_db_unlocked()
            with sqlite3.connect(self.db_path, timeout=30, isolation_level=None) as connection:
                connection.execute("begin immediate")
                row = connection.execute(
                    "select payload from memory_events where dedupe_fingerprint = ?",
                    (fingerprint,),
                ).fetchone()
                if row:
                    connection.execute("commit")
                    return json.loads(row[0])
                connection.execute(
                    "insert into memory_events(dedupe_fingerprint, payload) values (?, ?)",
                    (fingerprint, encoded),
                )
                connection.execute("commit")
        self._append_event_jsonl(payload)
        return payload

    def _ensure_db_unlocked(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=30) as connection:
            connection.execute("pragma journal_mode = wal")
            connection.execute(
                "create table if not exists memory_events ("
                "dedupe_fingerprint text primary key, payload text not null)"
            )

    def _append_event_jsonl(self, payload: dict[str, Any]) -> None:
        with self._file_lock:
            with interprocess_lock_for_path(self.events_path):
                self.events_path.parent.mkdir(parents=True, exist_ok=True)
                with self.events_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    with interprocess_lock_for_path(path):
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
