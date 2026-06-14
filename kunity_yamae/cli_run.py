import json

import click
from rich.console import Console

from .cli_providers import build_provider_doctor, provider_doctor_status
from .cli_run_config import with_local_patch_file
from .cli_run_payload import emit_lightweight_payload, emit_run_payload
from .modes import select_mode
from .risk import RiskClassifier
from .run_pipeline import run_mutating_pipeline
from .scanner import UnityProjectScanner

console = Console()


@click.command("run")
@click.argument("task")
@click.option("--agent", default=None, help="Agent backend")
@click.option("--verify/--no-verify", "do_verify", default=True, help="Run verification after.")
@click.option("--guard/--no-guard", "do_guard", default=True, help="Run guards after.")
@click.option("--plan-only", is_flag=True, help="Emit a non-mutating harness plan.")
@click.option("--context-only", is_flag=True, help="Emit selected context without agent execution.")
@click.option("--provider-check", is_flag=True, help="Run provider doctor before agent execution.")
@click.option("--verify-dry-run", is_flag=True, help="Include planned Unity commands.")
@click.option("--editor-probe", is_flag=True, help="Plan an editor probe verification stage.")
@click.option(
    "--guarded-agent-patch",
    is_flag=True,
    help="Treat agent output as a unified diff and run it through guards.",
)
@click.option("--apply-agent-patch", is_flag=True, help="Apply guarded agent patch if clean.")
@click.option(
    "--patch-file",
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    default=None,
    help="Unified diff file for --agent local-patch guarded handoff.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def run_cmd(
    ctx,
    task: str,
    agent: str | None,
    do_verify: bool,
    do_guard: bool,
    plan_only: bool,
    context_only: bool,
    provider_check: bool,
    verify_dry_run: bool,
    editor_probe: bool,
    guarded_agent_patch: bool,
    apply_agent_patch: bool,
    patch_file: str | None,
    as_json: bool,
) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    agent_name = agent or config["agents"]["default"]
    if patch_file is not None:
        config = with_local_patch_file(config, agent_name, patch_file)
    profile = UnityProjectScanner(project_path, config).scan()
    risk_report = RiskClassifier(config).classify(task, profile)
    selected_mode = select_mode(risk_report["risk_score"], config)

    if provider_check and _provider_check_failed(ctx, config, project_path, agent_name, as_json):
        return
    if plan_only or context_only:
        emit_lightweight_payload(
            project_path,
            config,
            task,
            risk_report,
            selected_mode,
            plan_only,
            context_only,
            verify_dry_run,
            editor_probe,
        )
        return

    quiet_json = as_json and (guarded_agent_patch or apply_agent_patch)
    if not quiet_json:
        console.print("[bold cyan]K-Unity-Yamae Pipeline[/bold cyan]")
        console.print(f"[dim]Task: {task}[/dim]\n")
    agent_patch_payload = run_mutating_pipeline(
        project_path=project_path,
        config=config,
        task=task,
        risk_report=risk_report,
        selected_mode=selected_mode,
        agent_name=agent_name,
        do_guard=do_guard,
        do_verify=do_verify,
        guarded_agent_patch=guarded_agent_patch,
        apply_agent_patch=apply_agent_patch,
        quiet=quiet_json,
    )
    if agent_patch_payload is not None:
        emit_run_payload(agent_patch_payload, as_json, ctx, console)


def _provider_check_failed(ctx, config: dict, project_path, agent_name: str, as_json: bool) -> bool:
    provider_payload = build_provider_doctor(
        config,
        provider=agent_name,
        project_path=project_path,
    )
    provider_status = provider_doctor_status(provider_payload)
    if provider_status == "ready":
        return False
    payload = {
        "schema": "unity-harness.run-result.v1",
        "status": "failed",
        "failed_stage": "provider_check",
        "agent": agent_name,
        "agent_executed": False,
        "provider_requests": 0,
        "provider": provider_payload,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        console.print(f"[red]Provider check failed: {provider_status}[/red]")
    ctx.exit(2)
    return True
