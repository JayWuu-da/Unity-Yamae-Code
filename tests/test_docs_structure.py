from pathlib import Path

PACKAGE_ROOT = Path("kunity_yamae")


def test_architecture_docs_name_refactored_modules() -> None:
    docs = "\n".join(
        [
            Path("README.md").read_text(encoding="utf-8"),
            Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8"),
        ]
    )
    required_modules = [
        "cli_run_payload.py",
        "cli_run_steps.py",
        "unity_verification_plan.py",
        "unity_verification_steps.py",
        "unity_verification_support.py",
        "unity_profile_graphics.py",
        "unity_profile_common.py",
        "unity_profile_architecture.py",
    ]
    missing = [module for module in required_modules if module not in docs]

    assert missing == []


def test_architecture_docs_match_current_package_modules() -> None:
    architecture = Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    focused_modules = {
        path.name
        for path in PACKAGE_ROOT.glob("*.py")
        if path.name.startswith(("cli_run", "run_pipeline", "unity_verification", "unity_profile"))
    }
    missing = sorted(module for module in focused_modules if module not in architecture)

    assert missing == []


def test_readme_avoids_stale_test_counts() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Test suite (14 tests)" not in readme
    assert "101 passed" not in readme


def test_docs_capture_windows_desktop_skill_contract() -> None:
    docs = "\n".join(
        [
            Path("README.md").read_text(encoding="utf-8"),
            Path("docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8"),
        ]
    )

    assert ".agents/skills/k-unity-yamae/SKILL.md" in docs
    assert ".claude/skills/k-unity-yamae/SKILL.md" in docs
    assert ".claude/commands/kunity-yamae.md" in docs
    assert "PowerShell" in docs
    assert "Git for Windows" in docs
    assert ".codex/skills" not in docs


def test_docs_exclude_api_provider_surface() -> None:
    docs = "\n".join(
        [
            Path("README.md").read_text(encoding="utf-8"),
            Path("README_KO.md").read_text(encoding="utf-8"),
            Path("docs/ANALYSIS.md").read_text(encoding="utf-8"),
            Path("docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8"),
            Path(".agents/skills/k-unity-yamae/SKILL.md").read_text(encoding="utf-8"),
            Path(".claude/skills/k-unity-yamae/SKILL.md").read_text(encoding="utf-8"),
            Path(".claude/commands/kunity-yamae.md").read_text(encoding="utf-8"),
        ]
    ).lower()

    assert "openai api" not in docs
    assert "--agent " + "openai" not in docs
    assert "openai_api_key" not in docs
    assert "anthropic_api_key" not in docs
    assert "api-backed" not in docs
    assert "provider" + "-backed" not in docs
    assert "api provider" not in docs
    assert '".[' + "agents]" + '"' not in docs
    assert "agent sdk" not in docs


def test_readme_is_concise_and_delegates_deep_details() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    line_count = len(readme.splitlines())

    assert line_count < 950
    assert "## Adding a Custom Agent" not in readme
    assert "class CustomAgent" not in readme
    assert "docs/ARCHITECTURE.md" in readme


def test_task10_docs_capture_shared_inventory_and_static_signal_limits() -> None:
    docs = "\n".join(
        [
            Path("README.md").read_text(encoding="utf-8"),
            Path("README_KO.md").read_text(encoding="utf-8"),
            Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8"),
            Path("docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8"),
        ]
    )
    docs_lower = docs.lower()

    assert "shared inventory" in docs_lower
    assert "bounded generic semantic signals" in docs_lower
    assert "tools list --json" in docs_lower
    assert "orchestrate" in docs_lower
    assert ".unity-harness/cache/" in docs
    assert "do not prove Inspector object references" in docs
    assert "do not claim unity editor, playmode, build, or inspector verification" in docs_lower
