from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict


class PlannedCommand(TypedDict):
    name: str
    tier: str
    status: str
    passed: bool
    command: list[str]


class VerificationResult(TypedDict, total=False):
    name: str
    status: str
    passed: bool
    details: str
    log_path: str
    xml_path: str
    tier: str


@dataclass(frozen=True, slots=True)
class VerificationContext:
    project_path: Path
    reports_dir: Path
    unity_config: dict[str, Any]
    unity_project_path: str
    planned_unity_executable: str
    timeout_compile: int
    timeout_tests: int
    timeout_build: int
