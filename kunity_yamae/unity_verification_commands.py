from __future__ import annotations

from pathlib import Path

from .constants import HARNESS_BUILD_ENTRY_METHOD
from .unity_verification_contracts import VerificationContext


def build_player_command(
    context: VerificationContext,
    unity_exe: str,
    build_target: str,
    log_path: Path,
) -> list[str]:
    output_path = context.reports_dir / "builds" / build_target / _build_output_name(build_target)
    return [
        unity_exe,
        "-batchmode",
        "-quit",
        "-projectPath",
        context.unity_project_path,
        "-buildTarget",
        build_target,
        "-executeMethod",
        HARNESS_BUILD_ENTRY_METHOD,
        "-kunityBuildTarget",
        build_target,
        "-kunityBuildOutput",
        str(output_path),
        "-logFile",
        str(log_path),
    ]


def _build_output_name(build_target: str) -> str:
    if build_target == "StandaloneWindows64":
        return "KUnityYamaeBuild.exe"
    return "KUnityYamaeBuild"
