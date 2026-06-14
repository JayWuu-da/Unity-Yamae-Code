import re
from pathlib import Path

ENTRYPOINTS = [
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path(".agents/skills/k-unity-yamae/SKILL.md"),
    Path(".claude/skills/k-unity-yamae/SKILL.md"),
    Path(".claude/commands/kunity-yamae.md"),
]


def test_entrypoints_enforce_discovered_facts_only_contract() -> None:
    for path in ENTRYPOINTS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"/path/to|OPENAI_API_KEY|ANTHROPIC_API_KEY|--agent openai|--agent claude",
            text,
            flags=re.IGNORECASE,
        ), path
        assert re.search(
            r"discovered facts|discovered files|found in the current Unity project",
            text,
            flags=re.IGNORECASE,
        ), path
        assert "editor-probe" in text or "Editor probe" in text


def test_codex_and_claude_surfaces_use_official_project_skill_roles() -> None:
    codex = Path(".agents/skills/k-unity-yamae/SKILL.md").read_text(encoding="utf-8")
    claude = Path(".claude/skills/k-unity-yamae/SKILL.md").read_text(encoding="utf-8")
    command = Path(".claude/commands/kunity-yamae.md").read_text(encoding="utf-8")

    assert re.search(r"^name:\s*k-unity-yamae$", codex, re.MULTILINE)
    assert re.search(r"^description:", codex, re.MULTILINE)
    assert "primary" in claude.lower()
    assert "compatibility" in command.lower()
