import pytest

import kunity_yamae.contracts as contracts
from kunity_yamae.contracts import ContractError


def _valid_editor_planned_result_v2() -> dict[str, object]:
    return {
        "schema": "unity-harness.unity-adapter-result.v2",
        "adapter": "editor",
        "operation": "plan",
        "status": "planned",
        "evidence_tier": "planned",
        "unity_editor_verified": False,
        "facts": {"planned_commands": []},
        "errors": [],
    }


def _valid_player_default_result_v2() -> dict[str, object]:
    return {
        "schema": "unity-harness.unity-adapter-result.v2",
        "adapter": "player",
        "operation": "status",
        "status": "unavailable",
        "evidence_tier": "unavailable",
        "unity_editor_verified": False,
        "player": {
            "enabled": False,
            "protocol": "none",
            "endpoint": "",
            "timeout_ms": 3000,
            "dev_build_only": True,
        },
        "facts": {},
        "errors": [{"code": "player_adapter_unavailable"}],
    }


def test_accepts_known_unity_adapter_v2_tiers() -> None:
    payload = _valid_editor_planned_result_v2()

    assert contracts.validate_unity_adapter_result_v2(payload) == payload


def test_rejects_unknown_unity_adapter_v2_tier() -> None:
    payload = _valid_editor_planned_result_v2()
    payload["evidence_tier"] = "inspector_guess"

    with pytest.raises(ContractError, match="evidence_tier"):
        contracts.validate_unity_adapter_result_v2(payload)


def test_rejects_editor_planned_result_claiming_verified() -> None:
    payload = _valid_editor_planned_result_v2()
    payload["unity_editor_verified"] = True

    with pytest.raises(ContractError, match="unity_editor_verified"):
        contracts.validate_unity_adapter_result_v2(payload)


def test_accepts_player_default_unavailable_dev_build_only() -> None:
    payload = _valid_player_default_result_v2()

    assert contracts.validate_unity_adapter_result_v2(payload) == payload


def test_rejects_player_default_without_dev_build_only() -> None:
    payload = _valid_player_default_result_v2()
    player = payload["player"]
    assert isinstance(player, dict)
    player["dev_build_only"] = False

    with pytest.raises(ContractError, match="player.dev_build_only"):
        contracts.validate_unity_adapter_result_v2(payload)
