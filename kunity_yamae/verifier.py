import subprocess
from pathlib import Path
from typing import Any

from .unity_verification_contracts import PlannedCommand, VerificationContext, VerificationResult
from .unity_verification_plan import build_verification_plan
from .unity_verification_steps import (
    run_build,
    run_compile_check,
    run_custom_method,
    run_editmode_tests,
    run_playmode_tests,
)
from .unity_verification_support import (
    find_unity_executable,
    parse_unity_log,
    process_output_summary,
)


class UnityVerifier:
    def __init__(self, project_path: Path, config: dict[str, Any]):
        self.project_path = project_path
        self.config = config
        self.unity_config = config.get("unity", {})
        self.verify_config = config.get("verification", {})
        self.reports_dir = project_path / ".unity-harness" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        timeouts = self.config.get("verification", {}).get("timeouts", {})
        self.timeout_compile = timeouts.get("compile", 300)
        self.timeout_tests = timeouts.get("tests", 600)
        self.timeout_build = timeouts.get("build", 1800)

    def verify(
        self,
        compile_check: bool = True,
        editmode_tests: bool = False,
        playmode_tests: bool = False,
        build_target: str | None = None,
        custom_method: str | None = None,
    ) -> list[VerificationResult]:
        results: list[VerificationResult] = []
        unity_exe = self._find_unity_executable()

        if compile_check:
            result = self._run_compile_check(unity_exe)
            result["tier"] = "1"
            results.append(result)
        if editmode_tests:
            result = self._run_editmode_tests(unity_exe)
            result["tier"] = "2"
            results.append(result)
        if playmode_tests:
            result = self._run_playmode_tests(unity_exe)
            result["tier"] = "3"
            results.append(result)
        if custom_method or self.unity_config.get("custom_validation_method"):
            method = custom_method or self.unity_config["custom_validation_method"]
            result = self._run_custom_method(unity_exe, method)
            result["tier"] = "4"
            results.append(result)
        if build_target:
            result = self._run_build(unity_exe, build_target)
            result["tier"] = "5"
            results.append(result)

        return results

    def plan(
        self,
        compile_check: bool = True,
        editmode_tests: bool = False,
        playmode_tests: bool = False,
        build_target: str | None = None,
        custom_method: str | None = None,
    ) -> list[PlannedCommand]:
        return build_verification_plan(
            self._context(),
            compile_check=compile_check,
            editmode_tests=editmode_tests,
            playmode_tests=playmode_tests,
            build_target=build_target,
            custom_method=custom_method,
        )

    def _context(self) -> VerificationContext:
        return VerificationContext(
            project_path=self.project_path,
            reports_dir=self.reports_dir,
            unity_config=self.unity_config,
            unity_project_path=self._unity_project_path(),
            planned_unity_executable=self._planned_unity_executable(),
            timeout_compile=self.timeout_compile,
            timeout_tests=self.timeout_tests,
            timeout_build=self.timeout_build,
        )

    def _planned_unity_executable(self) -> str:
        configured = self.unity_config.get("executable")
        if configured and configured != "auto":
            return str(configured)
        return self._find_unity_executable() or "Unity"

    def _run_compile_check(self, unity_exe: str | None) -> VerificationResult:
        return run_compile_check(
            self._context(),
            unity_exe,
            self._run_unity_command,
            self._parse_unity_log,
        )

    def _run_editmode_tests(self, unity_exe: str | None) -> VerificationResult:
        return run_editmode_tests(self._context(), unity_exe, self._run_unity_command)

    def _run_playmode_tests(self, unity_exe: str | None) -> VerificationResult:
        return run_playmode_tests(self._context(), unity_exe, self._run_unity_command)

    def _run_build(self, unity_exe: str | None, target: str) -> VerificationResult:
        return run_build(self._context(), unity_exe, target, self._run_unity_command)

    def _run_custom_method(self, unity_exe: str | None, method: str) -> VerificationResult:
        return run_custom_method(
            self._context(),
            unity_exe,
            method,
            self._run_unity_command,
            self._process_output_summary,
        )

    def _parse_unity_log(self, log_content: str) -> dict[str, Any]:
        return parse_unity_log(log_content)

    def _run_unity_command(self, cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def _unity_project_path(self) -> str:
        configured = self.unity_config.get("project_path")
        if not configured or configured == ".":
            return str(self.project_path)
        return str(configured)

    def _process_output_summary(self, result: subprocess.CompletedProcess) -> str:
        return process_output_summary(result)

    def _find_unity_executable(self) -> str | None:
        return find_unity_executable(self.unity_config)
