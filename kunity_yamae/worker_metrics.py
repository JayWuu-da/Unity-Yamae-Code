"""Observed-usage accounting. No inference cost is guessed from role names."""
from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import Decimal
from statistics import median
from typing import Any

TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_tokens", "output_tokens")


def _count(value: object, name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be an observed non-negative integer or null")
    return value


def observed_cost(usage: dict[str, Any], rates: dict[str, Any]) -> Decimal | None:
    """Normalized API counters; input includes cache reads/writes, output includes reasoning.

    Rates are USD per million tokens with keys input, cached_input, cache_write, output.
    Missing counters/rates return unknown, NOT free. Subscription quotas are not USD billing.
    """
    counts = {name: _count(usage.get(name), name) for name in TOKEN_FIELDS}
    reasoning = _count(usage.get("reasoning_tokens"), "reasoning_tokens")
    if any(value is None for value in counts.values()):
        return None
    total = counts["input_tokens"]
    cached, written = counts["cached_input_tokens"], counts["cache_write_tokens"]
    output = counts["output_tokens"]
    if cached + written > total or (reasoning is not None and reasoning > output):
        raise ValueError("overlapping/invalid token counters")
    quantities = {"input": total - cached - written, "cached_input": cached,
                  "cache_write": written, "output": output}
    cost = Decimal(0)
    for key, count in quantities.items():
        if not count:
            continue
        if rates.get(key) is None:
            return None
        rate = Decimal(str(rates[key]))
        if not rate.is_finite() or rate < 0:
            raise ValueError("rates must be finite and non-negative")
        cost += Decimal(count) * rate / Decimal(1_000_000)
    return cost


def summarize_runs(rows: Sequence[dict[str, Any]], rates_by_model: dict[str, dict]) -> dict:
    """Include failed attempts in cost; deduplicate successful task IDs, not token records."""
    run_ids, completed, durations, costs = set(), set(), [], []
    unknown_usage = 0
    for row in rows:
        run_id, task_id = row.get("run_id"), row.get("task_id")
        if not isinstance(run_id, str) or not run_id or run_id in run_ids:
            raise ValueError("each observation requires a unique run_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("task_id is required")
        if type(row.get("verified")) is not bool or row.get("source") != "observed":
            raise ValueError("require observed usage and an explicit verified boolean")
        run_ids.add(run_id)
        if row["verified"]:
            completed.add(task_id)
        duration = row.get("wall_ms")
        if duration is not None:
            if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                    or not math.isfinite(duration) or duration < 0):
                raise ValueError("wall_ms must be a finite non-negative duration")
            durations.append(duration)
        cost = observed_cost(row.get("usage", {}), rates_by_model.get(row.get("model"), {}))
        if cost is None:
            unknown_usage += 1
        else:
            costs.append(cost)
    total = sum(costs, Decimal(0)) if rows and not unknown_usage else None
    return {"schema": "unity-harness.efficiency-summary.v1", "attempts": len(rows),
            "verified_tasks": len(completed), "unknown_cost_attempts": unknown_usage,
            "total_cost_usd": float(total) if total is not None else None,
            "cost_per_verified_task_usd": float(total / len(completed))
            if total is not None and completed else None,
            "attempt_wall_ms_p50": median(durations) if durations else None,
            "attempt_wall_ms_p95": sorted(durations)[math.ceil(.95 * len(durations)) - 1]
            if durations else None,
            "duration_observations": len(durations),
            "latency_scope": "per attempt including caller-recorded tool/verification time"}
