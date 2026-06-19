import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .editor_probe_stage import stage_editor_probe
from .unity_verification_commands import build_player_command
from .unity_verification_contracts import VerificationContext, VerificationResult

UnityCommandRunner = Callable[[list[str], int], subprocess.CompletedProcess[str]]
UnityLogParser = Callable[[str], Mapping[str, Sequence[str]]]
OutputSummarizer = Callable[[subprocess.CompletedProcess[str]], str]


def run_compile_check(
    context: VerificationContext,
    unity_exe: str | None,
    run_unity_command: UnityCommandRunner,
    parse_unity_log: UnityLogParser,
) -> VerificationResult:
    if not unity_exe:
        return _unity_missing("compile/import")

    log_path = context.reports_dir / "compile.log"
    cmd = [
        unity_exe,
        "-batchmode",
        "-quit",
        "-projectPath",
        context.unity_project_path,
        "-logFile",
        str(log_path),
    ]

    try:
        result = run_unity_command(cmd, context.timeout_compile)
        log_content = _read_optional_log(log_path)
        parsed = parse_unity_log(log_content)
        if result.returncode == 0 and not parsed["errors"]:
            return _result("compile/import", "passed", True, "Compile/import succeeded", log_path)
        error_summary = "; ".join(parsed["errors"][:3])
        return _result("compile/import", "failed", False, f"Errors: {error_summary}", log_path)
    except subprocess.TimeoutExpired:
        return _result(
            "compile/import",
            "timeout",
            False,
            "Unity batchmode timed out after 300s",
            log_path,
        )
    except FileNotFoundError:
        return _unity_missing("compile/import")


def run_editmode_tests(
    context: VerificationContext,
    unity_exe: str | None,
    run_unity_command: UnityCommandRunner,
) -> VerificationResult:
    return _run_test_platform(
        context,
        unity_exe,
        "EditMode",
        "editmode",
        context.timeout_tests,
        run_unity_command,
    )


def run_playmode_tests(
    context: VerificationContext,
    unity_exe: str | None,
    run_unity_command: UnityCommandRunner,
) -> VerificationResult:
    return _run_test_platform(
        context,
        unity_exe,
        "PlayMode",
        "playmode",
        context.timeout_tests,
        run_unity_command,
    )


def run_build(
    context: VerificationContext,
    unity_exe: str | None,
    target: str,
    run_unity_command: UnityCommandRunner,
) -> VerificationResult:
    name = f"build_{target}"
    if not unity_exe:
        return _unity_missing(name)

    log_path = context.reports_dir / f"build_{target}.log"
    cmd = build_player_command(context, unity_exe, target, log_path)

    try:
        with stage_editor_probe(context.project_path):
            result = run_unity_command(cmd, context.timeout_build)
        log_content = _read_optional_log(log_path)
        if "Build succeeded" in log_content or result.returncode == 0:
            return _result(name, "passed", True, f"Build to {target} succeeded", log_path)
        return _result(name, "failed", False, f"Build to {target} failed", log_path)
    except subprocess.TimeoutExpired:
        return _result(name, "timeout", False, "Build timed out after 1800s", log_path)


def run_custom_method(
    context: VerificationContext,
    unity_exe: str | None,
    method: str,
    run_unity_command: UnityCommandRunner,
    summarize_output: OutputSummarizer,
) -> VerificationResult:
    name = f"custom_{method.split('.')[-1]}"
    if not unity_exe:
        return _unity_missing(name)

    log_path = context.reports_dir / "custom_probe.log"
    cmd = [
        unity_exe,
        "-batchmode",
        "-quit",
        "-projectPath",
        context.unity_project_path,
        "-executeMethod",
        method,
        "-logFile",
        str(log_path),
    ]

    try:
        result = run_unity_command(cmd, context.timeout_compile)
        log_content = _read_optional_log(log_path)
        if "HARNESS_CHECKS_COMPLETE" in log_content or result.returncode == 0:
            return _result(name, "passed", True, f"Custom method {method} succeeded", log_path)
        details = f"Custom method {method} failed{summarize_output(result)}"
        return _result(name, "failed", False, details, log_path)
    except subprocess.TimeoutExpired:
        return _result(name, "timeout", False, "Custom method timed out", log_path)


def _run_test_platform(
    context: VerificationContext,
    unity_exe: str | None,
    test_platform: str,
    basename: str,
    timeout: int,
    run_unity_command: UnityCommandRunner,
) -> VerificationResult:
    name = f"{basename}_tests"
    if not unity_exe:
        return _unity_missing(name)

    results_path = context.project_path / _test_results_dir(context)
    results_path.mkdir(parents=True, exist_ok=True)
    test_results = results_path / f"{basename}.xml"
    log_path = context.reports_dir / f"{basename}.log"
    cmd = _test_command(context, unity_exe, test_platform, test_results, log_path)

    try:
        process = run_unity_command(cmd, timeout)
        if not test_results.exists():
            return _result(name, "no_results", False, "No test results generated", log_path)
        try:
            root = ET.parse(test_results).getroot()
        except ET.ParseError as exc:
            return _result(
                name,
                "failed",
                False,
                f"Malformed test results XML: {exc}",
                log_path,
                test_results,
            )
        overall_result = root.attrib.get("result", "").lower()
        failed_count = int(root.attrib.get("failed", "0") or "0")
        passed = process.returncode == 0 and overall_result == "passed" and failed_count == 0
        details = (
            f"overall: {root.attrib.get('result', 'unknown')}; "
            f"failed: {failed_count}; return code: {process.returncode}"
        )
        return _result(
            name,
            "passed" if passed else "failed",
            passed,
            details,
            log_path,
            test_results,
        )
    except subprocess.TimeoutExpired:
        return _result(
            name,
            "timeout",
            False,
            f"{test_platform} tests timed out after 600s",
            log_path,
        )


def _test_command(
    context: VerificationContext,
    unity_exe: str,
    test_platform: str,
    test_results: Path,
    log_path: Path,
) -> list[str]:
    return [
        unity_exe,
        "-batchmode",
        "-runTests",
        "-projectPath",
        context.unity_project_path,
        "-testPlatform",
        test_platform,
        "-testResults",
        str(test_results),
        "-logFile",
        str(log_path),
    ]


def _test_results_dir(context: VerificationContext) -> str:
    configured = context.unity_config.get("test_results_dir")
    if isinstance(configured, str) and configured:
        return configured
    return ".unity-harness/reports/test-results"


def _result(
    name: str,
    status: str,
    passed: bool,
    details: str,
    log_path: Path,
    xml_path: Path | None = None,
) -> VerificationResult:
    result: VerificationResult = {
        "name": name,
        "status": status,
        "passed": passed,
        "details": details,
        "log_path": str(log_path),
    }
    if xml_path is not None:
        result["xml_path"] = str(xml_path)
    return result


def _unity_missing(name: str) -> VerificationResult:
    return {
        "name": name,
        "status": "skipped",
        "passed": False,
        "details": "Unity executable not found",
        "log_path": "",
    }


def _read_optional_log(log_path: Path) -> str:
    return log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
