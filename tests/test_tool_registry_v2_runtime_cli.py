import json

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.contracts import validate_tool_call_result_v2, validate_tool_registry_v2


def test_tools_list_schema_v2_is_explicit_and_default_stays_v1(tmp_path) -> None:
    runner = CliRunner()

    default_result = runner.invoke(main, ["--project", str(tmp_path), "tools", "list", "--json"])
    v2_result = runner.invoke(
        main,
        ["--project", str(tmp_path), "tools", "list", "--schema", "v2", "--json"],
    )

    assert default_result.exit_code == 0, default_result.output
    assert json.loads(default_result.output)["schema"] == "unity-harness.tool-registry.v1"
    assert v2_result.exit_code == 0, v2_result.output
    payload = json.loads(v2_result.output)
    assert validate_tool_registry_v2(payload) == payload
    risk_tool = next(tool for tool in payload["tools"] if tool["name"] == "harness.risk.classify")
    assert risk_tool["lifecycle"] == "available"
    assert risk_tool["adapter_scope"] == "harness"
    assert risk_tool["dry_run_supported"] is True
    assert "tool.completed" in risk_tool["observability_events"]


def test_tools_call_schema_v2_wraps_permission_and_observability(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "tools",
            "call",
            "harness.risk.classify",
            "--schema",
            "v2",
            "--payload-json",
            '{"task":"Inspect neutral runtime component"}',
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_tool_call_result_v2(payload) == payload
    assert payload["schema"] == "unity-harness.tool-call-result.v2"
    assert payload["permission"] == "read"
    assert payload["permission_outcome"] == "allowed"
    assert payload["status"] == "completed"
    assert payload["observability_events"] == ["tool.started", "tool.completed"]


def test_tools_show_schema_v2_reports_unknown_tool_as_v2_failure(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "tools", "show", "missing.tool", "--schema", "v2", "--json"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert validate_tool_call_result_v2(payload) == payload
    assert payload["tool"] == "missing.tool"
    assert payload["status"] == "failed"
    assert payload["permission_outcome"] == "refused"


def test_tools_invalid_schema_returns_json_failure(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "tools", "list", "--schema", "v3", "--json"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.tool-call-result.v1"
    assert payload["status"] == "failed"
    assert "unsupported schema" in payload["errors"][0]


def test_tools_call_schema_v2_player_status_includes_dev_build_adapter_contract(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "tools",
            "call",
            "unity.player.status",
            "--schema",
            "v2",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_tool_call_result_v2(payload) == payload
    assert payload["status"] == "unavailable"
    assert payload["permission_outcome"] == "unavailable"
    assert payload["result"]["adapter"] == "player"
    assert payload["result"]["player"]["dev_build_only"] is True


def test_tools_call_schema_v2_editor_probe_plan_includes_adapter_contract(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "tools",
            "call",
            "unity.inspect.editor_probe.plan",
            "--schema",
            "v2",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert validate_tool_call_result_v2(payload) == payload
    assert payload["status"] == "completed"
    assert payload["permission_outcome"] == "allowed"
    assert payload["result"]["adapter"] == "editor"
    assert payload["result"]["unity_editor_verified"] is False
