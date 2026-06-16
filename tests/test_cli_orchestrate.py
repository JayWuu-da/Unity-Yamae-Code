import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.contracts import validate_orchestration_plan_v1


def create_runtime_spawner_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.addressables": "2.2.2"}}),
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scripts").mkdir(parents=True)
    (project_path / "Assets" / "Scripts" / "RuntimeSpawner.cs").write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class RuntimeSpawner : MonoBehaviour",
                "{",
                "    [SerializeField] private GameObject spawnPrefab;",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_orchestrate_plan_only_outputs_non_mutating_plan(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Fix sample button raycast",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_orchestration_plan_v1(payload) == payload
    assert payload["status"] == "planned"
    assert payload["patch_handoff"]["mutating_backend"] == "local-patch"
    assert payload["verification_profile"]["dry_run"] is True
    assert payload["evidence_tier"] == "planned"


def test_orchestrate_without_plan_only_outputs_failed_tool_result(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "orchestrate", "Fix sample button raycast", "--json"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.tool-call-result.v1"
    assert payload["status"] == "failed"
    assert payload["tool"] == "orchestrate"


def test_orchestrate_plan_only_includes_concrete_tool_inputs_and_results(
    tmp_path: Path,
) -> None:
    # Given
    create_runtime_spawner_project(tmp_path)
    runner = CliRunner()

    # When
    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Fix RuntimeSpawner asset spawn",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
    )

    # Then
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_orchestration_plan_v1(payload) == payload
    assert payload["patch_handoff"]["applied"] is False
    assert payload["verification_profile"]["dry_run"] is True
    assert payload["verification_profile"].get("unity_editor_verified") is not True
    tool_plan = {row["tool"]: row for row in payload["tool_plan"]}
    context_row = tool_plan["harness.context.select"]
    assert context_row["input"] == {"task": "Fix RuntimeSpawner asset spawn"}
    assert context_row["evidence_tier"] == "static_scan"
    assert context_row["result"]["status"] == "completed"
    assert "Assets/Scripts/RuntimeSpawner.cs" in context_row["result"]["result"]["relevant_files"]
    verify_row = tool_plan["unity.verify.plan"]
    assert verify_row["input"]["compile_check"] is True
    assert verify_row["result"]["result"]["commands"]
    memory_row = tool_plan["harness.memory.record"]
    assert memory_row["result"]["status"] == "unavailable"
    player_row = tool_plan["unity.player.status"]
    assert player_row["result"]["status"] == "unavailable"
