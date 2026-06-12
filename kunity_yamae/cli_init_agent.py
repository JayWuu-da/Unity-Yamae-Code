import json
from pathlib import Path

import click


@click.command("init-agent")
@click.option(
    "--target",
    type=click.Choice(["codex", "claude", "both"]),
    default="both",
)
@click.option("--dry-run", is_flag=True, help="Preview files without writing.")
@click.option("--write", "write_files", is_flag=True, help="Write integration files.")
@click.option("--force", is_flag=True, help="Overwrite existing integration files.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def init_agent_cmd(
    ctx,
    target: str,
    dry_run: bool,
    write_files: bool,
    force: bool,
    as_json: bool,
) -> None:
    project_path: Path = ctx.obj["project_path"]
    effective_dry_run = dry_run or not write_files
    files = _target_files(target)
    statuses = [_file_status(project_path, path, content, force) for path, content in files.items()]
    conflicts = [item for item in statuses if item["status"] == "conflict"]

    payload = {
        "schema": "unity-harness.agent-init.v1",
        "status": "conflict" if conflicts else "ok",
        "target": target,
        "dry_run": effective_dry_run,
        "files": statuses,
    }
    if conflicts:
        _emit(payload, as_json)
        ctx.exit(2)
    if not effective_dry_run:
        for path, content in files.items():
            target_path = project_path / path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
    _emit(payload, as_json)


def _target_files(target: str) -> dict[str, str]:
    files: dict[str, str] = _yamae_files()
    if target in {"codex", "both"}:
        files["AGENTS.md"] = _agents_md()
        files[".codex/skills/k-unity-yamae/SKILL.md"] = _codex_skill()
    if target in {"claude", "both"}:
        files["CLAUDE.md"] = _claude_md()
        files[".claude/commands/kunity-yamae.md"] = _claude_command()
    return files


def _yamae_files() -> dict[str, str]:
    return {
        ".Yamae/AGENT_BOOTSTRAP.md": _agent_bootstrap_md(),
        ".Yamae/COMMANDS.md": _commands_md(),
        ".Yamae/UNITY_RULES.md": _unity_rules_md(),
    }


def _file_status(project_path: Path, path: str, content: str, force: bool) -> dict:
    target = project_path / path
    if target.exists() and not force:
        status = "conflict"
    elif target.exists():
        status = "overwrite"
    else:
        status = "create"
    return {"path": path, "status": status, "bytes": len(content.encode("utf-8"))}


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    for item in payload["files"]:
        click.echo(f"{item['status']}: {item['path']}")


def _agents_md() -> str:
    return "\n".join(
        [
            "# K-Unity-Yamae AI Agent Instructions",
            "",
            "Before editing this Unity project, read `.Yamae/AGENT_BOOTSTRAP.md`.",
            "",
            "Before Unity production edits, run:",
            "",
            "```bash",
            'kunity-yamae context --pretty "$TASK"',
            'kunity-yamae risk --json "$TASK"',
            "```",
            "",
            "Use `kunity-yamae inspect --editor-probe --json` only when Inspector, "
            "prefab, scene, or listener certainty is required.",
            "Do not directly edit Unity YAML assets or .meta files.",
            "Do not claim Unity Editor, PlayMode, or build verification unless that "
            "tier actually ran.",
        ]
    )


def _codex_skill() -> str:
    return "\n".join(
        [
            "---",
            "name: k-unity-yamae",
            "description: Unity production harness context, risk, guard, and "
            "verification workflow.",
            "---",
            "",
            "# K-Unity-Yamae",
            "",
            "Read `.Yamae/AGENT_BOOTSTRAP.md` before editing Unity code.",
            "Run `kunity-yamae providers doctor --json` before provider-backed work.",
            "Run `kunity-yamae context --pretty \"$TASK\"` before editing Unity code.",
            "Run `kunity-yamae run \"$TASK\" --plan-only --json` for a lightweight harness plan.",
        ]
    )


