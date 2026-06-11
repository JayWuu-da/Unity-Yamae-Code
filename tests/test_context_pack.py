import json
from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.context import ContextSelector
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner


def create_ui_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n", encoding="utf-8"
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.ugui": "2.0.0"}}),
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "UI" / "ShopButton.prefab").write_text(
        "GameObject:\n  m_Name: ShopButton\nCanvas:\nGraphicRaycaster:\nm_OnClick:\n",
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scripts").mkdir(parents=True)
    (project_path / "Assets" / "Scripts" / "ShopPresenter.cs").write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class ShopPresenter : MonoBehaviour",
                "{",
                "    private void Reset() {}",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_context_pack_selects_ui_rules_and_unity_facts(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    scanner = UnityProjectScanner(tmp_path, config)
    scanner.scan(deep=True)
    risk_report = RiskClassifier(config).classify("Fix UI button onClick raycast issue", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix UI button onClick raycast issue", risk_report, "standard"
    )

    assert "unity.ui" in context["rule_cards"]
    assert context["unity_facts"]["ui_system"]["prefab_count"] == 1
    assert (
        "Verify EventSystem, GraphicRaycaster, interactable state, and raycast blockers."
        in context["manual_checks"]
    )


def test_context_pack_selects_graphics_rules_for_texture_task(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Audit Android iOS texture compression settings", {}
    )

    context = ContextSelector(tmp_path, config).select(
        "Audit Android iOS texture compression settings", risk_report, "standard"
    )

    assert "unity.graphics-platform" in context["rule_cards"]
    assert (
        "Compare Android, iOS, and PC import overrides before recommending changes."
        in context["manual_checks"]
    )


def test_context_pack_selects_execution_path_rule_for_ui_route_task(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Fix the shop popup button route and controller reset path", {}
    )

    context = ContextSelector(tmp_path, config).select(
        "Fix the shop popup button route and controller reset path",
        risk_report,
        "standard",
    )

    assert "unity.execution-path" in context["rule_cards"]
    assert (
        "Trace the real user path before editing: entry point, open/create call, "
        "prefab or listener binding, controller reset, lock conditions, and final renderer."
        in context["manual_checks"]
    )


def test_context_pack_selects_data_contract_rule_for_payload_task(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Verify reward table localization and final packet payload contract", {}
    )

    context = ContextSelector(tmp_path, config).select(
        "Verify reward table localization and final packet payload contract",
        risk_report,
        "standard",
    )

    assert "unity.data-contracts" in context["rule_cards"]
    assert "unity.execution-path" not in context["rule_cards"]
    assert (
        "Verify source table rows, localization keys, displayed text, request/response DTOs, "
        "final payload shape, merge rules, and response apply path."
        in context["manual_checks"]
    )


def test_risk_classifier_does_not_treat_controller_reset_path_as_lifecycle(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)

    risk_report = RiskClassifier(config).classify(
        "Fix the shop popup button route and controller reset path",
        {},
    )

    assert "MonoBehaviour lifecycle (reset)" not in risk_report["triggers"]
    assert "Unity execution path tracing" in risk_report["triggers"]
    assert risk_report["mode"] == "asset_safe"
    assert risk_report["blocked_operations"]


def test_risk_classifier_matches_data_contract_plural_and_camel_case(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)

    plural_report = RiskClassifier(config).classify("Fix balance tables", {})
    camel_report = RiskClassifier(config).classify("Fix RewardTable values", {})

    assert "Unity data contract/payload" in plural_report["triggers"]
    assert "unity.data-contracts" in plural_report["required_rule_cards"]
    assert "Unity data contract/payload" in camel_report["triggers"]
    assert "unity.data-contracts" in camel_report["required_rule_cards"]


def test_context_pack_matches_execution_path_for_camel_case_popup(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify("Fix OpenShopPopup", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix OpenShopPopup",
        risk_report,
        risk_report["mode"],
    )

    assert "Unity execution path tracing" in risk_report["triggers"]
    assert "unity.execution-path" in context["rule_cards"]
    assert any("Trace the real user path" in check for check in context["manual_checks"])


def test_context_pack_includes_manual_checks_for_plural_contract_terms(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify("Audit payloads responses and packets", {})

    context = ContextSelector(tmp_path, config).select(
        "Audit payloads responses and packets",
        risk_report,
        risk_report["mode"],
    )

    assert "unity.data-contracts" in context["rule_cards"]
    assert any("final payload shape" in check for check in context["manual_checks"])


def test_risk_classifier_matches_common_unity_api_keyword_variants(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)

    addressables_report = RiskClassifier(config).classify(
        "Fix Addressables path for ability VFX",
        {},
    )
    buttons_report = RiskClassifier(config).classify("Fix shop buttons", {})
    event_system_report = RiskClassifier(config).classify(
        "Fix EventSystem configuration",
        {},
    )
    rect_transform_report = RiskClassifier(config).classify("Fix RectTransform anchors", {})

    assert "Resources/Addressables path change" in addressables_report["triggers"]
    assert "unity.resources-addressables" in addressables_report["required_rule_cards"]
    assert "Unity UI interaction/hierarchy" in buttons_report["triggers"]
    assert "Unity UI interaction/hierarchy" in event_system_report["triggers"]
    assert "Unity UI interaction/hierarchy" in rect_transform_report["triggers"]


def test_context_pack_includes_ui_facts_for_common_ui_api_variants(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)

    for task in (
        "Fix shop buttons",
        "Fix EventSystem configuration",
        "Fix RectTransform anchors",
    ):
        risk_report = RiskClassifier(config).classify(task, {})
        context = ContextSelector(tmp_path, config).select(task, risk_report, risk_report["mode"])

        assert "Unity UI interaction/hierarchy" in risk_report["triggers"]
        assert "ui_system" in context["unity_facts"]


def test_risk_classifier_still_matches_explicit_monobehaviour_reset(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)

    risk_report = RiskClassifier(config).classify("Override MonoBehaviour Reset()", {})

    assert "MonoBehaviour lifecycle (reset)" in risk_report["triggers"]
    assert "unity.monobehaviour-lifecycle" in risk_report["required_rule_cards"]


def test_context_pack_matches_camel_case_csharp_file_names(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Fix ShopPresenter button onClick raycast issue",
        {},
    )

    context = ContextSelector(tmp_path, config).select(
        "Fix ShopPresenter button onClick raycast issue",
        risk_report,
        risk_report["mode"],
    )

    assert "Assets/Scripts/ShopPresenter.cs" in context["relevant_files"]
    assert context["summaries"][0]["path"] == "Assets/Scripts/ShopPresenter.cs"


def test_context_pack_mode_override_controls_manual_inspection_check(
    tmp_path: Path,
) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify("Fix typo in ShopPresenter", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix typo in ShopPresenter",
        risk_report,
        "asset_safe",
    )

    assert context["mode"] == "asset_safe"
    assert any("Run Unity Editor/manual inspection" in check for check in context["manual_checks"])
