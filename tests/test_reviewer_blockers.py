import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main


def create_bom_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.ugui": "2.0.0"}}),
        encoding="utf-8-sig",
    )
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "UI" / "SamplePanel.prefab").write_text(
        "GameObject:\n  m_Name: SamplePanel\nCanvas:\nGraphicRaycaster:\nm_OnClick:\n",
        encoding="utf-8",
    )


def test_provider_doctor_rejects_removed_api_provider_without_traceback(tmp_path: Path) -> None:
    create_bom_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "providers", "doctor", "gemini", "--json"],
    )

    assert result.exit_code == 1, result.output
    assert "Unknown desktop integration: gemini" in result.output
    assert "traceback" not in result.output.lower()


def test_inspect_accepts_utf8_sig_manifest(tmp_path: Path) -> None:
    create_bom_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.inspect-report.v1"
    assert payload["ui"]["prefab_count"] == 1


def test_context_accepts_utf8_sig_manifest(tmp_path: Path) -> None:
    create_bom_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "context", "Fix UI raycast"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.context-pack.v1"
    assert "unity.ui" in payload["rule_cards"]
