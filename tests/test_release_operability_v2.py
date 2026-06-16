import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae import cli_release_check
from kunity_yamae.cli import main
from kunity_yamae.project_assumption_hygiene import (
    PROJECT_ASSUMPTION_TERMS,
    find_project_assumption_matches,
)
from tests.fixtures.make_unity_project import create_minimal_project


def test_release_check_reports_cli_help_and_local_patch_agent(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["cli_surface"]["run_has_guarded_agent_patch"] is True
    assert payload["cli_surface"]["tools_command_registered"] is True
    assert payload["cli_surface"]["orchestrate_command_registered"] is True
    assert payload["cli_surface"]["run_has_no_verify"] is True
    assert payload["desktop_integration"]["agents_md"] is True
    assert payload["desktop_integration"]["codex_skill"] is True
    assert payload["desktop_integration"]["claude_md"] is True
    assert payload["desktop_integration"]["claude_skill"] is True
    assert payload["desktop_integration"]["claude_command"] is True
    assert payload["desktop_integration"]["no_legacy_codex_skill"] is True
    assert payload["desktop_integration"]["codex_skill_mentions_guarded_patch"] is True
    assert payload["desktop_integration"]["claude_skill_mentions_git_for_windows"] is True
    assert payload["agent_registry"]["local_patch"] is True


def test_release_check_reports_agent_harness_v2_copy(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["desktop_integration"]["codex_skill_mentions_tools_list"] is True
    assert payload["desktop_integration"]["codex_skill_mentions_orchestrate"] is True
    assert payload["desktop_integration"]["claude_skill_mentions_orchestrate"] is True
    assert payload["agent_facing_copy"]["entrypoints_mention_non_mutating_orchestrate"] is True
    assert payload["project_assumption_hygiene"]["passed"] is True
    assert payload["project_assumption_hygiene"]["matches"] == []


def test_release_check_reports_task10_docs_and_entrypoint_contracts(
    tmp_path: Path,
) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["agent_facing_copy"]["docs_mention_shared_inventory"] is True
    assert payload["agent_facing_copy"]["docs_bound_generic_semantic_signals"] is True
    assert payload["agent_facing_copy"]["docs_mention_artifact_hygiene"] is True
    assert payload["agent_facing_copy"]["entrypoints_mention_concrete_tools_orchestrate"] is True
    assert payload["agent_facing_copy"]["entrypoints_mention_artifact_hygiene"] is True
    assert payload["agent_facing_copy"]["no_unity_verification_overclaim"] is True
    assert payload["desktop_integration"]["codex_skill_mentions_shared_inventory"] is True
    assert payload["desktop_integration"]["claude_skill_mentions_shared_inventory"] is True


def test_release_check_rejects_tracked_scratch_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_minimal_project(tmp_path)
    original_check_output = subprocess.check_output

    def fake_check_output(command, *, cwd: Path, text: bool) -> str:
        if command == ["git", "ls-files", ".omo", ".omx", "plans", "evidence"]:
            assert cwd.exists()
            assert text is True
            return "\n".join(
                [
                    ".omo/session.jsonl",
                    ".omx/evidence.txt",
                    "plans/agent-plan.md",
                    "evidence/final.txt",
                    "",
                ]
            )
        return original_check_output(command, cwd=cwd, text=text)

    monkeypatch.setattr(cli_release_check.subprocess, "check_output", fake_check_output)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["agent_facing_copy"]["tracked_artifact_hygiene"] is False
    assert "agent_facing_copy.tracked_artifact_hygiene" in payload["failed_checks"]


def test_project_assumption_hygiene_reports_synthetic_sentinel(tmp_path: Path) -> None:
    path = tmp_path / "example.txt"
    path.write_text("ForbiddenProjectTokenForTest", encoding="utf-8")

    matches = find_project_assumption_matches(
        tmp_path,
        paths=[path],
        terms=["ForbiddenProjectTokenForTest"],
    )

    assert matches == ["example.txt:1:ForbiddenProjectTokenForTest"]


def test_project_assumption_hygiene_blocks_resource_category_assumptions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "example.py"
    path.write_text(
        "\n".join(
            [
                'CATEGORY_CONSTANT = "' + "VFX" + '_PATTERNS"',
                'CATEGORY_DOC = "' + "semantic " + 'VFX buckets"',
            ]
        ),
        encoding="utf-8",
    )

    matches = find_project_assumption_matches(
        tmp_path,
        paths=[path],
        terms=PROJECT_ASSUMPTION_TERMS,
    )

    assert matches == [
        "example.py:1:" + "VFX" + "_PATTERNS",
        "example.py:2:" + "semantic " + "VFX buckets",
    ]


def test_providers_doctor_lists_local_patch_as_offline_handoff(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "providers", "doctor", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    handoff = payload["offline_handoffs"]["local-patch"]
    assert handoff["status"] == "ready"
    assert "requires_" + "api_key" not in handoff
    assert "--guarded-agent-patch" in handoff["usage"]
