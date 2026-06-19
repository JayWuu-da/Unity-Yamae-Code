import subprocess
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.tool_registry import ToolRegistry, ToolSpec, completed_tool_result
from kunity_yamae.unity_adapters import EditorAdapter
from kunity_yamae.unity_verification_contracts import VerificationContext
from kunity_yamae.unity_verification_plan import build_verification_plan
from kunity_yamae.unity_verification_steps import run_build, run_editmode_tests

EDITOR_PROBE_METHOD = "KUnityYamae.Editor.HarnessChecks.RunEditorInspection"
BUILD_ENTRY_METHOD = "KUnityYamae.Editor.BuildEntryPoint.Build"


def _context(tmp_path: Path) -> VerificationContext:
    reports_dir = tmp_path / ".unity-harness" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return VerificationContext(
        project_path=tmp_path,
        reports_dir=reports_dir,
        unity_config={"project_path": "."},
        unity_project_path=str(tmp_path),
        planned_unity_executable="Unity",
        timeout_compile=11,
        timeout_tests=22,
        timeout_build=33,
    )


def test_orchestrate_editor_probe_uses_real_harness_wrapper(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Inspect listeners",
            "--execute-loop",
            "--schema",
            "v2",
            "--editor-probe-plan",
            "--verify-dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert EDITOR_PROBE_METHOD in result.output
    assert "KUnityYamae.EditorInspectionProbe.Run" not in result.output


def test_execute_loop_requires_schema_v2(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "orchestrate",
            "Inspect listeners",
            "--execute-loop",
            "--json",
        ],
    )

    assert result.exit_code == 2
    assert "requires --schema v2" in result.output


def test_editor_adapter_default_probe_method_is_real_wrapper(tmp_path: Path) -> None:
    result = EditorAdapter(tmp_path).plan_probe()

    assert result["facts"]["custom_method"] == EDITOR_PROBE_METHOD


def test_build_plan_and_execution_use_same_entrypoint(tmp_path: Path) -> None:
    context = _context(tmp_path)
    planned = build_verification_plan(
        context,
        compile_check=False,
        build_target="StandaloneWindows64",
    )[0]["command"]
    calls: list[list[str]] = []

    def fake_runner(cmd: list[str], _timeout: int) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        _ = (context.reports_dir / "build_StandaloneWindows64.log").write_text(
            "Build succeeded",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0)

    result = run_build(context, "Unity", "StandaloneWindows64", fake_runner)

    assert result.get("passed") is True
    assert calls == [planned]
    assert BUILD_ENTRY_METHOD in planned
    assert "-kunityBuildTarget" in planned
    assert "-kunityBuildOutput" in planned
    assert "UnityEditor.BuildPipeline.BuildPlayer" not in planned


def test_mixed_nunit_result_is_failed_even_when_some_tests_passed(tmp_path: Path) -> None:
    context = _context(tmp_path)

    def fake_runner(cmd: list[str], _timeout: int) -> subprocess.CompletedProcess[str]:
        results_path = Path(cmd[cmd.index("-testResults") + 1])
        results_path.parent.mkdir(parents=True, exist_ok=True)
        mixed_xml = (
            '<test-run result="Failed" failed="1"><test-suite result="Passed" />'
            '<test-case result="Passed" /></test-run>'
        )
        _ = results_path.write_text(mixed_xml, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    result = run_editmode_tests(context, "Unity", fake_runner)

    assert result.get("status") == "failed"
    assert result.get("passed") is False
    assert "overall: Failed" in str(result.get("details", ""))


def test_nunit_result_fails_when_unity_return_code_is_nonzero(tmp_path: Path) -> None:
    context = _context(tmp_path)

    def fake_runner(cmd: list[str], _timeout: int) -> subprocess.CompletedProcess[str]:
        results_path = Path(cmd[cmd.index("-testResults") + 1])
        results_path.parent.mkdir(parents=True, exist_ok=True)
        _ = results_path.write_text('<test-run result="Passed" failed="0" />', encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 1)

    result = run_editmode_tests(context, "Unity", fake_runner)

    assert result.get("status") == "failed"
    assert result.get("passed") is False
    assert "return code: 1" in str(result.get("details", ""))


def test_malformed_nunit_xml_is_failed(tmp_path: Path) -> None:
    context = _context(tmp_path)

    def fake_runner(cmd: list[str], _timeout: int) -> subprocess.CompletedProcess[str]:
        results_path = Path(cmd[cmd.index("-testResults") + 1])
        results_path.parent.mkdir(parents=True, exist_ok=True)
        _ = results_path.write_text("<test-run", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    result = run_editmode_tests(context, "Unity", fake_runner)

    assert result.get("status") == "failed"
    assert result.get("passed") is False
    assert "Malformed test results XML" in str(result.get("details", ""))


def test_quality_gate_json_exits_nonzero_when_unavailable(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "verify", "--dry-run", "--quality-gate", "--json"],
    )

    assert result.exit_code == 2
    assert '"status": "unavailable"' in result.output


def test_tool_registry_refuses_disallowed_permission_before_handler_runs() -> None:
    called = False
    registry = ToolRegistry(allowed_permissions=("read",))

    def handler(_payload: dict[str, object]) -> dict[str, object]:
        nonlocal called
        called = True
        return completed_tool_result("repo.write", "guarded", {"changed": True})

    registry.register(
        ToolSpec(
            name="repo.write",
            version="1",
            description="Synthetic write tool.",
            input_contract="unity-harness.tool-input.v1",
            output_contract="unity-harness.tool-call-result.v1",
            permission="write_code",
            side_effect_level="low",
            timeout_ms=1000,
            evidence_tier="guarded",
            guard_required=True,
            handler_kind="local",
            capability_tags=("repo", "write"),
        ),
        handler,
    )

    result = registry.call("repo.write", {}, "v2")

    assert called is False
    assert result["status"] == "failed"
    assert result["permission"] == "write_code"
    assert result["permission_outcome"] == "refused"
    assert "permission denied" in result["errors"][0]


def test_tool_registry_reports_timeout_overrun_after_handler_returns() -> None:
    ticks = iter([0.0, 0.2])
    registry = ToolRegistry(clock=lambda: next(ticks))

    registry.register(
        ToolSpec(
            name="harness.slow",
            version="1",
            description="Synthetic slow tool.",
            input_contract="unity-harness.tool-input.v1",
            output_contract="unity-harness.tool-call-result.v1",
            permission="read",
            side_effect_level="none",
            timeout_ms=100,
            evidence_tier="static_scan",
            guard_required=False,
            handler_kind="local",
            capability_tags=("harness", "slow"),
        ),
        lambda _payload: completed_tool_result("harness.slow", "static_scan", {"ok": True}),
    )

    result = registry.call("harness.slow", {}, "v2")

    assert result["status"] == "failed"
    assert result["permission_outcome"] == "refused"
    assert "timed out after 200ms" in result["errors"][0]
