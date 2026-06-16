from pathlib import Path

from kunity_yamae.project_files import ProjectFileInventory
from kunity_yamae.semantic_index import detect_runtime_asset_signals, runtime_safety_hints


def test_runtime_asset_signals_do_not_emit_name_derived_categories(tmp_path: Path) -> None:
    prefab_name = "Neutral" + "Ra" + "in" + "Sl" + "ash" + "Au" + "ra" + ".prefab"
    prefab = tmp_path / "Assets" / "Resources" / "Effects" / prefab_name
    prefab.parent.mkdir(parents=True)
    prefab.write_text("PrefabInstance:\nParticleSystem:\n", encoding="utf-8")

    signals = detect_runtime_asset_signals(tmp_path)

    assert signals["summary"]["prefab_count"] == 1
    assert signals["prefab_candidates"] == [
        {"path": f"Assets/Resources/Effects/{prefab_name}", "source": "resources_prefab"}
    ]
    assert signals["category_counts"] == {}
    assert any("not semantic proof" in warning for warning in signals["warnings"])


def test_runtime_asset_signals_respect_explicit_caps_and_inventory(
    tmp_path: Path,
) -> None:
    # Given: more prefabs than the requested cap, generated folders, and package-local content.
    for index in range(5):
        prefab = tmp_path / "Assets" / "Resources" / "RuntimeAssets" / f"BossLoot{index}.prefab"
        prefab.parent.mkdir(parents=True, exist_ok=True)
        prefab.write_text("PrefabInstance:\n", encoding="utf-8")
    generated_prefab = tmp_path / "Library" / "GeneratedBossLoot.prefab"
    generated_prefab.parent.mkdir(parents=True)
    generated_prefab.write_text("PrefabInstance:\n", encoding="utf-8")
    package_prefab = tmp_path / "Packages" / "com.example.local" / "Runtime" / "PackageBoss.prefab"
    package_prefab.parent.mkdir(parents=True)
    package_prefab.write_text("PrefabInstance:\n", encoding="utf-8")
    inventory = ProjectFileInventory.collect(tmp_path)

    # When: runtime asset signals are collected with an explicit cap.
    signals = detect_runtime_asset_signals(
        tmp_path,
        inventory=inventory,
        prefab_candidate_cap=3,
    )

    # Then: the cap is honored without dropping package summary evidence or adding name categories.
    candidate_paths = [candidate["path"] for candidate in signals["prefab_candidates"]]
    assert len(candidate_paths) == 3
    assert signals["summary"]["prefab_count"] == 6
    assert signals["summary"]["resources_prefab_count"] == 5
    assert signals["summary"]["package_prefab_count"] == 1
    assert not any(path.startswith("Library/") for path in candidate_paths)
    assert "Packages/com.example.local/Runtime/PackageBoss.prefab" in candidate_paths
    assert signals["category_counts"] == {}


def test_runtime_safety_hints_respect_explicit_script_cap_and_inventory(
    tmp_path: Path,
) -> None:
    # Given: runtime-sensitive scripts exceed the requested cap and generated scripts exist.
    for index in range(4):
        script = tmp_path / "Assets" / "Scripts" / f"RuntimeSpawner{index}.cs"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            "\n".join(
                [
                    "using UnityEngine;",
                    "public sealed class RuntimeSpawner : MonoBehaviour",
                    "{",
                    "    private void Spawn()",
                    "    {",
                    "        Resources.Load<GameObject>(\"RuntimeAssets/BossLoot\");",
                    "        Instantiate(gameObject);",
                    "    }",
                    "}",
                ]
            ),
            encoding="utf-8",
        )
    generated_script = tmp_path / "Library" / "GeneratedRuntimeSpawner.cs"
    generated_script.parent.mkdir(parents=True)
    generated_script.write_text("Instantiate(gameObject);", encoding="utf-8")
    inventory = ProjectFileInventory.collect(tmp_path)

    # When: runtime safety hints are requested with an explicit script cap.
    hints = runtime_safety_hints(
        "Add runtime asset Resources.Load spawn collider visual smoke",
        tmp_path,
        inventory=inventory,
        script_cap=2,
    )

    # Then: the cap is honored and generated folders remain absent.
    assert len(hints["scripts"]) == 2
    assert not any(script.startswith("Library/") for script in hints["scripts"])
    assert all(script.startswith("Assets/Scripts/RuntimeSpawner") for script in hints["scripts"])
