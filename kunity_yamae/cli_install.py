from pathlib import Path

import click

from .desktop_integration import claude_install_files, codex_install_files


@click.command("install")
@click.option("--codex", is_flag=True, help="Install the repo-local Codex skill.")
@click.option("--claude", is_flag=True, help="Install repo-local Claude Code skill and command.")
@click.pass_context
def install_cmd(ctx, codex: bool, claude: bool) -> None:
    project_path: Path = ctx.obj["project_path"]
    install_codex = codex or not claude
    install_claude = claude or not codex
    written: list[str] = []

    if install_codex:
        written.extend(_write_files(project_path, codex_install_files()))

    if install_claude:
        written.extend(_write_files(project_path, claude_install_files()))

    for path in written:
        click.echo(f"written: {path}")


def _write_files(project_path: Path, files: dict[str, str]) -> list[str]:
    written = []
    for relative_path, content in files.items():
        target = project_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(str(target))
    return written
