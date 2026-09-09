from datetime import date

from kunity_yamae.mobile_knowledge import build_mobile_context, retrieve_mobile_knowledge
from kunity_yamae.mobile_routing import route_mobile_task


def test_deterministic_inspection_uses_local_lane() -> None:
    route = route_mobile_task("Read manifest and inspect package versions", risk_score=10)
    assert route.role == "local"
    assert route.requires_review is False


def test_bounded_low_risk_change_uses_worker() -> None:
    route = route_mobile_task("Fix one UI label typo with compile acceptance", risk_score=20)
    assert route.role == "worker"
    assert route.requires_review is True


def test_iap_and_auth_escalate_even_when_diff_is_small() -> None:
    for task in (
        "Fix IAP v5 transaction logging",
        "Link anonymous Firebase account with Google sign in",
        "Fix Apple sign in nonce handling",
        "Change AdMob rewarded callback",
    ):
        route = route_mobile_task(task, risk_score=15)
        assert route.role == "architect", task
        assert route.risk == "high"


def test_two_failures_stop_automatic_retry() -> None:
    route = route_mobile_task("Fix prefab binding", risk_score=20, failure_count=2)
    assert route.role == "human"
    assert route.risk == "blocked"


def test_mobile_knowledge_returns_only_relevant_cards() -> None:
    cards = retrieve_mobile_knowledge(
        "Unity IAP v5 purchase receipt transaction",
        today=date(2026, 9, 9),
    )
    assert cards
    assert cards[0]["id"] == "iap-v5"
    assert cards[0]["stale"] is False
    assert all(card["score"] > 0 for card in cards)


def test_mobile_context_is_source_backed_and_policy_bounded() -> None:
    context = build_mobile_context("Firebase Apple login account linking", today=date(2026, 9, 9))
    assert context["schema"] == "unity-harness.mobile-knowledge.v1"
    assert context["cards"]
    assert context["cards"][0]["sources"]
    assert any("never invent" in item for item in context["policy"])
