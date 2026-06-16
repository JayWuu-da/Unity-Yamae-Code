import json
import re
import subprocess
from pathlib import Path

import click

from .agents import list_agents
from .cli_orchestrate import orchestrate_cmd
from .cli_run import run_cmd
from .cli_tools import tools_cmd
from .cli_verify import verify_cmd
from .project_assumption_hygiene import collect_project_assumption_hygiene

QUALITY_GATES = ["python -m pytest -q", "python -m ruff check ."]
_ARTIFACT_HYGIENE_MARKERS = (
    ".unity-harness/cache/",
    ".unity-harness/reports/",
    ".unity-harness/last-",
    "scratch planning/evidence artifacts",
)
_FORBIDDEN_VERIFICATION_CLAIMS = (
    "unity editor verification passed",
    "playmode verification passed",
    "inspector verification passed",
    "editor verification passed",
    "build verification passed",
    "game view verification passed",
)


@click.command("release-check")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def release_check_cmd(ctx, as_json: bool) -> None:
    package_root = Path(__file__).resolve().parent.parent
    package_data = _collect_package_data(package_root)
    desktop_integration = _collect_desktop_integration(package_root)
    agent_facing_copy = _collect_agent_facing_copy(package_root)
    project_assumption_hygiene = collect_project_assumption_hygiene(package_root)
    failed = [
        *[f"package_data.{key}" for key, value in package_data.items() if not value],
        *[f"desktop_integration.{key}" for key, value in desktop_integration.items() if not value],
        *[
            f"agent_facing_copy.{key}"
            for key, value in agent_facing_copy.items()
            if not value
        ],
        *([] if project_assumption_hygiene["passed"] else ["project_assumption_hygiene"]),
    ]
    payload = {
        "schema": "unity-harness.release-check.v1",
        "status": "failed" if failed else "passed",
        "package_root": str(package_root),
        "project_path": str(ctx.obj["project_path"]),
        "package_data": package_data,
        "desktop_integration": desktop_integration,
        "agent_facing_copy": agent_facing_copy,
        "project_assumption_hygiene": project_assumption_hygiene,
        "cli_surface": _collect_cli_surface(),
        "agent_registry": _collect_agent_registry(),
        "quality_gates": QUALITY_GATES,
        "failed_checks": failed,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        if failed:
            ctx.exit(2)
        return

    click.echo(f"status: {payload['status']}")
    for key, value in package_data.items():
        click.echo(f"{key}: {value}")
    if failed:
        ctx.exit(2)


def _collect_package_data(package_root: Path) -> dict[str, int | bool]:
    return {
        "config_default": (package_root / "config" / "default.yml").exists(),
        "rule_cards": len(list((package_root / "kunity_yamae" / "rules").glob("*.md"))),
        "editor_sources": len(list((package_root / "Editor").glob("*.cs"))),
        "release_checklist": (package_root / "docs" / "RELEASE_CHECKLIST.md").exists(),
    }


def _collect_desktop_integration(package_root: Path) -> dict[str, bool]:
    codex_skill = package_root / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md"
    claude_skill = package_root / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md"
    claude_command = package_root / ".claude" / "commands" / "kunity-yamae.md"
    return {
        "agents_md": (package_root / "AGENTS.md").exists(),
        "codex_skill": codex_skill.exists(),
        "claude_md": (package_root / "CLAUDE.md").exists(),
        "claude_skill": claude_skill.exists(),
        "claude_command": claude_command.exists(),
        "no_legacy_codex_skill": not _legacy_codex_skill_path(package_root).exists(),
        "codex_skill_mentions_guarded_patch": _file_contains(codex_skill, "--guarded-agent-patch"),
        "codex_skill_mentions_tools_list": _file_contains(codex_skill, "tools list --json"),
        "codex_skill_mentions_orchestrate": _file_contains(codex_skill, "orchestrate"),
        "codex_skill_mentions_shared_inventory": _file_contains(codex_skill, "shared inventory"),
        "claude_skill_mentions_git_for_windows": _file_contains(claude_skill, "Git for Windows"),
        "claude_skill_mentions_orchestrate": _file_contains(claude_skill, "orchestrate"),
        "claude_skill_mentions_shared_inventory": _file_contains(claude_skill, "shared inventory"),
        "claude_command_mentions_plan_only": _file_contains(claude_command, "--plan-only"),
    }


def _collect_cli_surface() -> dict[str, bool]:
    run_option_names = {
        option
        for parameter in run_cmd.params
        for option in [
            *getattr(parameter, "opts", []),
            *getattr(parameter, "secondary_opts", []),
        ]
    }
    orchestrate_option_names = _click_option_names(orchestrate_cmd)
    verify_option_names = _click_option_names(verify_cmd)
    tools_list = tools_cmd.commands["list"]
    tools_call = tools_cmd.commands["call"]
    return {
        "run_has_guarded_agent_patch": "--guarded-agent-patch" in run_option_names,
        "run_has_apply_agent_patch": "--apply-agent-patch" in run_option_names,
        "run_has_no_verify": "--no-verify" in run_option_names,
        "run_has_no_guard": "--no-guard" in run_option_names,
        "tools_command_registered": tools_cmd.name == "tools",
        "tools_list_has_schema": "--schema" in _click_option_names(tools_list),
        "tools_call_has_schema": "--schema" in _click_option_names(tools_call),
        "orchestrate_command_registered": orchestrate_cmd.name == "orchestrate",
        "orchestrate_has_execute_loop": "--execute-loop" in orchestrate_option_names,
        "orchestrate_has_schema": "--schema" in orchestrate_option_names,
        "verify_has_quality_gate": "--quality-gate" in verify_option_names,
    }


def _collect_agent_facing_copy(package_root: Path) -> dict[str, bool]:
    docs = _primary_docs_text(package_root)
    readme = _read_text(package_root / "README.md")
    readme_ko = _read_text(package_root / "README_KO.md")
    entrypoints = "\n".join(
        [
            _read_text(package_root / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md"),
            _read_text(package_root / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md"),
            _read_text(package_root / ".claude" / "commands" / "kunity-yamae.md"),
            _read_text(package_root / "AGENTS.md"),
            _read_text(package_root / "CLAUDE.md"),
            _read_text(package_root / "kunity_yamae" / "desktop_integration.py"),
        ]
    )
    lowered = docs.lower()
    return {
        "readme_agent_workflow": all(
            text in readme
            for text in [
                "AI-agent Unity harness",
                "git URL",
                "current Unity project root",
                "python -m pip install -e .",
            ]
        ),
        "readme_ko_agent_workflow": all(
            text in readme_ko
            for text in [
                "AI 에이전트용 Unity 하네스",
                "git URL",
                "현재 Unity 프로젝트 루트",
            ]
        ),
        "entrypoints_discovered_facts": bool(
            re.search(
                r"discovered facts|discovered files|found in the current Unity project",
                entrypoints,
                flags=re.IGNORECASE,
            )
            and "editor-probe" in entrypoints
        ),
        "entrypoints_mention_non_mutating_orchestrate": (
            "kunity-yamae orchestrate" in entrypoints and "non-mutating" in entrypoints
        ),
        "docs_mention_shared_inventory": "shared inventory" in lowered,
        "docs_bound_generic_semantic_signals": (
            "bounded generic semantic signals" in lowered
            and "do not prove inspector object references" in lowered
        ),
        "docs_mention_artifact_hygiene": _mentions_artifact_hygiene(docs),
        "entrypoints_mention_concrete_tools_orchestrate": (
            "kunity-yamae tools list --json" in entrypoints
            and "kunity-yamae orchestrate" in entrypoints
            and "--plan-only --verify-dry-run --json" in entrypoints
            and "non-mutating" in entrypoints
        ),
        "entrypoints_mention_artifact_hygiene": _mentions_artifact_hygiene(entrypoints),
        "no_unity_verification_overclaim": _avoids_unity_verification_overclaim(
            docs + "\n" + entrypoints
        ),
        "docs_static_limits": bool(
            re.search(r"discovered static facts|static facts|signals", docs)
            and re.search(r"editor-probe|Editor probe|에디터 프로브", docs)
        ),
        "no_forbidden_path_placeholders": not bool(
            re.search(
                r"/path/to/UnityProject|/path/to/your/unity/project|kunity-yamae\s+\w+\s+--project",
                docs,
            )
        ),
        "no_api_provider_surface": not any(
            text in lowered
            for text in [
                "openai api",
                "--agent openai",
                "openai_api_key",
                "anthropic_api_key",
                "api-backed",
                "provider-backed",
                "api provider",
                "agent sdk",
            ]
        ),
        "tracked_artifact_hygiene": _tracked_artifact_hygiene(package_root),
    }


def _primary_docs_text(package_root: Path) -> str:
    paths = [
        package_root / "README.md",
        package_root / "README_KO.md",
        package_root / "AGENTS.md",
        package_root / "CLAUDE.md",
        package_root / "docs" / "ANALYSIS.md",
        package_root / "docs" / "ARCHITECTURE.md",
        package_root / "docs" / "RELEASE_CHECKLIST.md",
        package_root / "docs" / "UPGRADE_REPORT.md",
        package_root / "CONTRIBUTING.md",
        package_root / ".agents" / "skills" / "k-unity-yamae" / "SKILL.md",
        package_root / ".claude" / "skills" / "k-unity-yamae" / "SKILL.md",
        package_root / ".claude" / "commands" / "kunity-yamae.md",
        package_root / "kunity_yamae" / "desktop_integration.py",
    ]
    return "\n".join(_read_text(path) for path in paths)


def _tracked_artifact_hygiene(package_root: Path) -> bool:
    tracked = subprocess.check_output(
        ["git", "ls-files", ".omo", ".omx", "plans", "evidence"],
        cwd=package_root,
        text=True,
    )
    return not any(has_tracked_scratch_artifact(line) for line in tracked.splitlines())


def _mentions_artifact_hygiene(text: str) -> bool:
    return all(
        marker in text
        for marker in _ARTIFACT_HYGIENE_MARKERS
    )


def _avoids_unity_verification_overclaim(text: str) -> bool:
    lowered = text.lower()
    return (
        not any(claim in lowered for claim in _FORBIDDEN_VERIFICATION_CLAIMS)
        and "do not claim unity editor" in lowered
        and "unless that tier actually ran" in lowered
    )


def _legacy_codex_skill_path(package_root: Path) -> Path:
    return package_root / ".codex" / "skills" / "k-unity-yamae" / "SKILL.md"


def has_tracked_scratch_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith((".omo/", ".omx/", "plans/", "evidence/"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _file_contains(path: Path, needle: str) -> bool:
    return path.exists() and needle in path.read_text(encoding="utf-8")


def _click_option_names(command) -> set[str]:
    return {
        option
        for parameter in command.params
        for option in [
            *getattr(parameter, "opts", []),
            *getattr(parameter, "secondary_opts", []),
        ]
    }


def _collect_agent_registry() -> dict[str, int | bool]:
    agents = set(list_agents())
    return {
        "local_patch": "local-patch" in agents,
        "count": len(agents),
    }
