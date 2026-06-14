from pathlib import Path

from .unity_profile_common import iter_project_files, relative_path


def detect_architecture_patterns(project_path: Path) -> dict:
    buckets = _collect_architecture_buckets(project_path)
    presenters = buckets["presenters"]
    views = buckets["views"]
    controllers = buckets["controllers"]
    managers = buckets["managers"]
    services = buckets["services"]
    detected = []
    if presenters and (views or controllers):
        detected.append("mvp")
    if controllers and views:
        detected.append("mvc")
    if managers:
        detected.append("manager")
    if services:
        detected.append("service")
    confidence = _architecture_confidence(presenters, controllers, managers, services)
    warnings = []
    if confidence != "high":
        warnings.append("Do not assume architecture ownership from names alone.")
    return {
        "detected": detected,
        "presenters": presenters[:25],
        "views": views[:25],
        "controllers": controllers[:25],
        "managers": managers[:25],
        "services": services[:25],
        "event_buses": buckets["event_buses"][:25],
        "scriptable_objects": buckets["scriptable_objects"][:25],
        "confidence": confidence,
        "warnings": warnings,
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


def _architecture_confidence(
    presenters: list[str],
    controllers: list[str],
    managers: list[str],
    services: list[str],
) -> str:
    if presenters and controllers:
        return "high"
    if presenters or controllers or managers or services:
        return "medium"
    return "low"
