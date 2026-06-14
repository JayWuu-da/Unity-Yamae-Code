import re
from pathlib import Path


def test_readme_is_agent_handoff_not_human_cli_manual() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    forbidden = [
        "## Quick Start",
        "## CLI Commands",
        "/path/to/your/unity/project",
        "human-facing standalone CLI",
    ]

    assert [text for text in forbidden if text in readme] == []
    assert re.search(r"kunity-yamae\s+\w+\s+--project", readme) is None
    assert "AI-agent Unity harness" in readme
    assert "git URL" in readme
    assert "python -m pip install -e ." in readme
    assert "current Unity project root" in readme
    assert ".agents/skills/k-unity-yamae/SKILL.md" in readme
    assert ".claude/skills/k-unity-yamae/SKILL.md" in readme


def test_readme_states_static_facts_and_editor_probe_boundary() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert not re.search(
        r"understands every Unity project|universal understanding|complete Inspector object graph",
        readme,
        flags=re.IGNORECASE,
    )
    assert re.search(r"discovered facts|discovered files", readme, flags=re.IGNORECASE)
    assert "editor-probe" in readme