def _claude_md() -> str:
    return "\n".join(
        [
            "# K-Unity-Yamae",
            "",
            "Read `.Yamae/AGENT_BOOTSTRAP.md` before Unity edits.",
            "Use `kunity-yamae context --pretty \"$ARGUMENTS\"` before Unity edits.",
            "Use `kunity-yamae providers doctor --json` before provider calls.",
            "Keep Unity batchmode and live provider checks opt-in unless risk requires them.",
        ]
    )


def _claude_command() -> str:
    return "\n".join(
        [
            "# kunity-yamae",
            "",
            "Read `.Yamae/AGENT_BOOTSTRAP.md` first.",
            "",
            "```bash",
            'kunity-yamae context --pretty "$ARGUMENTS"',
            'kunity-yamae run "$ARGUMENTS" --plan-only --json',
            "```",
        ]
    )


def _agent_bootstrap_md() -> str:
    return "\n".join(
        [
            "# AI Agent Bootstrap",
            "",
            "This Unity project is configured for AI coding agents through K-Unity-Yamae.",
            "This file is for agents, not human onboarding.",
            "",
            "## Required Order",
            "",
            "1. Read `AGENTS.md` or `CLAUDE.md` from the project root.",
            "2. Read this `.Yamae/AGENT_BOOTSTRAP.md` file.",
            "3. Run `kunity-yamae context --pretty \"$TASK\"` before editing Unity code.",
            "4. Run `kunity-yamae risk --json \"$TASK\"` before choosing the edit scope.",
            "5. After edits, run the matching guard and verification commands from "
            "`.Yamae/COMMANDS.md`.",
            "",
            "## Operating Rules",
            "",
            "- Keep Unity edits surgical and scoped to the requested behavior.",
            "- Treat `.meta`, `.prefab`, `.unity`, `.asset`, `.controller`, `.anim`, "
            "and `.asmdef` changes as high risk.",
            "- Do not claim Unity Editor, PlayMode, build, or visual verification "
            "unless it actually ran.",
            "- Prefer static guard evidence when Unity Editor is unavailable, and report "
            "that limitation clearly.",
            "- Use one writer agent for file mutation; parallel agents may do read-only analysis.",
        ]
    )


def _commands_md() -> str:
    return "\n".join(
        [
            "# K-Unity-Yamae Agent Commands",
            "",
            "Use these commands from the Unity project root.",
            "",
            "## Context Before Editing",
            "",
            "```bash",
            'kunity-yamae context --pretty "$TASK"',
            'kunity-yamae risk --json "$TASK"',
            "```",
            "",
            "## Plan Without Mutating Files",
            "",
            "```bash",
            'kunity-yamae run "$TASK" --plan-only --verify-dry-run --json',
            "```",
            "",
            "## Guard Current Diff",
            "",
            "```bash",
            "kunity-yamae guard-diff --json",
            "```",
            "",
            "## Verification Plan",
            "",
            "```bash",
            "kunity-yamae verify --dry-run --json --qa-level standard",
            "```",
        ]
    )


def _unity_rules_md() -> str:
    return "\n".join(
        [
            "# Unity Agent Rules",
            "",
            "## High-Risk Files",
            "",
            "- Do not directly edit `.meta` files unless the task is explicitly about "
            "GUID/import metadata.",
            "- Do not directly edit `.unity`, `.prefab`, `.asset`, `.controller`, or "
            "`.anim` YAML without a guard plan.",
            "- Do not rename serialized fields without checking prefab, scene, and asset "
            "references.",
            "- Do not move runtime scripts across asmdef boundaries without checking "
            "assembly references.",
            "",
            "## Runtime Boundaries",
            "",
            "- Keep Editor-only APIs under Editor assemblies or Editor folders.",
            "- Do not add UnityEditor references to runtime code.",
            "- Do not widen server/API/socket behavior unless the user explicitly "
            "requested that surface.",
            "",
            "## Reporting",
            "",
            "- Separate what changed, what was verified, and what could not be verified.",
            "- If Unity Editor was unavailable, say that only static checks ran.",
        ]
    )
