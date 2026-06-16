import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path("kunity_yamae")
MAX_PURE_LOC = 250
SIZE_EXEMPTIONS: dict[Path, str] = {
    Path("kunity_yamae/cli_release_check.py"): (
        "release-check keeps its human-readable audit keys together so the JSON contract is stable"
    ),
    Path("kunity_yamae/desktop_integration.py"): (
        "desktop integration owns generated Codex and Claude entrypoint templates"
    ),
}


def test_python_package_modules_stay_under_cleanup_size_limit() -> None:
    package_files = sorted(PACKAGE_ROOT.rglob("*.py"))
    oversized = [
        f"{path.as_posix()}:{_pure_loc(path)}"
        for path in package_files
        if _pure_loc(path) > MAX_PURE_LOC and path not in SIZE_EXEMPTIONS
    ]

    assert oversized == []


def test_architecture_size_exemptions_must_be_explicitly_justified() -> None:
    unjustified = [
        path.as_posix()
        for path, reason in SIZE_EXEMPTIONS.items()
        if not path.is_relative_to(PACKAGE_ROOT) or not reason.strip()
    ]

    assert unjustified == []


def test_run_command_is_thin_click_boundary() -> None:
    cli_run = Path("kunity_yamae/cli_run.py").read_text(encoding="utf-8")
    run_pipeline = Path("kunity_yamae/run_pipeline.py").read_text(encoding="utf-8")

    assert "from .run_pipeline import run_mutating_pipeline" in cli_run
    assert "def _run_mutating_pipeline" not in cli_run
    assert "def _emit_agent_patch" not in cli_run
    assert _pure_loc(Path("kunity_yamae/cli_run.py")) <= 140
    assert _imported_modules(run_pipeline).isdisjoint({"click", "rich.console"})
    assert "ctx.exit" not in run_pipeline
    assert "click.echo" not in run_pipeline


def test_run_steps_do_not_catch_untyped_exception_boundary() -> None:
    run_steps = Path("kunity_yamae/cli_run_steps.py").read_text(encoding="utf-8")

    assert "except Exception" not in run_steps
    assert "except BaseException" not in run_steps
    assert "except:" not in run_steps
    assert "RuntimeError" not in run_steps


def test_run_agent_step_does_not_swallow_programming_errors(tmp_path: Path, monkeypatch) -> None:
    from kunity_yamae import agents
    from kunity_yamae.cli_run_steps import run_agent_step
    from kunity_yamae.ledger import EvidenceLedger

    class BrokenAgent:
        def execute(self, *args, **kwargs):
            raise AssertionError("programming bug")

    monkeypatch.setattr(agents, "get_agent", lambda *_args, **_kwargs: BrokenAgent())

    with pytest.raises(AssertionError, match="programming bug"):
        run_agent_step(
            "broken",
            {},
            tmp_path,
            "task",
            {"risk_score": 1},
            "fast_patch",
            EvidenceLedger(tmp_path),
            quiet=True,
        )


def _imported_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _pure_loc(path: Path) -> int:
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
