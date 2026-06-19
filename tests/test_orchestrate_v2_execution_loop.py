import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.contracts import validate_orchestration_run_v2


def test_orchestrate_execute_loop_outputs_v2_run_and_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Inspect neutral runtime component",
            "--execute-loop",
            "--schema",
            "v2",
            "--verify-dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_orchestration_run_v2(payload) == payload
    assert payload["schema"] == "unity-harness.orchestration-run.v2"
    assert payload["status"] == "completed_with_warnings"
    assert payload["artifacts"]["trace_events"].endswith(
        ".unity-harness/reports/traces/events.jsonl"
    )
    assert payload["artifacts"]["memory_summary"].endswith(
        ".unity-harness/cache/state/episodic-summary.json"
    )
    assert (tmp_path / ".unity-harness" / "reports" / "traces" / "events.jsonl").exists()
    assert (tmp_path / ".unity-harness" / "cache" / "state" / "episodic-summary.json").exists()
    step_by_tool = {step["tool"]: step for step in payload["steps"]}
    assert step_by_tool["harness.risk.classify"]["permission_outcome"] == "allowed"
    assert step_by_tool["harness.memory.record"]["status"] == "completed"
    assert step_by_tool["unity.player.status"]["permission_outcome"] == "unavailable"


def test_orchestrate_execute_loop_is_explicit_and_plan_only_remains_v1(tmp_path: Path) -> None:
    runner = CliRunner()

    plan_result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Inspect neutral runtime component",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
    )
    default_result = runner.invoke(
        main,
        ["--project", str(tmp_path), "orchestrate", "Inspect neutral runtime component", "--json"],
    )

    assert plan_result.exit_code == 0, plan_result.output
    assert json.loads(plan_result.output)["schema"] == "unity-harness.orchestration-plan.v1"
    assert default_result.exit_code == 2


def test_orchestrate_invalid_schema_returns_json_failure(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Inspect neutral runtime component",
            "--execute-loop",
            "--schema",
            "v3",
            "--json",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.tool-call-result.v1"
    assert payload["status"] == "failed"
    assert "unsupported schema" in payload["errors"][0]
