"""Bounded, explicit reads for worker handoffs; never a repository crawl."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_SUFFIXES = {".cs", ".asmdef", ".uxml", ".uss", ".shader"}
MAX_FILE_BYTES = 1_000_000


def project_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("use a project-relative POSIX path")
    if any(ord(char) < 32 for char in relative):
        raise ValueError("control characters are not permitted in paths")
    parts = PurePosixPath(relative).parts
    if (relative.startswith("/") or ".." in parts or ".git" in parts
            or PurePosixPath(relative).as_posix() != relative or not parts):
        raise ValueError("path escapes the project")
    base = root.resolve()
    path = base
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink reads are not permitted in worker packets")
    if not path.resolve().is_relative_to(base):
        raise ValueError("path escapes the project")
    return path


def read_bytes(root: Path, relative: str) -> bytes:
    with project_file(root, relative).open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("file exceeds the bounded read limit")
    return raw


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_slices(root: Path, slices: list[dict[str, Any]]) -> tuple[list[dict], dict[str, str]]:
    if not isinstance(slices, list) or len(slices) > 8:
        raise ValueError("slices must contain at most eight explicit ranges")
    snippets, hashes, loaded = [], {}, {}
    seen = set()
    for row in slices:
        if not isinstance(row, dict):
            raise ValueError("each slice must be an object")
        path, start, end = row.get("path"), row.get("start"), row.get("end")
        if not isinstance(path, str):
            raise ValueError("slice path is required")
        parts = PurePosixPath(path).parts
        if not parts or parts[0] not in {"Assets", "Packages"}:
            raise ValueError("source ranges must be in Assets or Packages")
        if PurePosixPath(path).suffix not in SOURCE_SUFFIXES:
            raise ValueError("only source ranges are allowed; do not send Unity YAML or secrets")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError("slice start/end must be positive inclusive line numbers")
        if end - start + 1 > 160:
            raise ValueError("a source range may contain at most 160 lines")
        if (path, start, end) in seen:
            continue
        seen.add((path, start, end))
        if path not in loaded:
            raw = read_bytes(root, path)
            loaded[path] = raw.decode("utf-8-sig").splitlines()
            hashes[path] = digest(raw)
        lines = loaded[path]
        if end > len(lines):
            raise ValueError("source range extends beyond EOF")
        snippets.append({"path": path, "start": start, "end": end,
                         "text": "\n".join(lines[start - 1:end])})
    return snippets, hashes


def project_versions(root: Path, package_ids: list[str]) -> tuple[dict, dict[str, str | None]]:
    """Keep manifest declarations separate from lock resolutions; never read auth configs."""
    hashes, documents = {}, {}
    for relative in ("ProjectSettings/ProjectVersion.txt", "Packages/manifest.json",
                     "Packages/packages-lock.json"):
        if not project_file(root, relative).is_file():
            hashes[relative] = None
            continue
        raw = read_bytes(root, relative)
        hashes[relative] = digest(raw)
        documents[relative] = raw.decode("utf-8-sig")
    match = re.search(r"^m_EditorVersion:\s*(\S+)",
                      documents.get("ProjectSettings/ProjectVersion.txt", ""), re.M)
    manifest = json.loads(documents.get("Packages/manifest.json", "{}"))
    lock = json.loads(documents.get("Packages/packages-lock.json", "{}"))
    if not isinstance(manifest, dict) or not isinstance(lock, dict):
        raise ValueError("package metadata must be a JSON object")
    declared, resolved = manifest.get("dependencies", {}), lock.get("dependencies", {})
    if not isinstance(declared, dict) or not isinstance(resolved, dict):
        raise ValueError("package dependencies must be an object")
    packages = {}
    for name in sorted(set(package_ids)):
        row = resolved.get(name, {})
        if not isinstance(row, dict):
            raise ValueError("lock entry must be an object")
        declaration = declared.get(name)
        version = row.get("version")
        # URLs can contain private credentials. Do not transmit git/file locators.
        safe_decl = declaration if _version(declaration) else None
        safe_version = version if _version(version) else None
        packages[name] = {"declared_version": safe_decl, "resolved_version": safe_version,
                          "resolution": "observed" if safe_version else "unknown"}
    return {"unity": match.group(1) if match else None, "packages": packages}, hashes


def _version(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"\d+\.\d+\.\d+[\w.+-]*", value) is not None


def focused_editor_report(root: Path, targets: list[str]) -> tuple[dict, dict[str, str]]:
    relative = ".unity-harness/reports/editor-inspection.json"
    raw = read_bytes(root, relative)
    report = json.loads(raw)
    if not isinstance(report, dict) or report.get("schema") != "unity-harness.editor-inspection.v1":
        raise ValueError("unsupported Editor inspection report")
    selected = {}
    for section, key in (("inspectorConnections", "listeners"), ("prefabOverrides", "instances"),
                         ("serializedReferences", "missingReferences"),
                         ("uiComponentStates", "components")):
        section_data = report.get(section, {})
        if not isinstance(section_data, dict) or not isinstance(section_data.get(key, []), list):
            raise ValueError("invalid Editor inspection section")
        rows = [row for row in section_data.get(key, []) if isinstance(row, dict) and
                (row.get("assetPath") in targets or row.get("sourcePrefabPath") in targets)]
        if len(rows) > 20:
            raise ValueError("Editor selection is too broad; obtain a narrower report")
        selected[section] = rows
    if not any(selected.values()):
        raise ValueError("Editor report has no facts for requested assets")
    if len(json.dumps(selected, ensure_ascii=False).encode("utf-8")) > 6000:
        raise ValueError("Editor selection exceeds the byte limit; obtain a narrower report")
    return {"source": relative, "facts": selected,
            "freshness": "unknown; re-resolve live before mutation",
            "complete_object_graph": False}, {relative: digest(raw)}
