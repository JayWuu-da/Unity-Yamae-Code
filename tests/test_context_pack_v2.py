import json
from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.context import ContextSelector
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_context_pack_includes_only_task_relevant_final_facts(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk = RiskClassifier(config).classify("Fix SamplePresenter button onClick raycast issue", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix SamplePresenter button onClick raycast issue",
        risk,
        "standard",
    )

    assert "ui_system" in context["unity_facts"]
    assert "architecture_patterns" in context["unity_facts"]
    assert "graphics_defaults" not in context["unity_facts"]
    assert "unity.ui" in context["rule_cards"]
    assert "unity.architecture-patterns" in context["rule_cards"]


def test_context_pack_infers_targets_from_cached_inventory_without_cs_tree_walk(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Given: the cached profile already contains the discovered script inventory.
    script_path = tmp_path / "Assets" / "Scripts" / "RuntimeSpawner.cs"
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class RuntimeSpawner : MonoBehaviour",
                "{",
                "    private void Start() => Instantiate(gameObject);",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".unity-harness" / "cache").mkdir(parents=True)
    (tmp_path / ".unity-harness" / "cache" / "project-profile.json").write_text(
        json.dumps(
            {
                "schema": "unity-harness.project-profile.v1",
                "project_files": {"scripts": ["Assets/Scripts/RuntimeSpawner.cs"]},
                "asset_summary": {},
                "runtime_asset_signals": {},
            }
        ),
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    risk_report = RiskClassifier(config).classify("Fix RuntimeSpawner asset spawn", {})

    def fail_cs_tree_walk(self, pattern: str):
        if pattern == "*.cs":
            raise AssertionError("unexpected full C# tree walk")
        return ()

    monkeypatch.setattr(Path, "rglob", fail_cs_tree_walk)

    # When: context is selected for a task matching the cached script name.
    context = ContextSelector(tmp_path, config).select(
        "Fix RuntimeSpawner asset spawn",
        risk_report,
        risk_report["mode"],
    )

    # Then: the target and runtime safety hints come from the cached script list.
    assert context["relevant_files"] == ["Assets/Scripts/RuntimeSpawner.cs"]
    assert context["unity_facts"]["runtime_safety"]["scripts"] == [
        "Assets/Scripts/RuntimeSpawner.cs"
    ]


def test_context_pack_uses_inventory_written_by_real_scanner(tmp_path: Path) -> None:
    script_path = tmp_path / "Assets" / "Scripts" / "RuntimeSpawner.cs"
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class RuntimeSpawner : MonoBehaviour",
                "{",
                "    private void Start() => Instantiate(gameObject);",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan()
    risk_report = RiskClassifier(config).classify("Fix RuntimeSpawner asset spawn", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix RuntimeSpawner asset spawn",
        risk_report,
        risk_report["mode"],
    )

    assert context["relevant_files"] == ["Assets/Scripts/RuntimeSpawner.cs"]


def test_context_pack_does_not_guess_undiscovered_targets_without_cached_inventory(
    tmp_path: Path,
) -> None:
    # Given: a script exists on disk, but no cached profile inventory discovered it.
    script_path = tmp_path / "Assets" / "Scripts" / "UndiscoveredGenerated.cs"
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        "using UnityEngine;\npublic sealed class UndiscoveredGenerated : MonoBehaviour {}\n",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    risk_report = RiskClassifier(config).classify("Fix UndiscoveredGenerated", {})

    # When: context is selected without cache inventory.
    context = ContextSelector(tmp_path, config).select(
        "Fix UndiscoveredGenerated",
        risk_report,
        risk_report["mode"],
    )

    # Then: no target is invented from a disk walk; unknown policy remains explicit.
    assert context["relevant_files"] == []
    assert "unknown" in context["fact_limits"]["unknown_policy"]


def test_context_pack_skips_stale_cached_runtime_scripts(tmp_path: Path) -> None:
    script_path = tmp_path / "Assets" / "Scripts" / "RuntimeSpawner.cs"
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        "using UnityEngine;\npublic sealed class RuntimeSpawner : MonoBehaviour {}\n",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan()
    script_path.unlink()
    risk_report = RiskClassifier(config).classify("Fix RuntimeSpawner asset spawn", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix RuntimeSpawner asset spawn",
        risk_report,
        risk_report["mode"],
    )

    assert context["relevant_files"] == []
    assert "runtime_safety" not in context["unity_facts"] or context["unity_facts"][
        "runtime_safety"
    ]["scripts"] == []
