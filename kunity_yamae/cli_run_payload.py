import json

import click

from .context import ContextSelector
from .guards import DiffGuard
from .ledger import EvidenceLedger
from .verifier import UnityVerifier


def build_lightweight_run_payload(
    *,
    project_path,
    config: dict,
    task: str,
    risk_report: dict,
    selected_mode: str,
    plan_only: bool,
    context_only: bool,
    verify_dry_run: bool,
    editor_probe: bool,
) -> dict:
    context = ContextSelector(project_path, config).select(task, risk_report, selected_mode)
    guard_issues = DiffGuard(project_path, config).check()
    verify_commands = _planned_verify_commands(
        project_path,
        config,
        risk_report,
        verify_dry_run,
        editor_probe,
    )
    ledger = EvidenceLedger(project_path)
    ledger.start_task(task, selected_mode, risk_report)
    ledger.add_event("run_planned", {"plan_only": plan_only, "context_only": context_only})
    return {
        "schema": "unity-harness.run-result.v1",
        "status": "planned",
        "plan_only": plan_only,
        "context_only": context_only,
        "provider_requests": 0,
        "agent_executed": False,
        "risk_report": risk_report,
        "context": context,
        "guard": _guard_payload(guard_issues),
        "verify_commands": verify_commands,
        "stages": _planned_stages(verify_dry_run),
        "report_path": str(project_path / ".unity-harness" / "last-ledger.jsonl"),
    }


def _planned_verify_commands(
    project_path,
    config: dict,
    risk_report: dict,
    verify_dry_run: bool,
    editor_probe: bool,
) -> list[dict]:
    if not verify_dry_run:
        return []
    verifier = UnityVerifier(project_path, config)
    return verifier.plan(
        compile_check=True,
        editmode_tests=risk_report["risk_score"] >= 30,
        playmode_tests=risk_report["risk_score"] >= 60,
        custom_method=(
            "KUnityYamae.Editor.HarnessChecks.RunEditorInspection" if editor_probe else None
        ),
    )


def _guard_payload(guard_issues: list[dict]) -> dict:
    return {
        "status": "failed"
        if any(issue.get("severity") == "hard_failure" for issue in guard_issues)
        else "passed",
        "issues": guard_issues,
    }


def _planned_stages(verify_dry_run: bool) -> list[dict]:
    return [
        {"stage": "scan", "status": "ok"},
        {"stage": "risk", "status": "ok"},
        {"stage": "context", "status": "ok"},
        {"stage": "guard", "status": "ok"},
        {"stage": "verify", "status": "planned" if verify_dry_run else "not_requested"},
    ]


def emit_lightweight_payload(
    project_path,
    config: dict,
    task: str,
    risk_report: dict,
    selected_mode: str,
    plan_only: bool,
    context_only: bool,
    verify_dry_run: bool,
    editor_probe: bool,
) -> None:
    payload = build_lightweight_run_payload(
        project_path=project_path,
        config=config,
        task=task,
        risk_report=risk_report,
        selected_mode=selected_mode,
        plan_only=plan_only,
        context_only=context_only,
        verify_dry_run=verify_dry_run,
        editor_probe=editor_probe,
    )
    click.echo(json.dumps(payload, indent=2))


def emit_run_payload(payload: dict, as_json: bool, ctx, console) -> None:
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        console.print(json.dumps(payload, indent=2))
    if payload["status"] == "failed":
        ctx.exit(2)
