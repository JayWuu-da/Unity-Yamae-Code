from __future__ import annotations

import json

import click

from .orchestrator import build_orchestration_plan, run_orchestration_loop_v2
from .tool_registry import failed_tool_result


@click.command("orchestrate")
@click.argument("task")
@click.option("--plan-only", is_flag=True, help="Require non-mutating plan output.")
@click.option("--execute-loop", is_flag=True, help="Run the explicit non-mutating v2 tool loop.")
@click.option("--schema", "schema_version", default="v1")
@click.option("--verify-dry-run", is_flag=True, help="Include planned Unity commands.")
@click.option("--editor-probe-plan", is_flag=True, help="Plan an editor probe command.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def orchestrate_cmd(
    ctx,
    task: str,
    plan_only: bool,
    execute_loop: bool,
    schema_version: str,
    verify_dry_run: bool,
    editor_probe_plan: bool,
    as_json: bool,
) -> None:
    if schema_version not in {"v1", "v2"}:
        payload = failed_tool_result(
            "orchestrate",
            "planned",
            f"unsupported schema: {schema_version}",
        )
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        ctx.exit(2)
        return
    if plan_only and execute_loop:
        payload = failed_tool_result(
            "orchestrate",
            "planned",
            "choose only one of --plan-only or --execute-loop",
        )
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        ctx.exit(2)
        return
    if execute_loop:
        payload = run_orchestration_loop_v2(
            ctx.obj["project_path"],
            ctx.obj["config"],
            task,
            verify_dry_run=verify_dry_run,
            editor_probe=editor_probe_plan,
        )
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        click.echo(f"completed v2 tool loop: {task}")
        return
    if not plan_only:
        payload = failed_tool_result(
            "orchestrate",
            "planned",
            "orchestrate is non-mutating; pass --plan-only",
        )
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        ctx.exit(2)
        return
    payload = build_orchestration_plan(
        ctx.obj["project_path"],
        ctx.obj["config"],
        task,
        verify_dry_run=verify_dry_run,
        editor_probe=editor_probe_plan,
    )
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"planned: {task}")
