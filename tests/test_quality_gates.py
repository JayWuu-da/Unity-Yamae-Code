import json

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.quality_gates import evaluate_quality_gate


def test_quality_gate_passes_required_successful_tiers() -> None:
    result = evaluate_quality_gate(
        [{"name": "compile", "status": "passed", "passed": True}],
        required_tiers=("compile",),
    )

    assert result["schema"] == "unity-harness.quality-gate-result.v1"
    assert result["status"] == "passed"
    assert result["missing_required_tiers"] == []


def test_quality_gate_normalizes_compile_import_result_name() -> None:
    result = evaluate_quality_gate(
        [{"name": "compile/import", "status": "passed", "passed": True}],
        required_tiers=("compile",),
    )

    assert result["status"] == "passed"
    assert result["missing_required_tiers"] == []


def test_quality_gate_fails_missing_required_tier() -> None:
    result = evaluate_quality_gate([], required_tiers=("compile",))

    assert result["status"] == "failed"
    assert result["missing_required_tiers"] == ["compile"]


def test_quality_gate_policy_requires_inspector_and_player_evidence_for_claims() -> None:
    result = evaluate_quality_gate(
        [{"name": "compile/import", "status": "passed", "passed": True}],
        mode="asset_safe",
        evidence_claims=("inspector", "player_live"),
    )

    assert result["status"] == "failed"
    assert result["missing_required_tiers"] == ["editor_probe", "player_live"]


def test_quality_gate_policy_for_static_only_task_requires_no_compile() -> None:
    result = evaluate_quality_gate([], mode="static_only", evidence_claims=())

    assert result["status"] == "passed"
    assert result["missing_required_tiers"] == []


def test_verify_dry_run_quality_gate_is_unavailable_not_passed(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "verify",
            "--dry-run",
            "--quality-gate",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["quality_gate"]["schema"] == "unity-harness.quality-gate-result.v1"
    assert payload["quality_gate"]["status"] == "unavailable"
    assert payload["quality_gate"]["passed"] is False
