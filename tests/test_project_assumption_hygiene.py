import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from kunity_yamae import project_assumption_hygiene
from kunity_yamae.project_assumption_hygiene import (
    collect_project_assumption_hygiene,
    git_visible_files,
)


def _load_scaffold_validator() -> ModuleType:
    script_path = Path("skills/unity-data-validator-builder/scripts/scaffold_validator.py")
    spec = importlib.util.spec_from_file_location("scaffold_validator", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scaffold_validator = _load_scaffold_validator()


def test_scaffold_default_profile_requires_project_local_configuration() -> None:
    profile = yaml.safe_load(scaffold_validator.default_profile("neutral-domain"))

    assert profile == {
        "domain": "neutral-domain",
        "table_root": "<configure-project-table-root>",
        "tables": [],
        "relationships": [],
    }


def test_generated_readme_does_not_record_absolute_project_path(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = tmp_path / "GeneratedValidator"

    scaffold_validator.prepare_output(project_path, output_path, force=False)
    scaffold_validator.write_files(project_path, output_path, "neutral-domain")

    readme = (output_path / "README.md").read_text(encoding="utf-8")

    assert str(project_path) not in readme
    assert "<unity-project-root>" in readme


def test_hygiene_fixture_uses_synthetic_sentinel_only(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("ForbiddenProjectTokenForTest", encoding="utf-8")

    assert "ForbiddenProjectTokenForTest" in sample.read_text(encoding="utf-8")


def test_project_assumption_hygiene_rejects_tracked_scaffold_shape_tokens(
    tmp_path: Path,
) -> None:
    git = ["git", "-c", "init.defaultBranch=main"]
    subprocess.run([*git, "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    template = tmp_path / "skills" / "unity-data-validator-builder" / "templates" / "README.md"
    template.parent.mkdir(parents=True)
    tokens = [
        "Assets" + "/Resources/" + "Ta" + "ble" + "Datas",
        "Sh" + "op" + ".json",
        "Pass" + "Product",
        "Reward" + ".json",
        "Localize" + "Text" + ".json",
        "PRODUCT" + "_GROUP_ID",
        "sku" + "-pass",
        "text" + "_pass_name",
    ]
    template.write_text("\n".join(tokens), encoding="utf-8")
    subprocess.run([*git, "add", "."], cwd=tmp_path, check=True, stdout=subprocess.PIPE)

    result = collect_project_assumption_hygiene(tmp_path)

    assert result == {
        "passed": False,
        "matches": [
            f"skills/unity-data-validator-builder/templates/README.md:{line}:{token}"
            for line, token in enumerate(tokens, 1)
        ],
    }


def test_git_visible_files_uses_cached_others_exclude_standard_with_scopes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_check_output(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
    ) -> str:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["text"] = text
        return "kunity_yamae/example.py\n"

    monkeypatch.setattr(project_assumption_hygiene.subprocess, "check_output", fake_check_output)

    paths = git_visible_files(tmp_path, ("kunity_yamae", "tests"))

    assert captured == {
        "command": [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "kunity_yamae",
            "tests",
        ],
        "cwd": tmp_path,
        "text": True,
    }
    assert paths == [tmp_path / "kunity_yamae" / "example.py"]


def test_git_visible_files_includes_untracked_visible_and_excludes_ignored(
    tmp_path: Path,
) -> None:
    git = ["git", "-c", "init.defaultBranch=main"]
    subprocess.run([*git, "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    (tmp_path / ".gitignore").write_text(".unity-harness/\n", encoding="utf-8")
    source = tmp_path / "kunity_yamae" / "visible.py"
    private_artifact = tmp_path / ".unity-harness" / "plans" / "evidence.txt"
    source.parent.mkdir()
    private_artifact.parent.mkdir(parents=True)
    source.write_text("untracked source", encoding="utf-8")
    private_artifact.write_text("ignored artifact", encoding="utf-8")

    paths = git_visible_files(tmp_path, ("kunity_yamae", ".unity-harness"))

    assert paths == [source]


def test_collect_project_assumption_hygiene_reports_git_unavailable_without_scanning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_artifact = tmp_path / ".unity-harness" / "plans" / "evidence.txt"
    private_artifact.parent.mkdir(parents=True)
    private_artifact.write_text("Sh" + "op" + ".json", encoding="utf-8")

    def fake_check_output(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
    ) -> str:
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(project_assumption_hygiene.subprocess, "check_output", fake_check_output)

    result = collect_project_assumption_hygiene(tmp_path)

    assert result == {
        "passed": False,
        "matches": [],
        "available": False,
        "failure": "git unavailable",
    }


def test_collect_project_assumption_hygiene_reports_non_worktree_without_scanning(
    tmp_path: Path,
) -> None:
    private_artifact = tmp_path / ".unity-harness" / "plans" / "evidence.txt"
    source = tmp_path / "kunity_yamae" / "visible.py"
    private_artifact.parent.mkdir(parents=True)
    source.parent.mkdir()
    private_artifact.write_text("Sh" + "op" + ".json", encoding="utf-8")
    source.write_text("Sh" + "op" + ".json", encoding="utf-8")

    result = collect_project_assumption_hygiene(tmp_path)

    assert result == {
        "passed": False,
        "matches": [],
        "available": False,
        "failure": "git ls-files failed",
    }
