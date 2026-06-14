import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main


def create_minimal_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {}}),
        encoding="utf-8",
    )
    (project_path / "Assets").mkdir()


def test_provider_doctor_reports_desktop_cli_integrations_without_api_keys(
    tmp_path: Path,
) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "providers",
            "doctor",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.desktop-integration-doctor.v1"
    assert set(payload["integrations"]) == {
        "codex-app",
        "codex-cli",
        "claude-code-desktop",
        "claude-cli",
    }
    for integration in payload["integrations"].values():
        assert "requires_" + "api_key" not in integration
        assert integration["status"] in {"ready", "not_installed"}
    assert "api_key" not in result.output.lower()
    assert "traceback" not in result.output.lower()


def test_provider_doctor_rejects_openai_api_provider(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "providers",
            "doctor",
            "openai",
            "--json",
        ],
    )

    assert result.exit_code == 1, result.output
    assert "Unknown desktop integration: openai" in result.output
    assert "OPENAI" + "_API_KEY" not in result.output
