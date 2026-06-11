import json
from pathlib import Path


def load_cached_profile(project_path: Path) -> dict:
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
