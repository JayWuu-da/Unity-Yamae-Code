import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project

REQUIRED_COPY_KEYS = {
    "readme_agent_workflow",
    "readme_ko_agent_workflow",
    "entrypoints_discovered_facts",
    "docs_static_limits",
    "no_forbidden_path_placeholders",
    "no_api_provider_surface",
    "tracked_artifact_hygiene",
}


def test_release_check_reports_agent_facing_copy_contract(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert REQUIRED_COPY_KEYS <= set(payload["agent_facing_copy"])
    assert all(payload["agent_facing_copy"][key] is True for key in REQUIRED_COPY_KEYS)


def test_release_check_failure_names_agent_facing_copy_checks(monkeypatch, tmp_path: Path) -> None:
    import kunity_yamae.cli_release_check as release_check

    create_minimal_project(tmp_path)
    monkeypatch.setattr(
        release_check,
        "_collect_agent_facing_copy",
        lambda _root: {
            key: key != "readme_agent_workflow" for key in REQUIRED_COPY_KEYS
        },
    )
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert "agent_facing_copy.readme_agent_workflow" in payload["failed_checks"]
