import json
from pathlib import Path

import click

from .desktop_integration import claude_init_files, codex_init_files


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
    files: dict[str, str] = {}
    if target in {"codex", "both"}:
        files.update(codex_init_files())
    if target in {"claude", "both"}:
        files.update(claude_init_files())
    return files


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
