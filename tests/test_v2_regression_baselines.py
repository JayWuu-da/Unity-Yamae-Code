import subprocess
import sys
from pathlib import Path

from kunity_yamae.project_files import ProjectFileInventory

FIXTURE_SCRIPT = Path("tests/fixtures/make_unity_project.py")


def _create_package_first_fixture(tmp_path: Path) -> Path:
    project_path = tmp_path / "package-first"
    subprocess.run(
        [
            sys.executable,
            str(FIXTURE_SCRIPT),
            "--kind",
            "package-first",
            "--out",
            str(project_path),
            "--git-init",
        ],
        check=True,
        cwd=Path.cwd(),
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    return project_path


def test_package_first_fixture_remains_supported(tmp_path: Path) -> None:
    project_path = _create_package_first_fixture(tmp_path)

    inventory = ProjectFileInventory.collect(project_path)

    assert inventory.relative_paths(inventory.scripts) == [
        "Packages/com.example.neutral/Runtime/NeutralComponent.cs",
        "Packages/com.example.neutral/Runtime/NeutralRuntime.cs",
    ]
    assert inventory.relative_paths(inventory.asmdefs) == [
        "Packages/com.example.neutral/Runtime/NeutralRuntime.asmdef"
    ]
    assert inventory.relative_paths(inventory.package_local_content) == [
        "Packages/com.example.neutral/Runtime/NeutralComponent.cs",
        "Packages/com.example.neutral/Runtime/NeutralRuntime.asmdef",
        "Packages/com.example.neutral/Runtime/NeutralRuntime.cs",
        "Packages/com.example.neutral/Runtime/NeutralView.uxml",
    ]
    assert inventory.relative_paths(inventory.resource_files) == []


def test_v2_docs_and_fixtures_stay_project_neutral(tmp_path: Path) -> None:
    project_path = _create_package_first_fixture(tmp_path)
    banned_terms = (
        "Table" + "Datas",
        "Sh" + "op" + ".json",
        "Pass" + "Product",
        "Reward" + ".json",
        "Localize" + "Text" + ".json",
        "sku" + "-pass",
        "text" + "_pass_name",
        "Sample" + "Presenter",
    )
    checked_paths = [
        Path("plans/next-upgrade-wave-ordering.md"),
        *sorted(
            path for path in project_path.rglob("*") if path.is_file() and ".git" not in path.parts
        ),
    ]

    matches = [
        f"{path}:{term}"
        for path in checked_paths
        for term in banned_terms
        if term in path.read_text(encoding="utf-8", errors="ignore")
    ]

    assert matches == []
