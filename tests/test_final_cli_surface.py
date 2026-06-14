import json
from pathlib import Path

from click.testing import CliRunner

import kunity_yamae.cli_context as cli_context
from kunity_yamae.cli import main


def create_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "ProjectSettings" / "ProjectSettings.asset").write_text(
        "activeInputHandler: 2\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "com.unity.ugui": "2.0.0",
                    "com.unity.inputsystem": "1.8.2",
                }
            }
        ),
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scenes").mkdir(parents=True)
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "Art").mkdir(parents=True)
    (project_path / "Assets" / "Scenes" / "Main.unity").write_text(
        "\n".join(
            [
                "GameObject:",
                "  m_Name: MainCanvas",
                "Canvas:",
                "GraphicRaycaster:",
                "EventSystem:",
                "PrefabInstance:",
                "  m_SourcePrefab: {fileID: 100100000, guid: shopbutton, type: 3}",
            ]
        ),
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI" / "ShopButton.prefab").write_text(
        "\n".join(
            [
                "GameObject:",
                "  m_Name: ShopButton",
                "MonoBehaviour:",
                "  m_Script: {fileID: 11500000, guid: 00000000000000000000000000000000, type: 3}",
                "Canvas:",
                "GraphicRaycaster:",
                "m_OnClick:",
            ]
        ),
        encoding="utf-8",
    )
    (project_path / "Assets" / "Art" / "Hero.png.meta").write_text(
        "\n".join(
            [
                "TextureImporter:",
                "  maxTextureSize: 4096",
                "  platformSettings:",
                "  - buildTarget: Android",
                "    textureCompression: ASTC",
                "  - buildTarget: iPhone",
                "    textureCompression: ASTC",
            ]
        ),
        encoding="utf-8",
    )


def test_install_command_writes_codex_and_claude_entrypoints(tmp_path: Path) -> None:
    create_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "install", "--codex", "--claude"])

    assert result.exit_code == 0, result.output
    codex_skill = tmp_path / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md"
    claude_skill = tmp_path / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md"
    claude_command = tmp_path / ".claude" / "commands" / "kunity-yamae.md"
    assert codex_skill.exists()
    assert claude_skill.exists()
    assert claude_command.exists()
    assert "kunity-yamae context --pretty" in codex_skill.read_text(encoding="utf-8")
    assert "kunity-yamae run" in claude_command.read_text(encoding="utf-8")


def test_install_command_defaults_to_both_entrypoints(tmp_path: Path) -> None:
    create_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "install"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "commands" / "kunity-yamae.md").exists()


def test_providers_doctor_json_reports_desktop_integrations(tmp_path: Path) -> None:
    create_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "providers", "doctor", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.desktop-integration-doctor.v1"
    assert set(payload["integrations"]) == {
        "codex-app",
        "codex-cli",
        "claude-code-desktop",
        "claude-cli",
    }
    assert "OPENAI" + "_API_KEY" not in result.output
    assert "ANTHROPIC" + "_API_KEY" not in result.output


def test_desktop_integration_status_reports_missing_entrypoints(tmp_path: Path) -> None:
    import kunity_yamae.cli_providers as cli_providers

    create_project(tmp_path)

    doctor = cli_providers.build_provider_doctor({}, project_path=tmp_path)

    assert doctor["integrations"]["codex-cli"]["status"] == "not_installed"
    assert doctor["integrations"]["claude-cli"]["status"] == "not_installed"
    assert doctor["offline_handoffs"]["local-patch"]["status"] == "ready"


def test_context_command_is_shallow_by_default(tmp_path: Path, monkeypatch) -> None:
    create_project(tmp_path)
    calls = []
    original_scan = cli_context.UnityProjectScanner.scan

    def capture_scan(self, deep: bool = False):
        calls.append(deep)
        return original_scan(self, deep=deep)

    monkeypatch.setattr(cli_context.UnityProjectScanner, "scan", capture_scan)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "context", "Fix UI button"])

    assert result.exit_code == 0, result.output
    assert calls == [False]


def test_inspect_json_reports_hierarchy_prefabs_and_platform_graphics(
    tmp_path: Path,
) -> None:
    create_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.inspect-report.v1"
    assert payload["hierarchy"]["scene_count"] == 1
    assert payload["hierarchy"]["prefab_instance_count"] == 1
    assert payload["ui"]["event_system_count"] == 1
    assert payload["prefabs"]["missing_script_count"] == 1
    assert payload["graphics"]["platform_overrides"]["Android"] == 1
    assert payload["graphics"]["platform_overrides"]["iPhone"] == 1
    assert payload["editor_probe"]["status"] == "unavailable"


def test_readme_documents_final_cli_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "kunity-yamae install --codex --claude" in readme
    assert "kunity-yamae providers doctor --json" in readme
    assert "kunity-yamae inspect --json" in readme
    assert "kunity-yamae context --pretty" in readme


def test_docs_document_desktop_cli_entrypoint_contract() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_ko = Path("README_KO.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "kunity-yamae init-agent --target both --write" in readme
    assert ".agents/skills/k-unity-yamae/SKILL.md" in readme
    assert ".agents/skills/k-unity-yamae/SKILL.md" in readme_ko
    assert ".agents/skills/k-unity-yamae/SKILL.md" in release_checklist
    assert ".claude/skills/k-unity-yamae/SKILL.md" in release_checklist
    assert ".claude/commands/kunity-yamae.md" in release_checklist


def test_run_help_matches_documented_disable_flags() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["run", "--help"])

    assert result.exit_code == 0, result.output
    assert "--no-verify" in result.output
    assert "--no-guard" in result.output
