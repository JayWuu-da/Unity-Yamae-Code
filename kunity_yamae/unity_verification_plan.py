from .unity_verification_commands import build_player_command
from .unity_verification_contracts import PlannedCommand, VerificationContext


def build_verification_plan(
    context: VerificationContext,
    *,
    compile_check: bool = True,
    editmode_tests: bool = False,
    playmode_tests: bool = False,
    build_target: str | None = None,
    custom_method: str | None = None,
) -> list[PlannedCommand]:
    unity_exe = context.planned_unity_executable
    project_path = context.unity_project_path
    results: list[PlannedCommand] = []
    if compile_check:
        results.append(_planned_compile_command(context, unity_exe, project_path))
    if editmode_tests:
        results.append(
            _planned_test_command(context, unity_exe, project_path, "EditMode", "editmode")
        )
    if playmode_tests:
        results.append(
            _planned_test_command(context, unity_exe, project_path, "PlayMode", "playmode")
        )
    if custom_method or context.unity_config.get("custom_validation_method"):
        method = str(custom_method or context.unity_config["custom_validation_method"])
        results.append(_planned_custom_command(context, unity_exe, project_path, method))
    if build_target:
        results.append(_planned_build_command(context, unity_exe, project_path, build_target))
    return results


def _planned_compile_command(
    context: VerificationContext,
    unity_exe: str,
    project_path: str,
) -> PlannedCommand:
    return {
        "name": "compile/import",
        "tier": "1",
        "status": "planned",
        "passed": False,
        "command": [
            unity_exe,
            "-batchmode",
            "-quit",
            "-projectPath",
            project_path,
            "-logFile",
            str(context.reports_dir / "compile.log"),
        ],
    }


def _planned_test_command(
    context: VerificationContext,
    unity_exe: str,
    project_path: str,
    test_platform: str,
    basename: str,
) -> PlannedCommand:
    results_dir = context.project_path / context.unity_config.get(
        "test_results_dir", ".unity-harness/reports/test-results"
    )
    return {
        "name": f"{basename}_tests",
        "tier": "2" if test_platform == "EditMode" else "3",
        "status": "planned",
        "passed": False,
        "command": [
            unity_exe,
            "-batchmode",
            "-runTests",
            "-projectPath",
            project_path,
            "-testPlatform",
            test_platform,
            "-testResults",
            str(results_dir / f"{basename}.xml"),
            "-logFile",
            str(context.reports_dir / f"{basename}.log"),
        ],
    }


def _planned_custom_command(
    context: VerificationContext,
    unity_exe: str,
    project_path: str,
    method: str,
) -> PlannedCommand:
    return {
        "name": "custom_method",
        "tier": "4",
        "status": "planned",
        "passed": False,
        "command": [
            unity_exe,
            "-batchmode",
            "-quit",
            "-projectPath",
            project_path,
            "-executeMethod",
            method,
            "-logFile",
            str(context.reports_dir / "custom.log"),
        ],
    }


def _planned_build_command(
    context: VerificationContext,
    unity_exe: str,
    project_path: str,
    build_target: str,
) -> PlannedCommand:
    log_path = context.reports_dir / f"build_{build_target}.log"
    return {
        "name": f"build_{build_target}",
        "tier": "5",
        "status": "planned",
        "passed": False,
        "command": build_player_command(context, unity_exe, build_target, log_path),
    }
