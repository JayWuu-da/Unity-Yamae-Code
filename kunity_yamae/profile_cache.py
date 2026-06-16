import json
from pathlib import Path
from typing import Any

from .project_files import ProjectFileInventory


def load_cached_profile(project_path: Path) -> dict[str, Any]:
    profile_path = project_path / ".unity-harness" / "cache" / "project-profile.json"
    fallback_path = project_path / ".unity-harness" / "project-profile.json"
    for path in (profile_path, fallback_path):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(loaded, dict):
                return loaded
    return {}


def cached_script_paths(profile: dict[str, Any]) -> list[str]:
    scripts: list[str] = []
    _extend_script_paths(scripts, profile.get("scripts"))
    for key in ("project_files", "project_file_inventory", "inventory"):
        value = profile.get(key)
        if isinstance(value, dict):
            _extend_script_paths(scripts, value.get("scripts"))
    architecture = profile.get("architecture_patterns")
    if isinstance(architecture, dict):
        for key in (
            "presenters",
            "views",
            "controllers",
            "managers",
            "services",
            "event_buses",
            "scriptable_objects",
        ):
            _extend_script_paths(scripts, architecture.get(key))
        signals = architecture.get("role_signals")
        if isinstance(signals, list):
            for signal in signals:
                if isinstance(signal, dict):
                    _extend_script_paths(scripts, [signal.get("path")])
    serialization_sensitive = profile.get("serialization_sensitive")
    if isinstance(serialization_sensitive, list):
        for entry in serialization_sensitive:
            if isinstance(entry, dict):
                _extend_script_paths(scripts, [entry.get("file")])
    return list(dict.fromkeys(scripts))


def cached_profile_inventory(project_path: Path, profile: dict[str, Any]) -> ProjectFileInventory:
    script_paths = tuple(
        path
        for relative_path in cached_script_paths(profile)
        if (path := project_path / relative_path).is_file()
    )
    return ProjectFileInventory(
        project_path=project_path,
        asmdefs=(),
        scripts=script_paths,
        scenes=(),
        prefabs=(),
        resource_files=(),
        package_local_content=(),
    )


def _extend_script_paths(scripts: list[str], raw_paths: Any) -> None:
    if not isinstance(raw_paths, list):
        return
    for raw_path in raw_paths:
        if not isinstance(raw_path, str):
            continue
        path = raw_path.replace("\\", "/")
        if path.endswith(".cs"):
            scripts.append(path)
