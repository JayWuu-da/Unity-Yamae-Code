"""Resources and Addressables guard - detects string-key asset path changes."""

import re
from pathlib import Path
from typing import Any

from kunity_yamae.constants import GENERATED_FOLDERS


class AddressablesGuard:
    def __init__(self, project_path: Path, config: dict[str, Any]):
        self.project_path = project_path
        self.config = config

    def check(self, changed_files: list[str], diff_content: str = "") -> list[dict[str, Any]]:
        """Check for Resources/Addressables string-key path changes."""
        issues = []

        if diff_content:
            issues.extend(self._check_diff_for_resources(diff_content))
            issues.extend(self._check_diff_for_addressables(diff_content))

        for f in changed_files:
            if self._is_resources_path(f):
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "warning",
                        "file": f,
                        "message": f"File under Resources folder: {f}. "
                        "Will be included in build and loaded by string key.",
                    }
                )

        return issues

    def _check_diff_for_resources(self, diff_content: str) -> list[dict[str, Any]]:
        issues = []
        pattern = re.compile(
            r'Resources\.Load(?:<[^>]+>)?\s*\(\s*@"?([^"]+)"?\s*\)',
            re.MULTILINE,
        )
        for match in pattern.finditer(diff_content):
            path = match.group(1)
            if not self._resources_key_exists(path):
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "warning",
                        "file": "",
                        "message": (
                            f"Resources.Load path '{path}' may not exist. "
                            "Verify asset is in a discovered Resources folder."
                        ),
                    }
                )
        return issues

    def _resources_key_exists(self, key: str) -> bool:
        normalized = key.replace("\\", "/").strip("/")
        if not normalized:
            return False
        parent = Path(normalized).parent
        stem = Path(normalized).name
        for root in self._resources_roots():
            search_root = root if str(parent) == "." else root / parent
            if search_root.exists() and any(search_root.glob(f"{stem}.*")):
                return True
        return False

    def _resources_roots(self) -> list[Path]:
        roots: list[Path] = []
        for path in self.project_path.rglob("Resources"):
            if not path.is_dir():
                continue
            try:
                relative_parts = path.relative_to(self.project_path).parts
            except ValueError:
                continue
            if GENERATED_FOLDERS & set(relative_parts):
                continue
            roots.append(path)
        return roots

    @staticmethod
    def _is_resources_path(path: str) -> bool:
        normalized = path.replace("\\", "/")
        return "/Resources/" in f"/{normalized}"

    def _check_diff_for_addressables(self, diff_content: str) -> list[dict[str, Any]]:
        issues = []
        key_pattern = re.compile(
            r'Addressables\.LoadAssetAsync(?:<[^>\n]+>)?\s*\(\s*@?"([^"\n]+)"',
            re.MULTILINE,
        )
        for match in key_pattern.finditer(diff_content):
            key = match.group(1)
            issues.append(
                {
                    "guard": "resources_addressables",
                    "severity": "info",
                    "file": "",
                    "message": (
                        f"Addressables key '{key}' referenced. "
                        "Verify it against discovered Addressables data."
                    ),
                }
            )

        key_list_pattern = re.compile(
            r'Addressables\.LoadAssetsAsync(?:<[^>\n]+>)?\s*\(\s*@?"([^"\n]+)"',
            re.MULTILINE,
        )
        for match in key_list_pattern.finditer(diff_content):
            key_or_label = match.group(1)
            issues.append(
                {
                    "guard": "resources_addressables",
                    "severity": "info",
                    "file": "",
                    "message": (
                        f"Addressables key/list '{key_or_label}' referenced. "
                        "Verify it against discovered Addressables data."
                    ),
                }
            )

        label_pattern = re.compile(
            r'Addressables\.LabelExists\s*\(\s*@?"([^"\n]+)"',
            re.MULTILINE,
        )
        for match in label_pattern.finditer(diff_content):
            label = match.group(1)
            issues.append(
                {
                    "guard": "resources_addressables",
                    "severity": "info",
                    "file": "",
                    "message": (
                        f"Addressables label '{label}' referenced. "
                        "Verify it against discovered Addressables data."
                    ),
                }
            )

        scene_pattern = re.compile(
            r'Addressables\.LoadSceneAsync\s*\(\s*@?"([^"\n]+)"',
            re.MULTILINE,
        )
        for match in scene_pattern.finditer(diff_content):
            scene_key = match.group(1)
            issues.append(
                {
                    "guard": "resources_addressables",
                    "severity": "info",
                    "file": "",
                    "message": (
                        f"Addressables scene key '{scene_key}' referenced. "
                        "Verify it against discovered Addressables data."
                    ),
                }
            )

        return issues

    def check_scene_name_change(self, diff_content: str) -> list[dict[str, Any]]:
        issues = []
        build_settings_pattern = re.compile(r"^[\+\-].*path:\s*(.+\.unity)", re.MULTILINE)
        for match in build_settings_pattern.finditer(diff_content):
            line = match.group(0)
            scene_path = match.group(1).strip().strip('"')
            if line.startswith("+"):
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "info",
                        "file": "ProjectSettings/EditorBuildSettings.asset",
                        "message": f"Scene '{scene_path}' added to build settings.",
                    }
                )
            elif line.startswith("-"):
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "warning",
                        "file": "ProjectSettings/EditorBuildSettings.asset",
                        "message": f"Scene '{scene_path}' removed from build settings.",
                    }
                )
        return issues
