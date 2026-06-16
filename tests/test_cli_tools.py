import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.contracts import validate_tool_registry_v1, validate_tool_spec_v1


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


def test_tools_list_outputs_registry_contract(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "tools", "list", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_tool_registry_v1(payload) == payload
    assert "unity.verify.plan" in [tool["name"] for tool in payload["tools"]]


def test_tools_show_outputs_spec_contract(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "tools", "show", "unity.verify.plan", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_tool_spec_v1(payload) == payload
    assert payload["name"] == "unity.verify.plan"


def test_tools_call_risk_classify_outputs_tool_result(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "tools",
            "call",
            "harness.risk.classify",
            "--payload-json",
            '{"task":"Fix sample button raycast"}',
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.tool-call-result.v1"
    assert payload["status"] == "completed"
    assert payload["tool"] == "harness.risk.classify"
    assert payload["evidence_tier"] == "static_scan"


def test_tools_call_invalid_json_exits_with_failed_contract(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "tools",
            "call",
            "harness.risk.classify",
            "--payload-json",
            "{bad",
            "--json",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.tool-call-result.v1"
    assert payload["status"] == "failed"


def test_tools_call_context_select_outputs_real_context_pack(tmp_path: Path) -> None:
    # Given
    create_runtime_spawner_project(tmp_path)
    runner = CliRunner()

    # When
    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "tools",
            "call",
            "harness.context.select",
            "--payload-json",
            '{"task":"Fix RuntimeSpawner asset spawn"}',
            "--json",
        ],
    )

    # Then
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.tool-call-result.v1"
    assert payload["tool"] == "harness.context.select"
    assert payload["status"] == "completed"
    context = payload["result"]
    assert context["schema"] == "unity-harness.context-pack.v1"
    assert context["fact_limits"]["unknown_policy"]
    assert "Assets/Scripts/RuntimeSpawner.cs" in context["relevant_files"]
    assert context["risk_report"]["task"] == "Fix RuntimeSpawner asset spawn"
