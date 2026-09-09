from __future__ import annotations

from datetime import date
from importlib.resources import files
import json


def load_mobile_knowledge() -> list[dict[str, object]]:
    raw = files("kunity_yamae").joinpath("data/mobile_packs.json").read_text(encoding="utf-8")
    return json.loads(raw)


def retrieve_mobile_knowledge(query: str, *, top_k: int = 4, today: date | None = None) -> list[dict[str, object]]:
    """Return only relevant, source-backed mobile SDK cards.

    Retrieval is intentionally deterministic and local: no embedding/API call is required.
    """
    if top_k < 1 or top_k > 20:
        raise ValueError("top_k must be between 1 and 20")
    today = today or date.today()
    text = query.lower()
    ranked: list[tuple[float, dict[str, object]]] = []
    for card in load_mobile_knowledge():
        tags = [str(tag).lower() for tag in card.get("tags", [])]
        score = sum(1.0 + min(len(tag), 12) / 12 for tag in tags if tag in text)
        if score <= 0:
            continue
        row = dict(card)
        reviewed = date.fromisoformat(str(card["reviewed_on"]))
        age = (today - reviewed).days
        row["stale"] = age < 0 or age > int(card["review_after_days"])
        row["score"] = round(score, 3)
        ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], str(item[1]["id"])))
    return [row for _, row in ranked[:top_k]]


def build_mobile_context(query: str, *, top_k: int = 4, today: date | None = None) -> dict[str, object]:
    cards = retrieve_mobile_knowledge(query, top_k=top_k, today=today)
    return {
        "schema": "unity-harness.mobile-knowledge.v1",
        "query": query,
        "cards": cards,
        "policy": [
            "installed package and native dependency versions override generic examples",
            "stale cards require source re-verification before SDK code changes",
            "never invent an SDK API when the installed version is unknown",
            "authentication, payments, ads and native build changes require higher scrutiny",
        ],
    }
