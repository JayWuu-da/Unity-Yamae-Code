import json
import os
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_agent_can_use_harness_from_current_unity_project_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_minimal_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    init_result = runner.invoke(main, ["init-agent", "--target", "both", "--dry-run", "--json"])
    doctor_result = runner.invoke(main, ["providers", "doctor", "--json"])
    context_result = runner.invoke(main, ["context", "--pretty", "Fix prefab button raycast"])
    run_result = runner.invoke(
        main,
        ["run", "Fix prefab button raycast", "--plan-only", "--verify-dry-run", "--json"],
    )

    assert init_result.exit_code == 0, init_result.output
    assert doctor_result.exit_code == 0, doctor_result.output
    assert context_result.exit_code == 0, context_result.output
    assert run_result.exit_code == 0, run_result.output

    init_payload = json.loads(init_result.output)
    context_payload = json.loads(context_result.output)
    run_payload = json.loads(run_result.output)
    paths = {item["path"] for item in init_payload["files"]}
    assert ".agents/skills/k-unity-yamae/SKILL.md" in paths
    assert ".claude/skills/k-unity-yamae/SKILL.md" in paths
    assert ".claude/commands/kunity-yamae.md" in paths
    assert "fact_limits" in context_payload
    serialized = json.dumps({"context": context_payload, "run": run_payload})
    assert "Editor verification passed" not in serialized
    assert "Inspector validation passed" not in serialized
    assert "PlayMode passed" not in serialized

    evidence = Path(
        os.environ.get(
            "KUNITY_YAMAE_SETUP_FLOW_EVIDENCE",
            str(Path.cwd().parent / "task-8-current-root-flow.json"),
        )
    )
    evidence.write_text(serialized, encoding="utf-8")


def test_plan_only_flow_reports_unity_verification_as_planned_not_run(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "run",
            "Fix prefab button raycast",
            "--plan-only",
            "--verify-dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Editor verification passed" not in result.output
    assert "Inspector validation passed" not in result.output
    assert "PlayMode passed" not in result.output


def test_init_agent_write_reports_conflicts_for_existing_agent_files(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    (tmp_path / "AGENTS.md").write_text("existing", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("existing", encoding="utf-8")
    runner = CliRunner()

    write_result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--write", "--json"],
    )
    dry_run_result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--dry-run", "--json"],
    )

    assert write_result.exit_code == 2, write_result.output
    assert json.loads(write_result.output)["status"] == "conflict"
    assert dry_run_result.exit_code == 2, dry_run_result.output
    assert json.loads(dry_run_result.output)["status"] == "conflict"
