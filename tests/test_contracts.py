import pytest


def test_integration_doctor_v1_contract_rejects_missing_status() -> None:
    from kunity_yamae.contracts import ContractError, validate_integration_doctor_v1

    with pytest.raises(ContractError, match="integrations.codex-cli.status"):
        validate_integration_doctor_v1(
            {
                "schema": "unity-harness.desktop-integration-doctor.v1",
                "integrations": {
                    "codex-cli": {
                        "kind": "desktop-cli",
                        "entrypoint": ".agents/skills/k-unity-yamae/SKILL.md",
                    }
                },
            }
        )


def test_run_result_v1_contract_accepts_plan_only_result() -> None:
    from kunity_yamae.contracts import validate_run_result_v1

    payload = {
        "schema": "unity-harness.run-result.v1",
        "status": "planned",
        "plan_only": True,
        "provider_requests": 0,
        "stages": [
            {"stage": "scan", "status": "ok"},
            {"stage": "risk", "status": "ok"},
        ],
    }

    assert validate_run_result_v1(payload)["status"] == "planned"
