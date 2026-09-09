"""Single-call, non-mutating worker handoff CLI."""
from __future__ import annotations

import json
from pathlib import Path

import click

from .worker_context import MAX_FILE_BYTES
from .worker_packet import compact_json, prepare_worker_packet, render_worker_prompt


@click.command("worker-pack")
@click.option("--request-file", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--prompt-only", is_flag=True, help="Print only the ready worker prompt, once.")
@click.option("--json", "as_json", is_flag=True, help="Compact machine-readable packet.")
@click.pass_context
def worker_pack_cmd(ctx, request_file: Path, prompt_only: bool, as_json: bool) -> None:
    """Prepare, never execute, a bounded Unity work order."""
    if prompt_only and as_json:
        raise click.UsageError("choose --prompt-only or --json")
    try:
        with request_file.open("rb") as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("work order is too large")
        request = json.loads(raw.decode("utf-8-sig"))
        packet = prepare_worker_packet(ctx.obj["project_path"], request, ctx.obj["config"])
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        click.echo(compact_json({"status": "invalid_request", "error": type(exc).__name__}))
        ctx.exit(2)
        return
    if prompt_only and packet["status"] == "prepared":
        click.echo(render_worker_prompt(packet))
    else:
        click.echo(compact_json(packet))
    if (packet["status"] not in {"prepared", "planned_local"}
            or prompt_only and packet["status"] != "prepared"):
        ctx.exit(3)
