import re
import subprocess
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.cli_release_check import has_tracked_scratch_artifact
from tests.fixtures.make_unity_project import create_minimal_project, initialize_git_fixture

HARNESS_GITIGNORE = "\n".join(
    [
        ".unity-harness/cache/",
        ".unity-harness/reports/",
        ".unity-harness/last-*.jsonl",
        ".unity-harness/last-*.json",
        "",
    ]
)


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


def test_harness_cli_outputs_stay_ignored_or_cached_in_git_fixture(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    (tmp_path / ".gitignore").write_text(HARNESS_GITIGNORE, encoding="utf-8")
    initialize_git_fixture(
        tmp_path,
        user_email="artifact-hygiene@example.com",
        user_name="Artifact Hygiene",
        commit_message="baseline fixture",
    )
    runner = CliRunner()

    commands = [
        ["--project", str(tmp_path), "scan", "--json"],
        ["--project", str(tmp_path), "context", "Fix generated artifact hygiene"],
        [
            "--project",
            str(tmp_path),
            "run",
            "Fix generated artifact hygiene",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Fix generated artifact hygiene",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Fix generated artifact hygiene",
            "--execute-loop",
            "--schema",
            "v2",
            "--verify-dry-run",
            "--json",
        ],
    ]

    for command in commands:
        result = runner.invoke(main, command)
        assert result.exit_code == 0, result.output

    generated = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / ".unity-harness").rglob("*")
        if path.is_file()
    )
    assert ".unity-harness/project-profile.json" not in generated
    assert generated
    assert all(
        path.startswith(".unity-harness/cache/")
        or path.startswith(".unity-harness/reports/")
        or path.startswith(".unity-harness/last-")
        for path in generated
    )

    status = subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=tmp_path,
        text=True,
    )
    assert ".unity-harness/" not in status


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


def test_task10_docs_and_entrypoints_keep_artifact_hygiene_receipt() -> None:
    docs = "\n".join(
        [
            Path("README.md").read_text(encoding="utf-8"),
            Path("README_KO.md").read_text(encoding="utf-8"),
            Path("docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8"),
            Path(".agents/skills/k-unity-yamae/SKILL.md").read_text(encoding="utf-8"),
            Path(".claude/skills/k-unity-yamae/SKILL.md").read_text(encoding="utf-8"),
            Path(".claude/commands/kunity-yamae.md").read_text(encoding="utf-8"),
        ]
    )

    assert ".unity-harness/cache/" in docs
    assert ".unity-harness/reports/" in docs
    assert ".unity-harness/last-" in docs
    assert "scratch planning/evidence artifacts" in docs
