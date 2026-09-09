from decimal import Decimal

import pytest

from kunity_yamae.worker_metrics import observed_cost, summarize_runs

RATES = {"input": 10, "cached_input": 1, "cache_write": 12.5, "output": 50}
USAGE = {"input_tokens": 1000, "cached_input_tokens": 400, "cache_write_tokens": 200,
         "output_tokens": 100, "reasoning_tokens": 60}


def test_cache_write_pricing_and_reasoning_not_double_counted():
    assert observed_cost(USAGE, RATES) == Decimal("0.0119")
    assert observed_cost({**USAGE, "reasoning_tokens": 0}, RATES) == Decimal("0.0119")


@pytest.mark.parametrize("key", list(USAGE)[:4])
def test_missing_usage_is_unknown_not_zero(key):
    usage = dict(USAGE)
    usage.pop(key)
    assert observed_cost(usage, RATES) is None


def test_missing_relevant_rate_is_unknown():
    assert observed_cost(USAGE, {"input": 10}) is None


@pytest.mark.parametrize("values", [{"input_tokens": True}, {"output_tokens": -1},
                                    {"cached_input_tokens": 9999}, {"reasoning_tokens": 101}])
def test_invalid_usage_is_rejected(values):
    with pytest.raises(ValueError):
        observed_cost({**USAGE, **values}, RATES)


def row(number, *, verified=False, usage=None):
    return {"run_id": str(number), "task_id": "same-task", "verified": verified,
            "source": "observed", "usage": USAGE if usage is None else usage,
            "model": "fixture-model", "wall_ms": number * 100}


def test_failed_attempts_count_toward_verified_task_cost():
    result = summarize_runs([row(1), row(2, verified=True)], {"fixture-model": RATES})
    assert result["attempts"] == 2 and result["verified_tasks"] == 1
    assert result["total_cost_usd"] == pytest.approx(.0238)
    assert result["cost_per_verified_task_usd"] == pytest.approx(.0238)
    assert result["attempt_wall_ms_p50"] == 150
    assert result["attempt_wall_ms_p95"] == 200


def test_unknown_attempt_prevents_fake_complete_total():
    result = summarize_runs([row(1, usage={}), row(2, verified=True)], {"fixture-model": RATES})
    assert result["unknown_cost_attempts"] == 1
    assert result["total_cost_usd"] is None and result["cost_per_verified_task_usd"] is None


def test_all_failed_is_not_free_success():
    result = summarize_runs([row(1)], {"fixture-model": RATES})
    assert result["verified_tasks"] == 0 and result["cost_per_verified_task_usd"] is None


def test_duplicate_record_rejected_and_verified_tasks_deduplicated():
    with pytest.raises(ValueError):
        summarize_runs([row(1), row(1)], {})
    result = summarize_runs([row(1, verified=True), row(2, verified=True)],
                            {"fixture-model": RATES})
    assert result["verified_tasks"] == 1
