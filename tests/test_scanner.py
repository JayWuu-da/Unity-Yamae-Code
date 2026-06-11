"""Tests for Unity project scanner."""

import json
import tempfile
from pathlib import Path

import pytest

from kunity_yamae import scanner as scanner_module
from kunity_yamae.profile_cache import load_cached_profile
from kunity_yamae.scanner import UnityProjectScanner


def make_config():
    return {
        "protected_files": {
            "block_direct_write": ["Assets/**/*.meta"],
            "escalate_direct_write": ["Assets/**/*.asmdef"],
            "never_touch": ["Library/**"],
        }
    }


def test_scan_non_unity_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        scanner = UnityProjectScanner(project_path, make_config())
        profile = scanner.scan()
        assert profile["unity_version"] == "unknown"
        assert profile["packages"] == {}


def test_scan_unity_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "ProjectSettings").mkdir()
        (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.4.0f1\nm_EditorVersionWithRevision: 6000.4.0f1 (abc123)"
        )
        (project_path / "Packages").mkdir()
        (project_path / "Packages" / "manifest.json").write_text(
            json.dumps({"dependencies": {"com.unity.test-framework": "1.1.33"}})
        )
        scanner = UnityProjectScanner(project_path, make_config())
        profile = scanner.scan()
        assert profile["unity_version"] == "6000.4.0f1"
        assert "com.unity.test-framework" in profile["packages"]


def test_scan_detects_asmdef():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "ProjectSettings").mkdir()
        (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.0.0f1"
        )
        asm_dir = project_path / "Assets" / "Game"
        asm_dir.mkdir(parents=True)
        (asm_dir / "Game.asmdef").write_text(
            json.dumps(
                {
                    "name": "Game.Runtime",
                    "references": [],
                    "includePlatforms": [],
                    "excludePlatforms": [],
                }
            )
        )
        scanner = UnityProjectScanner(project_path, make_config())
        profile = scanner.scan(deep=True)
        assert len(profile["assemblies"]) == 1
        assert profile["assemblies"][0]["name"] == "Game.Runtime"


def test_load_cached_profile_uses_fallback_when_primary_cache_is_partial(tmp_path: Path) -> None:
    cache_dir = tmp_path / ".unity-harness" / "cache"
    cache_dir.mkdir(parents=True)
    fallback_dir = tmp_path / ".unity-harness"
    primary = cache_dir / "project-profile.json"
    fallback = fallback_dir / "project-profile.json"
    primary.write_text("", encoding="utf-8")
    fallback.write_text(json.dumps({"schema": "fallback", "packages": {}}), encoding="utf-8")

    profile = load_cached_profile(tmp_path)

    assert profile["schema"] == "fallback"


def test_scan_keeps_existing_cache_when_cache_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scanner = UnityProjectScanner(tmp_path, make_config())
    scanner.scan()
    cache_path = tmp_path / ".unity-harness" / "cache" / "project-profile.json"
    original_profile = json.loads(cache_path.read_text(encoding="utf-8"))

    def fail_dump(*args, **kwargs):
        raise OSError("simulated partial write")

    monkeypatch.setattr(scanner_module.json, "dump", fail_dump)

    with pytest.raises(OSError, match="simulated partial write"):
        scanner.scan()

    preserved_profile = json.loads(cache_path.read_text(encoding="utf-8"))
    assert preserved_profile == original_profile


def test_scan_retries_transient_cache_replace_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scanner = UnityProjectScanner(tmp_path, make_config())
    original_replace = Path.replace
    attempts = {"count": 0}

    def flaky_replace(path: Path, target: Path) -> Path:
        if target.name == "project-profile.json" and attempts["count"] == 0:
            attempts["count"] += 1
            raise PermissionError("simulated Windows cache lock")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    scanner.scan()

    cache_path = tmp_path / ".unity-harness" / "cache" / "project-profile.json"
    assert attempts["count"] == 1
    assert json.loads(cache_path.read_text(encoding="utf-8"))["schema"] == (
        "unity-harness.project-profile.v1"
    )
