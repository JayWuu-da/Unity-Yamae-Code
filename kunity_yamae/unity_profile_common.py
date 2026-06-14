import re
from pathlib import Path

from .constants import GENERATED_FOLDERS


def iter_project_files(project_path: Path, pattern: str) -> list[Path]:
    paths = []
    for path in project_path.rglob(pattern):
        try:
            relative_parts = path.relative_to(project_path).parts
        except ValueError:
            continue
        if GENERATED_FOLDERS & set(relative_parts):
            continue
        paths.append(path)
    return paths


def relative_path(project_path: Path, path: Path) -> str:
    return str(path.relative_to(project_path)).replace("\\", "/")


def has_missing_script(content: str) -> bool:
    return bool(re.search(r"m_Script:\s*\{[^}]*guid:\s*0{32}", content))
