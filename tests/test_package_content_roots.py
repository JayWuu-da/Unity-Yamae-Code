from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.guards.meta_guard import MetaGuard
from kunity_yamae.project_files import ProjectFileInventory
from kunity_yamae.risk import RiskClassifier


def test_default_config_protects_package_local_unity_assets(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    report = RiskClassifier(config).classify("Update local package prefab", {})

    protected = config["protected_files"]
    file_risk_scores = config["file_risk_scores"]

    assert "Packages/**/*.prefab" in protected["block_direct_write"]
    assert "Packages/**/*.asset" in protected["escalate_direct_write"]
    assert file_risk_scores["Packages/**/*.prefab"] == {"base": 85, "max": 85}
    assert "Packages/**/*.prefab" in report["blocked_operations"]


def test_meta_guard_checks_package_local_assets(tmp_path: Path) -> None:
    asset = "Packages/com.example.tool/Runtime/View.prefab"
    (tmp_path / "Packages" / "com.example.tool" / "Runtime").mkdir(parents=True)

    issues = MetaGuard(tmp_path, load_config(tmp_path)).check([asset])

    assert issues == [
        {
            "guard": "meta_pair",
            "severity": "hard_failure",
            "file": asset,
            "message": "Asset without matching .meta file",
        }
    ]


def test_project_file_inventory_includes_package_content_and_excludes_generated(
    tmp_path: Path,
) -> None:
    (tmp_path / "Assets" / "Resources" / "Runtime").mkdir(parents=True)
    (tmp_path / "Packages" / "com.example.tool" / "Runtime" / "Resources").mkdir(
        parents=True
    )
    (tmp_path / "Library" / "PackageCache" / "com.example.generated").mkdir(parents=True)
    (tmp_path / "Assets" / "Resources" / "Runtime" / "Local.prefab").write_text(
        "PrefabInstance:\n",
        encoding="utf-8",
    )
    (tmp_path / "Packages" / "com.example.tool" / "Runtime" / "Tool.asmdef").write_text(
        '{"name":"Tool.Runtime"}',
        encoding="utf-8",
    )
    (
        tmp_path
        / "Packages"
        / "com.example.tool"
        / "Runtime"
        / "Resources"
        / "PackageView.prefab"
    ).write_text("PrefabInstance:\n", encoding="utf-8")
    (
        tmp_path
        / "Library"
        / "PackageCache"
        / "com.example.generated"
        / "Generated.asmdef"
    ).write_text('{"name":"Generated"}', encoding="utf-8")

    inventory = ProjectFileInventory.collect(tmp_path)

    assert inventory.relative_paths(inventory.asmdefs) == [
        "Packages/com.example.tool/Runtime/Tool.asmdef"
    ]
    assert inventory.relative_paths(inventory.prefabs) == [
        "Assets/Resources/Runtime/Local.prefab",
        "Packages/com.example.tool/Runtime/Resources/PackageView.prefab",
    ]
    assert inventory.relative_paths(inventory.resource_files) == [
        "Assets/Resources/Runtime/Local.prefab",
        "Packages/com.example.tool/Runtime/Resources/PackageView.prefab",
    ]
    assert inventory.relative_paths(inventory.package_local_content) == [
        "Packages/com.example.tool/Runtime/Resources/PackageView.prefab",
        "Packages/com.example.tool/Runtime/Tool.asmdef",
    ]
