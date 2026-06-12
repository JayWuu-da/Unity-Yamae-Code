import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_init_agent_dry_run_lists_codex_and_claude_files(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--dry-run", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.agent-init.v1"
    assert payload["dry_run"] is True
    paths = {item["path"] for item in payload["files"]}
    assert "AGENTS.md" in paths
    assert "CLAUDE.md" in paths
    assert ".claude/commands/kunity-yamae.md" in paths
    assert ".codex/skills/k-unity-yamae/SKILL.md" in paths
    assert ".Yamae/AGENT_BOOTSTRAP.md" in paths
    assert ".Yamae/COMMANDS.md" in paths
    assert ".Yamae/UNITY_RULES.md" in paths


def test_init_agent_write_creates_yamae_context_pack_for_ai_agents(tmp_path: Path) -> None:
    # Given: a minimal Unity project with no AI-agent bootstrap files.
    create_minimal_project(tmp_path)
    runner = CliRunner()

    # When: init-agent writes both Codex and Claude entrypoints.
    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--write", "--json"],
    )

    # Then: the generated project includes the AI-oriented .Yamae context pack.
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    paths = {item["path"] for item in payload["files"]}
    for path in {
        "AGENTS.md",
        "CLAUDE.md",
        ".Yamae/AGENT_BOOTSTRAP.md",
        ".Yamae/COMMANDS.md",
        ".Yamae/UNITY_RULES.md",
        ".codex/skills/k-unity-yamae/SKILL.md",
        ".claude/commands/kunity-yamae.md",
    }:
        assert path in paths
        assert (tmp_path / path).exists()

    bootstrap = (tmp_path / ".Yamae" / "AGENT_BOOTSTRAP.md").read_text(encoding="utf-8")
    assert "AI Agent Bootstrap" in bootstrap
    assert "AGENTS.md" in bootstrap
    assert "CLAUDE.md" in bootstrap
    assert "kunity-yamae context" in bootstrap


def test_init_agent_refuses_to_overwrite_existing_yamae_bootstrap(tmp_path: Path) -> None:
    # Given: a Unity project already has a hand-authored .Yamae bootstrap.
    create_minimal_project(tmp_path)
    bootstrap = tmp_path / ".Yamae" / "AGENT_BOOTSTRAP.md"
    bootstrap.parent.mkdir(parents=True)
    bootstrap.write_text("existing bootstrap", encoding="utf-8")
    runner = CliRunner()

    # When: init-agent tries to write without --force.
    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--write", "--json"],
    )

    # Then: it reports a conflict and preserves existing content.
    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "conflict"
    conflicts = {item["path"] for item in payload["files"] if item["status"] == "conflict"}
    assert ".Yamae/AGENT_BOOTSTRAP.md" in conflicts
    assert bootstrap.read_text(encoding="utf-8") == "existing bootstrap"


def test_init_agent_entrypoints_route_to_yamae_bootstrap(tmp_path: Path) -> None:
    # Given: a minimal Unity project.
    create_minimal_project(tmp_path)
    runner = CliRunner()

    # When: init-agent writes both agent entrypoint families.
    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--write", "--json"],
    )

    # Then: automatic entrypoints route future agents into the .Yamae pack.
    assert result.exit_code == 0, result.output
    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    codex_skill = (
        tmp_path / ".codex" / "skills" / "k-unity-yamae" / "SKILL.md"
    ).read_text(encoding="utf-8")
    claude_command = (
        tmp_path / ".claude" / "commands" / "kunity-yamae.md"
    ).read_text(encoding="utf-8")

    assert ".Yamae/AGENT_BOOTSTRAP.md" in agents_md
    assert ".Yamae/AGENT_BOOTSTRAP.md" in claude_md
    assert ".Yamae/AGENT_BOOTSTRAP.md" in codex_skill
    assert ".Yamae/AGENT_BOOTSTRAP.md" in claude_command
    assert "kunity-yamae context" in codex_skill
    assert "kunity-yamae run" in claude_command


def test_init_agent_write_refuses_to_overwrite_existing_agents_md(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    existing = tmp_path / "AGENTS.md"
    existing.write_text("existing", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "codex", "--write", "--json"],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "conflict"
    assert existing.read_text(encoding="utf-8") == "existing"
