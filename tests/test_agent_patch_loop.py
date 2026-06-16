import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import kunity_yamae.agents as agents
from kunity_yamae.cli import main
from kunity_yamae.guarded_edits import GuardedEditWorkflow
from tests.fixtures.make_unity_project import (
    create_git_project_with_player_stats,
    create_minimal_project,
)


class FakePatchAgent:
    def __init__(
        self,
        name: str,
        config: dict[str, Any],
        agent_config: dict[str, Any],
    ) -> None:
        self.name = name
        self.config = config
        self.agent_config = agent_config

    def execute(
        self,
        task: str,
        project_path: Path,
        risk_report: dict[str, Any],
        mode: str,
        ledger: Any,
    ) -> dict[str, Any]:
        return {"status": "completed", "output": self.agent_config["patch"]}


@pytest.fixture
def git_fixture_counter(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    counter = {"calls": 0}
    original_create_git_project = create_git_project_with_player_stats

    def counted_create_git_fixture(project_path: Path) -> None:
        counter["calls"] += 1
        original_create_git_project(project_path)

    monkeypatch.setattr(
        sys.modules[__name__],
        "create_git_project_with_player_stats",
        counted_create_git_fixture,
    )
    return counter


def test_run_agent_patch_plan_routes_output_through_guarded_edit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_git_project_with_player_stats(tmp_path)
    monkeypatch.setitem(agents.AGENT_REGISTRY, "fakepatch", FakePatchAgent)
    config_path = _write_config(tmp_path, "fakepatch", _safe_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Add readonly bonus helper",
            "--agent",
            "fakepatch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.run-result.v1"
    assert payload["agent_executed"] is True
    assert payload["agent_patch"]["status"] == "ready_to_apply"
    assert payload["agent_patch"]["applied"] is False
    assert "Bonus" not in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )
    assert payload["provider_requests"] == 0


def test_run_local_patch_reads_patch_file_from_cli_and_reports_no_provider_requests(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_git_project_with_player_stats(tmp_path)
    patch_file = tmp_path / "proposed.diff"
    patch_file.write_text(_safe_patch(), encoding="utf-8")
    config_path = _write_config(tmp_path, "local-patch", "")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Add readonly bonus helper",
            "--agent",
            "local-patch",
            "--patch-file",
            "proposed.diff",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "completed"
    assert payload["provider_requests"] == 0
    assert payload["agent_patch"]["status"] == "ready_to_apply"
    assert "Bonus" not in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )


def test_run_agent_patch_apply_blocks_serialized_rename(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_git_project_with_player_stats(tmp_path)
    monkeypatch.setitem(agents.AGENT_REGISTRY, "fakepatch", FakePatchAgent)
    config_path = _write_config(tmp_path, "fakepatch", _rename_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Rename serialized stat",
            "--agent",
            "fakepatch",
            "--guarded-agent-patch",
            "--apply-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["status"] == "blocked"
    assert payload["agent_patch"]["issues"][0]["guard"] == "serialized_rename"
    assert "hitpoints" in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    "asset_path",
    ["Assets/NewUI.prefab", "Assets/NewScene.unity", "Assets/NewConfig.asset"],
)
def test_run_agent_patch_apply_blocks_new_unity_asset_without_meta(
    tmp_path: Path,
    monkeypatch,
    asset_path: str,
) -> None:
    create_git_project_with_player_stats(tmp_path)
    monkeypatch.setitem(agents.AGENT_REGISTRY, "fakepatch", FakePatchAgent)
    config_path = _write_config(tmp_path, "fakepatch", _new_unity_asset_patch(asset_path))
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Add generated prefab",
            "--agent",
            "fakepatch",
            "--guarded-agent-patch",
            "--apply-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["applied"] is False
    guards = {issue["guard"] for issue in payload["agent_patch"]["issues"]}
    assert "meta_pair" in guards
    assert "yaml_write" in guards
    assert not (tmp_path / asset_path).exists()


def test_run_agent_patch_returns_json_failure_for_non_git_project(
    tmp_path: Path,
    git_fixture_counter: dict[str, int],
) -> None:
    create_minimal_project(tmp_path)
    config_path = _write_config(tmp_path, "local-patch", _safe_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Patch non git project",
            "--agent",
            "local-patch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["status"] == "error"
    assert git_fixture_counter["calls"] == 0


def test_run_agent_patch_returns_json_failure_for_empty_patch(
    tmp_path: Path,
    git_fixture_counter: dict[str, int],
) -> None:
    create_minimal_project(tmp_path)
    config_path = _write_config(tmp_path, "local-patch", "")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Empty patch",
            "--agent",
            "local-patch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_execution"
    assert payload["error"] == "local-patch requires patch or patch_file"
    assert git_fixture_counter["calls"] == 0


def test_guarded_workflow_reports_invalid_patch_without_git_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_fixture_counter: dict[str, int],
) -> None:
    def fake_run_git(
        self: GuardedEditWorkflow,
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git", *args], 0, stdout="", stderr="")

    def fake_run_git_apply(
        cwd: Path,
        patch_text: str,
        *,
        check_only: bool = False,
        reverse: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            ["git", "apply"],
            1,
            stdout="",
            stderr="error: No valid patches in input",
        )

    monkeypatch.setattr(GuardedEditWorkflow, "_run_git", fake_run_git)
    monkeypatch.setattr(GuardedEditWorkflow, "_run_git_apply", staticmethod(fake_run_git_apply))

    result = GuardedEditWorkflow(tmp_path, {}).evaluate("not a patch")

    assert result["status"] == "invalid_patch"
    assert result["error"] == "error: No valid patches in input"
    assert result["cleanup"]["worktree_removed"] is True
    assert git_fixture_counter["calls"] == 0


def _write_config(project_path: Path, agent_name: str, patch: str) -> Path:
    config_path = project_path / ".unity-harness" / "config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_patch = "\n".join(f"          {line}" for line in patch.splitlines())
    config_path.write_text(
        "\n".join(
            [
                "agents:",
                f"  default: {agent_name}",
                "  backends:",
                f"    {agent_name}:",
                "      enabled: true",
                "      patch: |",
                escaped_patch,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _rename_patch() -> str:
    return "\n".join(
        [
            "diff --git a/Assets/PlayerStats.cs b/Assets/PlayerStats.cs",
            "--- a/Assets/PlayerStats.cs",
            "+++ b/Assets/PlayerStats.cs",
            "@@ -1,5 +1,5 @@",
            " using UnityEngine;",
            " public sealed class PlayerStats : MonoBehaviour",
            " {",
            "-    [SerializeField] private int hitpoints;",
            "+    [SerializeField] private int health;",
            " }",
            "",
        ]
    )


def _safe_patch() -> str:
    return "\n".join(
        [
            "diff --git a/Assets/PlayerStats.cs b/Assets/PlayerStats.cs",
            "--- a/Assets/PlayerStats.cs",
            "+++ b/Assets/PlayerStats.cs",
            "@@ -1,5 +1,6 @@",
            " using UnityEngine;",
            " public sealed class PlayerStats : MonoBehaviour",
            " {",
            "     [SerializeField] private int hitpoints;",
            "+    public int Bonus => hitpoints;",
            " }",
            "",
        ]
    )


def _new_unity_asset_patch(asset_path: str) -> str:
    filename = Path(asset_path).name
    return "\n".join(
        [
            f"diff --git a/{asset_path} b/{asset_path}",
            "new file mode 100644",
            "index 0000000..9c942f5",
            "--- /dev/null",
            f"+++ b/{asset_path}",
            "@@ -0,0 +1,2 @@",
            "+GameObject:",
            f"+  m_Name: {filename}",
            "",
        ]
    )
