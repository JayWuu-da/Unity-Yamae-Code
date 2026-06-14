import re
from pathlib import Path
from typing import Final

from .profile_cache import load_cached_profile as load_cached_profile
from .unity_profile_architecture import detect_architecture_patterns
from .unity_profile_common import has_missing_script, iter_project_files, relative_path
from .unity_profile_graphics import detect_graphics_defaults

RENDER_PIPELINE_PACKAGES: Final[dict[str, str]] = {
    "com.unity.render-pipelines.universal": "urp",
    "com.unity.render-pipelines.high-definition": "hdrp",
}


def collect_unity_facts(project_path: Path, packages: dict[str, str]) -> dict:
    return {
        "render_pipeline": _detect_render_pipeline(project_path, packages),
        "input_system": _detect_input_system(project_path, packages),
        "platform_targets": _detect_platform_targets(project_path),
        "asset_summary": _detect_asset_summary(project_path),
        "ui_system": _detect_ui_system(project_path),
        "graphics_defaults": detect_graphics_defaults(project_path),
        "architecture_patterns": detect_architecture_patterns(project_path),
    }


def _detect_render_pipeline(project_path: Path, packages: dict[str, str]) -> str:
    for package_name, pipeline in RENDER_PIPELINE_PACKAGES.items():
        if package_name in packages:
            return pipeline
    graphics_settings = project_path / "ProjectSettings" / "GraphicsSettings.asset"
    if not graphics_settings.exists():
        return "builtin"
    content = graphics_settings.read_text(encoding="utf-8", errors="replace")
    if "m_RenderPipelineAsset: {fileID: 0}" in content:
        return "builtin"
    if "m_RenderPipelineAsset:" in content:
        return "srp"
    return "builtin"


def _detect_input_system(project_path: Path, packages: dict[str, str]) -> str:
    has_new_input = "com.unity.inputsystem" in packages
    settings = project_path / "ProjectSettings" / "ProjectSettings.asset"
    content = settings.read_text(encoding="utf-8", errors="replace") if settings.exists() else ""
    if "activeInputHandler: 2" in content:
        return "both"
    if "activeInputHandler: 1" in content:
        return "new" if has_new_input else "old"
    if "activeInputHandler: 0" in content:
        return "old"
    return "new" if has_new_input else "unknown"


def _detect_platform_targets(project_path: Path) -> list[str]:
    targets: set[str] = set()
    for meta_path in iter_project_files(project_path, "*.meta"):
        content = meta_path.read_text(encoding="utf-8", errors="replace")
        targets.update(re.findall(r"buildTarget:\s*([A-Za-z0-9_]+)", content))
    return sorted(targets)


def _detect_asset_summary(project_path: Path) -> dict:
    prefabs = list(iter_project_files(project_path, "*.prefab"))
    scenes = list(iter_project_files(project_path, "*.unity"))
    scriptable_assets = list(iter_project_files(project_path, "*.asset"))
    return {
        "prefab_count": len(prefabs),
        "scene_count": len(scenes),
        "asset_count": len(scriptable_assets),
        "prefabs": [relative_path(project_path, path) for path in prefabs[:25]],
        "scenes": [relative_path(project_path, path) for path in scenes[:25]],
    }


def _detect_ui_system(project_path: Path) -> dict:
    totals = _new_ui_totals()
    ui_paths: list[str] = []
    prefab_wiring: list[dict] = []
    for path in [
        *iter_project_files(project_path, "*.prefab"),
        *iter_project_files(project_path, "*.unity"),
    ]:
        content = path.read_text(encoding="utf-8", errors="replace")
        if not _has_ui_tokens(content):
            continue
        if path.suffix == ".prefab":
            totals["prefab_count"] += 1
            prefab_wiring.append(_prefab_wiring(project_path, path, content))
        _add_ui_counts(totals, content)
        ui_paths.append(relative_path(project_path, path))
    return {
        **totals,
        "prefab_wiring": prefab_wiring[:25],
        "hierarchy_warnings": _ui_hierarchy_warnings(totals),
        "paths": ui_paths[:25],
    }


def _new_ui_totals() -> dict[str, int]:
    return {
        "prefab_count": 0,
        "button_like_count": 0,
        "event_system_count": 0,
        "graphic_raycaster_count": 0,
        "canvas_group_count": 0,
        "missing_script_count": 0,
    }


def _has_ui_tokens(content: str) -> bool:
    ui_tokens = ("Canvas", "GraphicRaycaster", "CanvasGroup", "m_OnClick")
    return any(token in content for token in ui_tokens)


def _prefab_wiring(project_path: Path, path: Path, content: str) -> dict:
    return {
        "path": relative_path(project_path, path),
        "button_like_count": content.count("m_OnClick"),
        "graphic_raycaster_count": content.count("GraphicRaycaster"),
        "canvas_group_count": content.count("CanvasGroup"),
        "has_missing_script": bool(has_missing_script(content)),
    }


def _add_ui_counts(totals: dict[str, int], content: str) -> None:
    totals["button_like_count"] += content.count("m_OnClick")
    totals["event_system_count"] += content.count("EventSystem")
    totals["graphic_raycaster_count"] += content.count("GraphicRaycaster")
    totals["canvas_group_count"] += content.count("CanvasGroup")
    if has_missing_script(content):
        totals["missing_script_count"] += 1


def _ui_hierarchy_warnings(totals: dict[str, int]) -> list[str]:
    warnings = []
    if totals["button_like_count"] > 0 and totals["event_system_count"] == 0:
        warnings.append("missing_event_system")
    if totals["button_like_count"] > 0 and totals["graphic_raycaster_count"] == 0:
        warnings.append("missing_graphic_raycaster")
    return warnings
