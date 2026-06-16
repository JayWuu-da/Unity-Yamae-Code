from pathlib import Path

from kunity_yamae.contracts import validate_unity_adapter_result_v2
from kunity_yamae.unity_adapters import EditorAdapter, PlayerAdapter, default_player_adapter_config


def test_editor_adapter_plan_probe_does_not_claim_editor_verification(tmp_path: Path) -> None:
    result = EditorAdapter(tmp_path).plan_probe("KUnityYamae.EditorInspectionProbe.Run")

    assert validate_unity_adapter_result_v2(result) == result
    assert result["adapter"] == "editor"
    assert result["operation"] == "plan"
    assert result["status"] == "planned"
    assert result["unity_editor_verified"] is False
    assert result["facts"]["executed"] is False


def test_player_adapter_default_status_is_disabled_dev_build_only(tmp_path: Path) -> None:
    result = PlayerAdapter(tmp_path, default_player_adapter_config()).status()

    assert validate_unity_adapter_result_v2(result) == result
    assert result["adapter"] == "player"
    assert result["operation"] == "status"
    assert result["status"] == "unavailable"
    assert result["evidence_tier"] == "unavailable"
    assert result["player"] == {
        "enabled": False,
        "protocol": "none",
        "endpoint": "",
        "timeout_ms": 3000,
        "dev_build_only": True,
    }
