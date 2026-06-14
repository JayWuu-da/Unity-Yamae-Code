import subprocess

from rich.console import Console

from .guarded_edits import GuardedEditError, GuardedEditWorkflow
from .guards import DiffGuard
from .ledger import EvidenceLedger
from .reporter import ReportWriter
from .verifier import UnityVerifier

console = Console()

AGENT_OPERATIONAL_ERRORS = (ImportError, OSError, ValueError)
PATCH_OPERATIONAL_ERRORS = (
    GuardedEditError,
    subprocess.CalledProcessError,
    OSError,
    ValueError,
)


def print_risk_step(risk_report: dict, selected_mode: str) -> None:
    console.print("[bold]Step 1: Risk Classification[/bold]")
    console.print(f"  Score: {risk_report['risk_score']} | Mode: {selected_mode}")
    if risk_report.get("triggers"):
        console.print(f"  Triggers: {', '.join(risk_report['triggers'][:3])}")
    console.print()


def run_agent_step(
    agent_name: str,
    config: dict,
    project_path,
    task: str,
    risk_report: dict,
    selected_mode: str,
    ledger: EvidenceLedger,
    *,
    quiet: bool = False,
) -> dict:
    if not quiet:
        console.print("[bold]Step 2: Agent Execution[/bold]")
    try:
        from .agents import get_agent

        agent_backend = get_agent(agent_name, config)
        result = agent_backend.execute(task, project_path, risk_report, selected_mode, ledger)
        if result.get("status") == "error":
            return _agent_error(result, ledger, quiet)
        if not quiet:
            console.print(f"  [green]Completed via {agent_name}[/green]")
            if result.get("changes", []):
                console.print(f"  Files to change: {len(result['changes'])}")
        return result
    except AGENT_OPERATIONAL_ERRORS as exc:
        if not quiet:
            console.print(f"  [red]Failed: {exc}[/red]")
        ledger.add_event("agent_error", {"error": str(exc)})
        return {"status": "error", "message": str(exc)}


def handle_agent_patch(
    *,
    project_path,
    config: dict,
    agent_name: str,
    agent_result: dict,
    apply_patch: bool,
) -> dict:
    if agent_result.get("status") == "error":
        return _agent_execution_failure(agent_name, agent_result)
    workflow = GuardedEditWorkflow(project_path, config)
    try:
        patch_result = (
            workflow.apply(str(agent_result.get("output", "")))
            if apply_patch
            else workflow.evaluate(str(agent_result.get("output", "")))
        )
    except PATCH_OPERATIONAL_ERRORS as exc:
        patch_result = {"status": "error", "applied": False, "issues": [], "error": str(exc)}
    clean_statuses = {"ready_to_apply", "applied"}
    status = "completed" if patch_result["status"] in clean_statuses else "failed"
    return {
        "schema": "unity-harness.run-result.v1",
        "status": status,
        "failed_stage": None if status == "completed" else "agent_patch_guard",
        "agent": agent_name,
        "agent_executed": True,
        "provider_requests": 0,
        "agent_patch": patch_result,
    }


def run_guard_step(project_path, config: dict) -> None:
    console.print("\n[bold]Step 3: Guard Check[/bold]")
    issues = DiffGuard(project_path, config).check()
    if not issues:
        console.print("  [green]No issues found[/green]")
        return
    hard = [issue for issue in issues if issue["severity"] == "hard_failure"]
    warn = [issue for issue in issues if issue["severity"] == "warning"]
    console.print(
        f"  [red]Hard failures: {len(hard)}[/red] | [yellow]Warnings: {len(warn)}[/yellow]"
    )
    for issue in issues[:5]:
        console.print(f"  - [{issue['severity']}] {issue['guard']}: {issue['message'][:80]}")


def run_verification_step(project_path, config: dict, risk_report: dict) -> None:
    console.print("\n[bold]Step 4: Verification[/bold]")
    results = UnityVerifier(project_path, config).verify(
        compile_check=True,
        editmode_tests=risk_report["risk_score"] >= 30,
        playmode_tests=risk_report["risk_score"] >= 60,
    )
    for result in results:
        color = "green" if result["passed"] else "red"
        console.print(
            f"  [{color}]Tier {result.get('tier', '?')}: "
            f"{result['name']} - {result['status']}[/{color}]"
        )
        if not result["passed"]:
            console.print(f"    {result.get('details', '')[:100]}")


def write_report_step(
    project_path,
    task: str,
    selected_mode: str,
    risk_report: dict,
    ledger: EvidenceLedger,
) -> None:
    console.print("\n[bold]Step 5: Report[/bold]")
    report_path = ledger.finalize()
    console.print(f"  Ledger: {report_path}")
    writer = ReportWriter(project_path)
    events = writer.read_last_ledger()
    if events:
        report_md = writer.write_report(events, risk_report, task, selected_mode)
        console.print(f"  Report: {report_md}")
    console.print("\n[bold cyan]Pipeline complete[/bold cyan]")


def _agent_error(result: dict, ledger: EvidenceLedger, quiet: bool) -> dict:
    if not quiet:
        console.print(f"  [red]Error: {result.get('message', 'unknown')}[/red]")
    ledger.add_event("agent_error", {"error": result.get("message", "unknown")})
    return result


def _agent_execution_failure(agent_name: str, agent_result: dict) -> dict:
    return {
        "schema": "unity-harness.run-result.v1",
        "status": "failed",
        "failed_stage": "agent_execution",
        "agent": agent_name,
        "agent_executed": True,
        "provider_requests": 0,
        "agent_patch": None,
        "error": agent_result.get("message", "unknown"),
    }
