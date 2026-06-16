from pathlib import Path
from typing import Any, Final

from .project_files import ProjectFileInventory

RUNTIME_TASK_TOKENS: Final[tuple[str, ...]] = (
    "visual",
    "runtime asset",
    "asset",
    "spawn",
    "instantiate",
    "resources.load",
    "resources",
    "recursion",
    "recursive",
    "clone",
    "collider",
)


DEFAULT_PREFAB_CANDIDATE_CAP: Final = 40
DEFAULT_RUNTIME_SCRIPT_CAP: Final = 25


def detect_runtime_asset_signals(
    project_path: Path,
    *,
    inventory: ProjectFileInventory | None = None,
    prefab_candidate_cap: int = DEFAULT_PREFAB_CANDIDATE_CAP,
) -> dict[str, Any]:
    project_inventory = inventory or ProjectFileInventory.collect(project_path)
    prefab_candidates: list[dict[str, str]] = []
    resource_prefab_count = 0
    package_prefab_count = 0
    for prefab in _ordered_prefabs(project_inventory):
        relative = project_inventory.relative_path(prefab)
        source = "resources_prefab" if _is_under_resources(prefab) else "prefab"
        if relative.startswith("Packages/"):
            package_prefab_count += 1
        if source == "resources_prefab":
            resource_prefab_count += 1
        prefab_candidates.append({"path": relative, "source": source})
    return {
        "summary": {
            "prefab_count": len(prefab_candidates),
            "resources_prefab_count": resource_prefab_count,
            "package_prefab_count": package_prefab_count,
        },
        "prefab_candidates": prefab_candidates[: max(prefab_candidate_cap, 0)],
        "category_counts": {},
        "warnings": [
            "File names are not semantic proof; treat candidates as leads until project "
            "rules or Unity evidence confirm intent."
        ],
        "recommendation": (
            "Use project configuration or Unity evidence before assigning runtime asset meaning."
        ),
    }


def runtime_safety_hints(
    task: str,
    project_path: Path,
    *,
    inventory: ProjectFileInventory | None = None,
    script_cap: int = DEFAULT_RUNTIME_SCRIPT_CAP,
) -> dict[str, Any]:
    task_lower = task.lower()
    if not any(token in task_lower for token in RUNTIME_TASK_TOKENS):
        return {}

    checks = {
        "cap_runtime_spawn_counts",
        "guard_recursive_runtime_events",
        "verify_resource_load_keys",
        "verify_runtime_asset_lifetime",
    }
    project_inventory = inventory or ProjectFileInventory.collect(project_path)
    scripts = _find_runtime_sensitive_scripts(project_inventory, max(script_cap, 0))
    return {
        "checks": sorted(checks),
        "scripts": scripts,
        "notes": [
            "Runtime-spawned assets should have explicit lifetime or pooling.",
            "Recursive runtime events should be guarded by project-specific ownership rules.",
            "Generated primitives should remove colliders unless collision is intended.",
            "Resources.Load paths should be covered by scan/context evidence or runtime fallback.",
        ],
    }


def _find_runtime_sensitive_scripts(
    inventory: ProjectFileInventory,
    script_cap: int,
) -> list[str]:
    scripts: list[str] = []
    if script_cap <= 0:
        return scripts
    needles = (
        "Resources.Load",
        "Instantiate(",
        "GameObject.CreatePrimitive",
        "Destroy(",
        "Collider",
    )
    for script in inventory.scripts:
        try:
            content = script.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(needle in content for needle in needles):
            scripts.append(inventory.relative_path(script))
        if len(scripts) >= script_cap:
            break
    return scripts


def _ordered_prefabs(inventory: ProjectFileInventory) -> tuple[Path, ...]:
    return tuple(
        sorted(
            inventory.prefabs,
            key=lambda path: (
                not inventory.relative_path(path).startswith("Packages/"),
                inventory.relative_path(path),
            ),
        )
    )


def _is_under_resources(path: Path) -> bool:
    return "Resources" in path.parts
