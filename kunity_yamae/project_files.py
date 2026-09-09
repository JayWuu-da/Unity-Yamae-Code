from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .constants import GENERATED_FOLDERS

UNITY_CONTENT_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".anim",
        ".asmdef",
        ".asmref",
        ".asset",
        ".controller",
        ".cs",
        ".mat",
        ".overrideController",
        ".playable",
        ".prefab",
        ".shader",
        ".spriteatlas",
        ".unity",
        ".uss",
        ".uxml",
    }
)


@dataclass(frozen=True, slots=True)
class ProjectFileInventory:
    project_path: Path
    asmdefs: tuple[Path, ...]
    scripts: tuple[Path, ...]
    scenes: tuple[Path, ...]
    prefabs: tuple[Path, ...]
    resource_files: tuple[Path, ...]
    package_local_content: tuple[Path, ...]

    @classmethod
    def collect(cls, project_path: Path) -> ProjectFileInventory:
        files = sorted(
            _iter_project_files(project_path),
            key=lambda path: _relative_path(project_path, path),
        )
        return cls(
            project_path=project_path,
            asmdefs=tuple(path for path in files if path.suffix == ".asmdef"),
            scripts=tuple(path for path in files if path.suffix == ".cs"),
            scenes=tuple(path for path in files if path.suffix == ".unity"),
            prefabs=tuple(path for path in files if path.suffix == ".prefab"),
            resource_files=tuple(path for path in files if _is_resource_file(project_path, path)),
            package_local_content=tuple(
                path for path in files if _is_package_local_content(project_path, path)
            ),
        )

    def relative_path(self, path: Path) -> str:
        return _relative_path(self.project_path, path)

    def relative_paths(self, paths: tuple[Path, ...]) -> list[str]:
        return [self.relative_path(path) for path in paths]


def _iter_project_files(project_path: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    # Prune before descent: filtering rglob results still visits every Library entry.
    for root, directories, filenames in os.walk(project_path, followlinks=False):
        directories[:] = sorted(
            name for name in directories
            if name not in GENERATED_FOLDERS and not (Path(root) / name).is_symlink()
        )
        for name in sorted(filenames):
            path = Path(root) / name
            if not path.is_symlink() and path.is_file():
                files.append(path)
    return tuple(files)


def _relative_path(project_path: Path, path: Path) -> str:
    return path.relative_to(project_path).as_posix()


def _is_resource_file(project_path: Path, path: Path) -> bool:
    return "Resources" in path.relative_to(project_path).parts


def _is_package_local_content(project_path: Path, path: Path) -> bool:
    relative = path.relative_to(project_path)
    return (
        len(relative.parts) > 1
        and relative.parts[0] == "Packages"
        and path.suffix in UNITY_CONTENT_SUFFIXES
    )
