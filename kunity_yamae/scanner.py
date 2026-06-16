"""Unity project scanner - detects project structure and caches facts."""

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import GENERATED_FOLDERS
from .project_files import ProjectFileInventory
from .semantic_index import detect_runtime_asset_signals
from .unity_profile import collect_unity_facts


class UnityProjectScanner:
    def __init__(self, project_path: Path, config: dict[str, Any]):
        self.project_path = project_path
        self.config = config
        self.cache_dir = project_path / ".unity-harness" / "cache"

    def scan(self, deep: bool = False) -> dict[str, Any]:
        """Scan Unity project and return profile."""
        inventory = ProjectFileInventory.collect(self.project_path)
        packages = self._detect_packages()
        profile = {
            "schema": "unity-harness.project-profile.v1",
            "project_path": str(self.project_path),
            "unity_version": self._detect_unity_version(),
            "packages": packages,
            "assemblies": self._detect_assemblies(inventory),
            "tests": self._detect_tests(inventory, packages),
            "scenes": self._detect_scenes(inventory),
            "project_files": self._project_files(inventory),
            "protected_patterns": self._get_protected_patterns(),
            "serialization_sensitive": (
                self._detect_serialization_sensitive(inventory) if deep else []
            ),
            "generated_folders": sorted(GENERATED_FOLDERS),
            "last_scan_utc": datetime.now(timezone.utc).isoformat(),
        }
        profile.update(collect_unity_facts(self.project_path, packages))
        profile["runtime_asset_signals"] = detect_runtime_asset_signals(
            self.project_path,
            inventory=inventory,
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / "project-profile.json"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=self.cache_dir,
                encoding="utf-8",
            ) as f:
                tmp_path = Path(f.name)
                json.dump(profile, f, indent=2)
            self._replace_cache_file(tmp_path, cache_path)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()
        return profile

    def _replace_cache_file(self, tmp_path: Path, cache_path: Path) -> None:
        last_error = None
        for attempt in range(5):
            try:
                tmp_path.replace(cache_path)
                return
            except PermissionError as exc:
                last_error = exc
                if attempt == 4:
                    break
                time.sleep(0.05 * (attempt + 1))
        if last_error is not None:
            raise last_error

    def _detect_unity_version(self) -> str:
        version_file = self.project_path / "ProjectSettings" / "ProjectVersion.txt"
        if not version_file.exists():
            return "unknown"
        content = version_file.read_text(encoding="utf-8").strip()
        for line in content.splitlines():
            if line.startswith("m_EditorVersion:"):
                return line.split(":", 1)[1].strip()
        return "unknown"

    def _detect_packages(self) -> dict[str, Any]:
        manifest = self.project_path / "Packages" / "manifest.json"
        if not manifest.exists():
            return {}
        with open(manifest, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data.get("dependencies", {})

    @staticmethod
    def _project_files(inventory: ProjectFileInventory) -> dict[str, list[str]]:
        return {
            "asmdefs": inventory.relative_paths(inventory.asmdefs),
            "scripts": inventory.relative_paths(inventory.scripts),
            "scenes": inventory.relative_paths(inventory.scenes),
            "prefabs": inventory.relative_paths(inventory.prefabs),
            "resource_files": inventory.relative_paths(inventory.resource_files),
            "package_local_content": inventory.relative_paths(inventory.package_local_content),
        }

    def _detect_assemblies(self, inventory: ProjectFileInventory) -> list[dict[str, Any]]:
        assemblies = []
        for asmdef in inventory.asmdefs:
            try:
                with open(asmdef, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                rel_path = inventory.relative_path(asmdef)
                platform = "editor" if data.get("includePlatforms", []) == ["Editor"] else "runtime"
                assemblies.append(
                    {
                        "name": data.get("name", asmdef.stem),
                        "path": rel_path,
                        "platform": platform,
                        "references": data.get("references", []),
                        "include_platforms": data.get("includePlatforms", []),
                        "exclude_platforms": data.get("excludePlatforms", []),
                        "define_constraints": data.get("defineConstraints", []),
                        "auto_referenced": data.get("autoReferenced", True),
                        "allowUnsafeCode": data.get("allowUnsafeCode", False),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return assemblies

    def _detect_tests(
        self,
        inventory: ProjectFileInventory,
        packages: dict[str, Any],
    ) -> dict[str, Any]:
        test_asmdefs = []
        for asmdef in inventory.asmdefs:
            try:
                with open(asmdef, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                is_editor_only = data.get("includePlatforms") == ["Editor"]
                is_test_assembly = "test" in data.get("name", "").lower()
                if is_editor_only and is_test_assembly:
                    test_asmdefs.append(inventory.relative_path(asmdef))
            except (json.JSONDecodeError, OSError):
                continue
        has_test_framework = "com.unity.test-framework" in packages
        return {
            "editModeAvailable": len(test_asmdefs) > 0 or has_test_framework,
            "playModeAvailable": has_test_framework,
            "test_asmdefs": test_asmdefs,
        }

    def _detect_scenes(self, inventory: ProjectFileInventory) -> list[str]:
        scenes = []
        build_settings = self.project_path / "ProjectSettings" / "EditorBuildSettings.asset"
        if build_settings.exists():
            content = build_settings.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "path:" in line:
                    path = line.split("path:", 1)[1].strip().strip('"')
                    scenes.append(path)
        for unity_file in inventory.scenes:
            rel = inventory.relative_path(unity_file)
            if rel not in scenes:
                scenes.append(rel)
        return scenes

    def _get_protected_patterns(self) -> list[str]:
        protected = self.config.get("protected_files", {})
        patterns = []
        patterns.extend(protected.get("block_direct_write", []))
        patterns.extend(protected.get("escalate_direct_write", []))
        patterns.extend(protected.get("never_touch", []))
        return patterns

    def _detect_serialization_sensitive(
        self,
        inventory: ProjectFileInventory,
    ) -> list[dict[str, Any]]:
        import re

        results = []
        for cs_file in inventory.scripts:
            try:
                content = cs_file.read_text(encoding="utf-8")
                if "MonoBehaviour" in content or "ScriptableObject" in content:
                    fields = []
                    for line in content.splitlines():
                        line_stripped = line.strip()
                        if line_stripped.startswith("[") or line_stripped.startswith("//"):
                            continue
                        if (
                            "SerializeField" in line_stripped
                            or "SerializeReference" in line_stripped
                        ):
                            fields.append(line_stripped)
                        match = re.match(r"public\s+\w+\s+(\w+)\s*[;=]", line_stripped)
                        if match:
                            fields.append(match.group(1))
                    if fields:
                        script_type = (
                            "MonoBehaviour" if "MonoBehaviour" in content else "ScriptableObject"
                        )
                        results.append(
                            {
                                "file": inventory.relative_path(cs_file),
                                "type": script_type,
                                "serialized_fields": fields[:20],
                            }
                        )
            except OSError:
                continue
        return results[:50]

    def _is_in_generated_folder(self, path: Path) -> bool:
        parts = path.relative_to(self.project_path).parts
        return bool(GENERATED_FOLDERS & set(parts))

    def write_memory_files(self, profile: dict[str, Any]) -> None:
        """Write UNITY_AGENTS.md files near relevant code domains."""
        memories = self._generate_domain_memories(profile)
        for domain_path, content in memories.items():
            target = self.project_path / domain_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _generate_domain_memories(self, profile: dict[str, Any]) -> dict[str, str]:
        memories = {}
        root_content = [
            "# UNITY_AGENTS.md",
            "Scope: Project root",
            f"Unity version: {profile.get('unity_version', 'unknown')}",
            "",
            "## Stable facts",
        ]
        for pkg_name, pkg_ver in list(profile.get("packages", {}).items())[:10]:
            root_content.append(f"- Package: {pkg_name} ({pkg_ver})")
        if profile.get("assemblies"):
            root_content.append("")
            root_content.append("## Assembly graph")
            for asm in profile["assemblies"]:
                refs = ", ".join(asm.get("references", [])[:5])
                root_content.append(f"- {asm['name']} ({asm['platform']}) refs: [{refs}]")
        root_content.extend(
            [
                "",
                "## Protected patterns",
                "- Do not edit .meta, .unity, .prefab, .asset, .controller, .anim directly.",
                "- Do not edit Library/, Temp/, Obj/, Logs/, Builds/, UserSettings/.",
                "",
                "## Verification",
                "- Run compile/import when Unity is available.",
                "- Run EditMode tests for logic changes.",
                "- Report manual Inspector checks for asset changes.",
            ]
        )
        memories["AGENTS.md"] = "\n".join(root_content)
        return memories
