from pathlib import Path

from kunity_yamae.verifier import UnityVerifier


def test_verifier_builds_explicit_context_contract(tmp_path: Path) -> None:
    from kunity_yamae.unity_verification_contracts import VerificationContext

    verifier = UnityVerifier(
        tmp_path,
        {
            "unity": {"project_path": "."},
            "verification": {"timeouts": {"compile": 11, "tests": 22, "build": 33}},
        },
    )

    context = verifier._context()

    assert isinstance(context, VerificationContext)
    assert context.project_path == tmp_path
    assert context.reports_dir == tmp_path / ".unity-harness" / "reports"
    assert context.unity_project_path == str(tmp_path)
    assert context.timeout_compile == 11
    assert context.timeout_tests == 22
    assert context.timeout_build == 33


def test_verifier_plan_returns_planned_command_contract(tmp_path: Path) -> None:
    from kunity_yamae.unity_verification_contracts import PlannedCommand

    planned = UnityVerifier(tmp_path, {"unity": {"project_path": "."}}).plan(
        compile_check=True,
        editmode_tests=True,
        playmode_tests=True,
        build_target="StandaloneWindows64",
        custom_method="Harness.Check",
    )

    assert len(planned) == 5
    for command in planned:
        typed_command: PlannedCommand = command
        assert typed_command["status"] == "planned"
        assert typed_command["passed"] is False
        assert isinstance(typed_command["command"], list)
        assert typed_command["command"][0]


def test_verifier_verify_returns_verification_result_contract(tmp_path: Path) -> None:
    from kunity_yamae.unity_verification_contracts import VerificationResult

    verifier = UnityVerifier(tmp_path, {"unity": {"executable": "missing-unity"}})

    result = verifier.verify(compile_check=True)[0]
    typed_result: VerificationResult = result

    assert typed_result["name"] == "compile/import"
    assert typed_result["status"] == "skipped"
    assert typed_result["passed"] is False
    assert "Unity executable" in typed_result["details"]
