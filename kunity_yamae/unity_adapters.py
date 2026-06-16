from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import validate_unity_adapter_result_v2


def default_player_adapter_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "protocol": "none",
        "endpoint": "",
        "timeout_ms": 3000,
        "dev_build_only": True,
    }


class EditorAdapter:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def plan_probe(self, method: str) -> dict[str, Any]:
        return validate_unity_adapter_result_v2(
            {
                "schema": "unity-harness.unity-adapter-result.v2",
                "adapter": "editor",
                "operation": "plan",
                "status": "planned",
                "evidence_tier": "planned",
                "unity_editor_verified": False,
                "facts": {
                    "project": str(self.project_path),
                    "custom_method": method,
                    "executed": False,
                },
                "errors": [],
            }
        )


class PlayerAdapter:
    def __init__(self, project_path: Path, config: dict[str, Any] | None = None) -> None:
        self.project_path = project_path
        self.config = default_player_adapter_config() | (config or {})

    def status(self) -> dict[str, Any]:
        player = default_player_adapter_config()
        return validate_unity_adapter_result_v2(
            {
                "schema": "unity-harness.unity-adapter-result.v2",
                "adapter": "player",
                "operation": "status",
                "status": "unavailable",
                "evidence_tier": "unavailable",
                "unity_editor_verified": False,
                "facts": {
                    "project": str(self.project_path),
                    "dev_build_only": True,
                    "connected": False,
                },
                "player": player,
                "errors": [{"code": "player_adapter_unavailable"}],
            }
        )
