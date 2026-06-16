from pathlib import Path
from typing import Any

from .unity_profile_common import iter_project_files, relative_path


def detect_architecture_patterns(project_path: Path) -> dict[str, Any]:
    buckets = _collect_architecture_buckets(project_path)
    presenters = buckets["presenters"]
    views = buckets["views"]
    controllers = buckets["controllers"]
    managers = buckets["managers"]
    services = buckets["services"]
    role_signals = _role_signals(buckets)
    return {
        "detected": [],
        "presenters": presenters[:25],
        "views": views[:25],
        "controllers": controllers[:25],
        "managers": managers[:25],
        "services": services[:25],
        "event_buses": buckets["event_buses"][:25],
        "scriptable_objects": buckets["scriptable_objects"][:25],
        "role_signals": role_signals[:50],
        "confidence": "low",
        "warnings": ["Do not assume architecture ownership from names alone."],
    }


def _collect_architecture_buckets(project_path: Path) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "presenters": [],
        "views": [],
        "controllers": [],
        "managers": [],
        "services": [],
        "event_buses": [],
        "scriptable_objects": [],
    }
    for path in iter_project_files(project_path, "*.cs"):
        content = path.read_text(encoding="utf-8", errors="replace")
        relative = relative_path(project_path, path)
        stem = path.stem.lower()
        if "presenter" in stem:
            buckets["presenters"].append(relative)
        if stem.endswith("view") or "view" in stem:
            buckets["views"].append(relative)
        if "controller" in stem:
            buckets["controllers"].append(relative)
        if "manager" in stem:
            buckets["managers"].append(relative)
        if "service" in stem:
            buckets["services"].append(relative)
        if "eventbus" in stem or "event bus" in content.lower():
            buckets["event_buses"].append(relative)
        if "ScriptableObject" in content:
            buckets["scriptable_objects"].append(relative)
    return buckets


def _role_signals(buckets: dict[str, list[str]]) -> list[dict[str, str]]:
    role_names = {
        "presenters": "presenter",
        "views": "view",
        "controllers": "controller",
        "managers": "manager",
        "services": "service",
        "event_buses": "event_bus",
        "scriptable_objects": "scriptable_object",
    }
    signals: list[dict[str, str]] = []
    for bucket, role in role_names.items():
        for path in buckets[bucket]:
            signals.append(
                {
                    "path": path,
                    "role": role,
                    "source": "content" if bucket == "scriptable_objects" else "filename",
                    "confidence": "low",
                }
            )
    return signals
