import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_run_plan_only_outputs_risk_context_guard_verify_plan(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "run",
            "Fix SamplePresenter button raycast",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.run-result.v1"
    assert payload["plan_only"] is True
    assert payload["provider_requests"] == 0
    assert payload["risk_report"]["required_rule_cards"] == [
        "unity.global",
        "unity.ui",
        "unity.architecture-patterns",
    ]
    assert payload["verify_commands"][0]["status"] == "planned"
    assert payload["report_path"].endswith("last-ledger.jsonl")


def test_run_provider_check_accepts_local_patch_without_api_key(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "run",
            "Fix typo",
            "--agent",
            "local-patch",
            "--provider-check",
            "--plan-only",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "planned"
    assert payload["provider_requests"] == 0
