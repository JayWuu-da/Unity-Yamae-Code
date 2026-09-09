"""Deterministic proposals for fully specified asset operations; no Editor writes."""
from __future__ import annotations

from typing import Any

from .worker_guidance import OBJECT_FIELDS, RECIPES


def plan_local_operation(
    kind: str, target: str, contract: dict[str, Any], hashes: dict,
    editor: dict, result: dict,
) -> dict:
    fields = list(OBJECT_FIELDS[kind])
    if kind == "prefab_bind":
        fields.append("expected_old_value")
    operation = {"op": RECIPES[kind]["operation"], "asset": target,
                 **{field: contract[field] for field in fields}}
    return {**result, "status": "planned_local",
            "route": {"role": "local", "risk": result["route"]["risk"],
                      "requires_review": True,
                      "reasons": ["fully specified operation needs no generative model"],
                      "policy": ["proposal only; live Editor identity and guards still required"]},
            "payload": {"operation": operation, "base_sha256": hashes,
                        "editor_excerpt": editor, "required_checks": RECIPES[kind]["checks"]},
            "execution_ready": False,
            "next_step": "live adapter must resolve unique objects, verify preconditions, "
                         "then guarded apply/save/reload; adapter execution is not implemented"}
