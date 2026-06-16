from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

PROJECT_ASSUMPTION_SCOPES: Final[tuple[str, ...]] = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "README_KO.md",
    ".agents",
    ".claude",
    "config",
    "docs",
    "kunity_yamae",
    "skills",
    "tests",
)
PROJECT_ASSUMPTION_TERMS: Final[tuple[str, ...]] = (
    "Assets" + "/Resources/" + "Ta" + "ble" + "Datas",
    "Sh" + "op" + ".json",
    "Ta" + "bleDatas",
    "Sh" + "op",
    "Pass" + "Product",
    "Reward" + ".json",
    "Localize" + "Text" + ".json",
    "PRODUCT" + "_GROUP_ID",
    "sku" + "-pass",
    "text" + "_pass_name",
    "Localize" + "Text",
    "Game" + "Controller",
    "Main" + "Menu",
    "Hero" + ".png",
    "storm" + "fall",
    "fire" + "ball",
    "Reward" + "Table",
    "reward" + " table",
    "Reward" + " links",
    "Localization" + " links",
    "payload" + "-shape",
    "VFX" + "_PATTERNS",
    "semantic " + "VFX buckets",
)


def collect_project_assumption_hygiene(package_root: Path) -> dict[str, bool | list[str] | str]:
    try:
        paths = git_visible_files(package_root, PROJECT_ASSUMPTION_SCOPES)
    except FileNotFoundError:
        return git_visible_unavailable("git unavailable")
    except subprocess.CalledProcessError:
        return git_visible_unavailable("git ls-files failed")
    matches = find_project_assumption_matches(
        package_root,
        paths=paths,
        terms=PROJECT_ASSUMPTION_TERMS,
    )
    return {"passed": not matches, "matches": matches}


def git_visible_unavailable(reason: str) -> dict[str, bool | list[str] | str]:
    return {"passed": False, "matches": [], "available": False, "failure": reason}


def find_project_assumption_matches(
    package_root: Path,
    *,
    paths: list[Path],
    terms: list[str] | tuple[str, ...],
) -> list[str]:
    matches: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(package_root).as_posix()
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_number, line in enumerate(lines, 1):
            if found := first_found_term(line, terms):
                matches.append(f"{relative}:{line_number}:{found}")
    return matches


def first_found_term(line: str, terms: list[str] | tuple[str, ...]) -> str | None:
    for term in terms:
        if term in line:
            return term
    return None


def git_visible_files(package_root: Path, scopes: tuple[str, ...]) -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *scopes],
        cwd=package_root,
        text=True,
    )
    return [package_root / line for line in output.splitlines() if line]
