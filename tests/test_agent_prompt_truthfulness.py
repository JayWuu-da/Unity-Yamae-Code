from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.context import ContextSelector
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner
from tests.test_context_pack import create_ui_project
from tests.test_desktop_integration import PromptOnlyAgent


def test_context_pack_exposes_stable_fact_limits(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify("Fix prefab button raycast", profile)

    context = ContextSelector(tmp_path, config).select(
        "Fix prefab button raycast",
        risk_report,
        risk_report["mode"],
    )

    assert set(context["fact_limits"]) == {
        "source",
        "unknown_policy",
        "editor_probe_required_for",
        "no_claim_without_evidence",
    }
    assert "discovered" in context["fact_limits"]["source"]
    assert "unknown" in context["fact_limits"]["unknown_policy"]


def test_agent_prompt_includes_fact_limit_boundary(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    agent = PromptOnlyAgent("prompt-only", config, {})
    risk_report = RiskClassifier(config).classify("Fix prefab button raycast", {})

    prompt = agent._build_prompt("Fix prefab button raycast", risk_report, "asset_safe", tmp_path)

    assert "Fact Limits" in prompt
    assert "discovered facts" in prompt
    assert "unknown" in prompt
    assert "editor-probe" in prompt
    assert "Do not claim" in prompt
