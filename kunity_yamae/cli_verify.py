import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .live_plan import (
    qa_level_defaults,
    test_assembly_suggestions,
    unity_mcp_plan,
    visual_smoke_plan,
)
from .quality_gates import evaluate_quality_gate
from .verifier import UnityVerifier

console = Console()


@click.command("verify")
@click.option("--editmode", is_flag=True, help="Run EditMode tests only")
@click.option("--playmode", is_flag=True, help="Run PlayMode tests only")
@click.option("--compile-only", is_flag=True, help="Compile/import check only")
@click.option("--build", default=None, help="Build target (e.g. StandaloneWindows64)")
@click.option("--custom-method", default=None, help="Custom Editor method to run")
@click.option(
    "--qa-level",
    type=click.Choice(["minimal", "standard", "release"]),
    default="standard",
    help="Verification scope when no explicit tier flags are supplied.",
)
@click.option("--live", is_flag=True, help="Include Unity MCP live verification scenario.")
@click.option("--visual-smoke", is_flag=True, help="Include Game View screenshot smoke plan.")
@click.option("--quality-gate", is_flag=True, help="Evaluate required verification tiers.")
@click.option("--dry-run", is_flag=True, help="Print Unity commands without executing them.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def verify_cmd(
    ctx,
    editmode: bool,
    playmode: bool,
    compile_only: bool,
    build: str | None,
    custom_method: str | None,
    qa_level: str,
    live: bool,
    visual_smoke: bool,
    quality_gate: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    verifier = UnityVerifier(project_path, config)
    explicit_selection = any([editmode, playmode, compile_only, build, custom_method])
    defaults = qa_level_defaults(qa_level, explicit_selection)
    selected_compile = compile_only or defaults["compile"] or not any(
        [editmode, playmode, build, custom_method, defaults["editmode"], defaults["playmode"]]
    )
    selected_editmode = editmode or defaults["editmode"]
    selected_playmode = playmode or defaults["playmode"]
    selected_build = build
    if defaults["release_build"] and not selected_build:
        selected_build = "StandaloneWindows64"
    if dry_run:
        results = verifier.plan(
            compile_check=selected_compile,
            editmode_tests=selected_editmode,
            playmode_tests=selected_playmode,
            build_target=selected_build,
            custom_method=custom_method,
        )
        if as_json:
            payload = _verify_payload(project_path, qa_level, True, results, live, visual_smoke)
            if quality_gate:
                payload["quality_gate"] = evaluate_quality_gate(results)
            click.echo(json.dumps(payload, indent=2))
            _exit_if_quality_gate_failed(ctx, payload)
            return
        for result in results:
            console.print(" ".join(str(part) for part in result["command"]))
        return

    results = verifier.verify(
        compile_check=selected_compile,
        editmode_tests=selected_editmode,
        playmode_tests=selected_playmode,
        build_target=selected_build,
        custom_method=custom_method,
    )

    if as_json:
        payload = _verify_payload(project_path, qa_level, False, results, live, visual_smoke)
        if quality_gate:
            payload["quality_gate"] = evaluate_quality_gate(results)
        click.echo(json.dumps(payload, indent=2))
        _exit_if_quality_gate_failed(ctx, payload)
        return

    table = Table(title="Verification Results")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")
    for result in results:
        passed = bool(result.get("passed"))
        status_color = "green" if passed else "red"
        name = str(result.get("name", "unknown"))
        status = str(result.get("status", "unknown"))
        details = str(result.get("details", ""))
        table.add_row(
            name,
            f"[{status_color}]{status}[/{status_color}]",
            details,
        )
    console.print(table)
    if quality_gate:
        gate = evaluate_quality_gate(results)
        if gate["passed"] is not True:
            ctx.exit(2)


def _verify_payload(
    project_path: Path,
    qa_level: str,
    dry_run: bool,
    results: Sequence[Mapping[str, Any]],
    live: bool,
    visual_smoke: bool,
) -> dict[str, Any]:
    return {
        "schema": "unity-harness.verify-result.v1",
        "dry_run": dry_run,
        "qa_level": qa_level,
        "results": list(results),
        "test_assembly_suggestions": test_assembly_suggestions(project_path),
        "unity_mcp": unity_mcp_plan(live, visual_smoke),
        "visual_smoke": visual_smoke_plan(visual_smoke),
    }


def _exit_if_quality_gate_failed(ctx, payload: Mapping[str, Any]) -> None:
    gate = payload.get("quality_gate")
    if isinstance(gate, Mapping) and gate.get("passed") is not True:
        ctx.exit(2)
