"""Offline fixture benchmark: bytes and local host work, never model-performance claims."""
from __future__ import annotations

import platform
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from statistics import median

from .constants import GENERATED_FOLDERS
from .worker_packet import compact_json, prepare_worker_packet, render_worker_prompt


def _put(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _milliseconds(call, repeats: int = 7) -> float:
    values = []
    for _ in range(repeats):
        started = time.perf_counter()
        call()
        values.append((time.perf_counter() - started) * 1000)
    return round(median(values), 3)


def benchmark() -> dict:
    with tempfile.TemporaryDirectory(prefix="yamae-benchmark-") as temporary:
        root = Path(temporary)
        _put(root, "ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 6000.3.8f1\n")
        _put(root, "Packages/manifest.json", '{"dependencies":{}}')
        lines = [f"// unrelated implementation detail {i:04d}" for i in range(1, 601)]
        lines[399:403] = ["public string GetCaption()", "{", '    return "Contine";', "}"]
        text = "\n".join(lines)
        _put(root, "Assets/Caption.cs", text)
        for folder in range(20):
            for file in range(50):
                _put(root, f"Library/generated-{folder}/entry-{file}.cs", "// generated")
        request = {"kind": "code_patch", "task": "Fix Contine to Continue in GetCaption",
                   "acceptance": ["Only GetCaption text changes; compile and focused test pass."],
                   "write_paths": ["Assets/Caption.cs"],
                   "slices": [{"path": "Assets/Caption.cs", "start": 398, "end": 405}]}
        packet = prepare_worker_packet(root, request)
        if packet["status"] != "prepared":
            raise AssertionError(packet)
        scoped = render_worker_prompt(packet)
        # Same policies, versions, checks and task: only the source payload differs.
        full = deepcopy(packet)
        full["payload"]["sources"] = [{"path": "Assets/Caption.cs", "start": 1,
                                        "end": len(lines), "text": text}]
        full_prompt = render_worker_prompt(full)
        sizes = {"full_file_bytes": len(full_prompt.encode("utf-8")),
                 "explicit_range_bytes": len(scoped.encode("utf-8"))}

        def original_inventory():
            return sorted(path.relative_to(root).as_posix() for path in root.rglob("*")
                          if path.is_file()
                          and not any(p in GENERATED_FOLDERS for p in path.relative_to(root).parts))

        def pruned_inventory():
            return sorted(path.relative_to(root).as_posix() for path in _pruned_files(root))

        if original_inventory() != pruned_inventory():
            raise AssertionError("inventory optimization changed discovered files")
        return {"schema": "unity-harness.efficiency-benchmark.v1", "fixture_only": True,
                "python": platform.python_version(), "platform": platform.system(),
                "model_called": False, "unity_executed": False,
                "prompt": {**sizes, "byte_reduction_percent": round(
                    (1 - sizes["explicit_range_bytes"] / sizes["full_file_bytes"]) * 100, 2),
                    "target_in_original_head_50": "Contine" in "\n".join(lines[:50]),
                    "target_in_scoped_packet": "Contine" in packet["payload"]["sources"][0]["text"],
                    "policies_and_acceptance_preserved": True,
                    "token_reduction": None, "model_latency_reduction": None},
                "host": {"generated_files": 1000, "same_inventory": True,
                         "repeats": 7, "timing": "warm local filesystem median; fixture-specific",
                         "rglob_then_filter_ms": _milliseconds(original_inventory),
                         "pruned_walk_ms": _milliseconds(pruned_inventory),
                         "worker_packet_prepare_ms": _milliseconds(
                             lambda: prepare_worker_packet(root, request))},
                "limits": ["No model token counts, cache hits, success rates or bill measured.",
                           "Planner selection/discovery overhead is not in the byte comparison.",
                           "Host timings do not predict end-to-end agent speed."]}


def _pruned_files(root):
    # Benchmark the same implementation used by ProjectFileInventory.collect.
    from .project_files import _iter_project_files

    files = _iter_project_files(root)
    return files


if __name__ == "__main__":
    print(compact_json(benchmark()))
