from pathlib import Path
from typing import Any

from .cli_run_steps import (
    handle_agent_patch,
    print_risk_step,
    run_agent_step,
    run_guard_step,
    run_verification_step,
    write_report_step,
)
from .ledger import EvidenceLedger


def run_mutating_pipeline(
    *,
    project_path: Path,
    config: dict[str, Any],
    task: str,
    risk_report: dict[str, Any],
    selected_mode: str,
    agent_name: str,
    do_guard: bool,
    do_verify: bool,
    guarded_agent_patch: bool,
    apply_agent_patch: bool,
    quiet: bool,
) -> dict[str, Any] | None:
    if not quiet:
        print_risk_step(risk_report, selected_mode)
    ledger = EvidenceLedger(project_path)
    ledger.start_task(task, selected_mode, risk_report)
    agent_result = run_agent_step(
        agent_name,
        config,
        project_path,
        task,
        risk_report,
        selected_mode,
        ledger,
        quiet=quiet,
    )
    if guarded_agent_patch or apply_agent_patch:
        return handle_agent_patch(
            project_path=project_path,
            config=config,
            agent_name=agent_name,
            agent_result=agent_result,
            apply_patch=apply_agent_patch,
        )
    if do_guard:
        run_guard_step(project_path, config)
    if do_verify:
        run_verification_step(project_path, config, risk_report)
    write_report_step(project_path, task, selected_mode, risk_report, ledger)
    return None
