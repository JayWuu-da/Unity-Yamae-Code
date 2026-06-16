import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.agents.base import BaseAgent
from kunity_yamae.cli import main
from kunity_yamae.config import load_config
from kunity_yamae.desktop_integration import claude_command, claude_skill, codex_skill
from tests.fixtures.make_unity_project import create_minimal_project


class PromptOnlyAgent(BaseAgent):
    def execute(self, task, project_path, risk_report, mode, ledger):
        return {}


def test_codex_entrypoints_use_agents_md_and_repo_skill_location(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "codex", "--dry-run", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    paths = {item["path"] for item in payload["files"]}
    assert "AGENTS.md" in paths
    assert ".agents/skills/k-unity-yamae/SKILL.md" in paths
    assert ".codex/skills/k-unity-yamae/SKILL.md" not in paths

    write_result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "codex", "--write", "--json"],
    )
    assert write_result.exit_code == 0, write_result.output
    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    skill = (tmp_path / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "python -m pytest -q" in agents_md
    assert "python -m ruff check ." in agents_md
    assert "Do not claim Unity Editor" in agents_md
    assert "Codex App" in skill
    assert "Codex CLI" in skill
    assert "Windows PowerShell" in skill
    assert "kunity-yamae run \"$TASK\" --plan-only --verify-dry-run --json" in skill
    assert "--patch-file proposed.diff --guarded-agent-patch --json" in skill
    assert "--agent codex" not in skill


def test_claude_entrypoints_include_skill_command_and_windows_guidance(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "claude", "--write", "--json"],
    )

    assert result.exit_code == 0, result.output
    paths = {item["path"] for item in json.loads(result.output)["files"]}
    assert "CLAUDE.md" in paths
    assert ".claude/skills/k-unity-yamae/SKILL.md" in paths
    assert ".claude/commands/kunity-yamae.md" in paths

    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    skill = (tmp_path / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    command = (tmp_path / ".claude" / "commands" / "kunity-yamae.md").read_text(
        encoding="utf-8"
    )
    assert "Claude Code Desktop" in skill
    assert "Claude CLI" in skill
    assert "Git for Windows" in skill
    assert "Windows PowerShell" in claude_md
    assert "kunity-yamae context --pretty \"$ARGUMENTS\"" in command
    assert "/k-unity-yamae" in command
    assert "--patch-file proposed.diff --guarded-agent-patch --json" in skill


def test_install_writes_official_skill_locations(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "install", "--codex", "--claude"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "commands" / "kunity-yamae.md").exists()
    assert not (tmp_path / ".codex" / "skills" / "k-unity-yamae" / "SKILL.md").exists()


def test_checked_in_desktop_entrypoints_match_generated_templates() -> None:
    codex_path = Path(".agents/skills/k-unity-yamae/SKILL.md")
    claude_skill_path = Path(".claude/skills/k-unity-yamae/SKILL.md")
    claude_command_path = Path(".claude/commands/kunity-yamae.md")

    assert codex_path.read_text(encoding="utf-8") == codex_skill()
    assert claude_skill_path.read_text(encoding="utf-8") == claude_skill()
    assert claude_command_path.read_text(encoding="utf-8") == claude_command()


def test_no_openai_api_provider_surface_remains(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "providers", "doctor", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    serialized = json.dumps(payload)
    assert payload["schema"] == "unity-harness.desktop-integration-doctor.v1"
    assert "providers" not in payload
    assert "openai" not in serialized.lower()
    assert "OPENAI" + "_API_KEY" not in serialized
    assert set(payload["integrations"]) == {
        "codex-app",
        "codex-cli",
        "claude-code-desktop",
        "claude-cli",
    }


def test_agent_prompt_prefers_unified_diff_for_guarded_flow(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    config = load_config(tmp_path)
    agent = PromptOnlyAgent("prompt-only", config, {})
    risk_report = {
        "risk_score": 30,
        "triggers": [],
        "required_rule_cards": [],
        "blocked_operations": [],
    }

    prompt = agent._build_prompt("Fix UI button", risk_report, "standard", tmp_path)

    assert "unified diff" in prompt
    assert "--guarded-agent-patch" in prompt
    assert "Do not use FILE/ACTION/CONTENT" in prompt


def test_generated_entrypoints_describe_task10_operability_contracts() -> None:
    entrypoints = "\n".join(
        [
            codex_skill(),
            claude_skill(),
            claude_command(),
        ]
    )
    entrypoints_lower = entrypoints.lower()

    assert "shared inventory" in entrypoints_lower
    assert "bounded generic semantic signals" in entrypoints_lower
    assert "kunity-yamae tools list --json" in entrypoints
    assert "kunity-yamae orchestrate" in entrypoints
    assert "non-mutating" in entrypoints_lower
    assert ".unity-harness/cache/" in entrypoints
    assert "do not claim unity editor, playmode, build, or inspector" in entrypoints_lower
