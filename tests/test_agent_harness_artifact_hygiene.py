import re
import subprocess
from pathlib import Path

from kunity_yamae.cli_release_check import has_tracked_scratch_artifact


def test_no_tracked_scratch_plans_or_evidence_artifacts() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", ".omo", ".omx", "plans", "evidence"],
        text=True,
    )

    assert not any(has_tracked_scratch_artifact(line) for line in tracked.splitlines())


def test_tracked_artifact_detection_rejects_any_local_artifact_directory() -> None:
    assert has_tracked_scratch_artifact(".omo/session.jsonl") is True
    assert has_tracked_scratch_artifact(".omx/evidence.txt") is True
    assert has_tracked_scratch_artifact("plans/agent-plan.md") is True
    assert has_tracked_scratch_artifact("evidence/final.txt") is True
    assert has_tracked_scratch_artifact("docs/ARCHITECTURE.md") is False


def test_ancillary_docs_keep_agent_harness_positioning() -> None:
    docs = "\n".join(
        [
            Path("CONTRIBUTING.md").read_text(encoding="utf-8"),
            Path("docs/UPGRADE_REPORT.md").read_text(encoding="utf-8"),
        ]
    )

    assert not re.search(
        r"/path/to/UnityProject|human-facing standalone CLI|api provider",
        docs,
        flags=re.IGNORECASE,
    )
    assert re.search(r"AI-agent|agent", docs)
