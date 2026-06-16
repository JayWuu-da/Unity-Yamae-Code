import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path


def _write_lines(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, str | Mapping[str, str]]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_git(project_path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=project_path, check=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--git-init", action="store_true")
    args = parser.parse_args()

    target = Path(args.out)
    match args.kind:
        case "minimal":
            create_minimal_project(target)
        case "ui-graphics-architecture":
            create_ui_graphics_architecture_project(target)
        case "ui-no-eventsystem":
            create_ui_graphics_architecture_project(target, include_event_system=False)
        case "graphics-mismatch":
            create_ui_graphics_architecture_project(target, graphics_mismatch=True)
        case "graphics-platforms":
            create_ui_graphics_architecture_project(target)
        case "ambiguous-architecture":
            create_ui_graphics_architecture_project(target, ambiguous_architecture=True)
        case "serialized-rename-diff":
            create_ui_graphics_architecture_project(target)
        case "package-first":
            create_package_first_project(target)
        case unknown:
            print(f"unknown fixture kind: {unknown}", file=sys.stderr)
            return 2

    if args.git_init:
        initialize_git_fixture(
            target,
            user_email="fixture@example.com",
            user_name="Fixture",
            commit_message="test fixture",
        )

    print(f"FIXTURE_OK {target}")
    return 0


def create_minimal_project(project_path: Path) -> None:
    settings_root = project_path / "ProjectSettings"
    settings_root.mkdir(parents=True, exist_ok=True)
    _write_lines(settings_root / "ProjectVersion.txt", "m_EditorVersion: 6000.4.0f1")
    (project_path / "Packages").mkdir(parents=True, exist_ok=True)
    _write_json(project_path / "Packages" / "manifest.json", {"dependencies": {}})
    (project_path / "Assets").mkdir(parents=True, exist_ok=True)


def create_package_first_project(project_path: Path) -> None:
    create_minimal_project(project_path)
    package_root = project_path / "Packages" / "com.example.neutral"
    runtime_root = package_root / "Runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    _write_json(
        package_root / "package.json",
        {
            "name": "com.example.neutral",
            "version": "0.1.0",
            "displayName": "Neutral Runtime",
        },
    )
    _write_json(runtime_root / "NeutralRuntime.asmdef", {"name": "NeutralRuntime"})
    _write_lines(
        runtime_root / "NeutralRuntime.cs",
        "using UnityEngine;",
        "public static class NeutralRuntime",
        "{",
        "    public const string Label = \"neutral data\";",
        "}",
    )
    _write_lines(
        runtime_root / "NeutralComponent.cs",
        "using UnityEngine;",
        "public sealed class NeutralComponent : MonoBehaviour",
        "{",
        "    [SerializeField] private string neutralData;",
        "}",
    )
    _write_lines(runtime_root / "NeutralView.uxml", '<UXML><Label text="neutral data" /></UXML>')
    package_cache = project_path / "Library" / "PackageCache" / "com.example.neutral"
    (package_cache / "Runtime").mkdir(parents=True, exist_ok=True)
    _write_lines(
        package_cache / "Runtime" / "CachedGenerated.cs",
        "public static class CachedGenerated {}",
    )


def create_git_project_with_player_stats(project_path: Path) -> None:
    create_minimal_project(project_path)
    script = project_path / "Assets" / "PlayerStats.cs"
    _write_lines(
        script,
        "using UnityEngine;",
        "public sealed class PlayerStats : MonoBehaviour",
        "{",
        "    [SerializeField] private int hitpoints;",
        "}",
    )
    initialize_git_fixture(
        project_path,
        user_email="test@example.com",
        user_name="Test",
        commit_message="baseline",
    )


def initialize_git_fixture(
    project_path: Path,
    *,
    user_email: str,
    user_name: str,
    commit_message: str,
) -> None:
    _run_git(project_path, "init")
    _run_git(project_path, "config", "user.email", user_email)
    _run_git(project_path, "config", "user.name", user_name)
    _run_git(project_path, "add", ".")
    _run_git(project_path, "commit", "-m", commit_message)


def create_ui_graphics_architecture_project(
    project_path: Path,
    *,
    include_event_system: bool = True,
    graphics_mismatch: bool = False,
    ambiguous_architecture: bool = False,
    include_importer_variety: bool = False,
) -> None:
    create_minimal_project(project_path)
    (project_path / "ProjectSettings" / "ProjectSettings.asset").write_text(
        "activeInputHandler: 2\n",
        encoding="utf-8",
    )
    _write_json(
        project_path / "Packages" / "manifest.json",
        {
            "dependencies": {
                "com.unity.ugui": "2.0.0",
                "com.unity.inputsystem": "1.8.2",
            }
        },
    )
    _write_ui_assets(project_path, include_event_system)
    _write_graphics_assets(project_path, graphics_mismatch, include_importer_variety)
    _write_architecture_scripts(project_path, ambiguous_architecture)


def _write_ui_assets(project_path: Path, include_event_system: bool) -> None:
    (project_path / "Assets" / "Scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "Assets" / "UI").mkdir(parents=True, exist_ok=True)
    scene_tokens = [
        "GameObject:",
        "  m_Name: MainCanvas",
        "Canvas:",
        "GraphicRaycaster:",
        "PrefabInstance:",
        "  m_SourcePrefab: {fileID: 100100000, guid: samplepanel, type: 3}",
    ]
    if include_event_system:
        scene_tokens.append("EventSystem:")
    _write_lines(project_path / "Assets" / "Scenes" / "Main.unity", *scene_tokens)
    _write_lines(
        project_path / "Assets" / "UI" / "SamplePanel.prefab",
        "GameObject:",
        "  m_Name: SamplePanel",
        "Canvas:",
        "GraphicRaycaster:",
        "CanvasGroup:",
        "m_RaycastTarget: 1",
        "m_OnClick:",
        "MonoBehaviour:",
        "  m_Script: {fileID: 11500000, guid: 00000000000000000000000000000000, type: 3}",
    )


def _write_graphics_assets(
    project_path: Path,
    graphics_mismatch: bool,
    include_importer_variety: bool,
) -> None:
    (project_path / "Assets" / "Textures").mkdir(parents=True, exist_ok=True)
    standalone_format = "RGBA32" if graphics_mismatch else "ASTC_6x6"
    (project_path / "Assets" / "Textures" / "SampleTexture.png").write_bytes(b"png")
    texture_lines = [
        "TextureImporter:",
        "  spriteMode: 1",
        "  spritePixelsToUnits: 100",
        "  mipmapEnabled: 1",
        "  isReadable: 0",
        "  maxTextureSize: 4096",
        "  platformSettings:",
    ]
    for build_target, max_size, compression, texture_format, quality, crunched in (
        ("Android", "2048", "Compressed", "ASTC_6x6", "50", "1"),
        ("iPhone", "2048", "Compressed", "ASTC_6x6", "50", "1"),
        ("Standalone", "4096", "Uncompressed", standalone_format, "100", "0"),
    ):
        texture_lines.extend(
            [
                f"  - buildTarget: {build_target}",
                f"    maxTextureSize: {max_size}",
                f"    textureCompression: {compression}",
                f"    format: {texture_format}",
                f"    compressionQuality: {quality}",
                f"    crunchedCompression: {crunched}",
            ]
        )
    _write_lines(
        project_path / "Assets" / "Textures" / "SampleTexture.png.meta",
        *texture_lines,
    )
    if not include_importer_variety:
        return
    (project_path / "Assets" / "Audio").mkdir(parents=True, exist_ok=True)
    (project_path / "Assets" / "Models").mkdir(parents=True, exist_ok=True)
    (project_path / "Assets" / "Audio" / "Click.wav").write_bytes(b"wav")
    _write_lines(
        project_path / "Assets" / "Audio" / "Click.wav.meta",
        "AudioImporter:",
        "  loadType: CompressedInMemory",
        "  compressionFormat: Vorbis",
        "  quality: 0.7",
        "  preloadAudioData: 1",
    )
    (project_path / "Assets" / "Models" / "SampleModel.fbx").write_bytes(b"fbx")
    _write_lines(
        project_path / "Assets" / "Models" / "SampleModel.fbx.meta",
        "ModelImporter:",
        "  meshCompression: Medium",
        "  isReadable: 0",
        "  optimizeMeshPolygons: 1",
        "  importBlendShapes: 0",
    )


def _write_architecture_scripts(project_path: Path, ambiguous_architecture: bool) -> None:
    (project_path / "Assets" / "Scripts").mkdir(parents=True, exist_ok=True)
    presenter_name = "SamplePresenter" if not ambiguous_architecture else "SampleThing"
    _write_lines(
        project_path / "Assets" / "Scripts" / f"{presenter_name}.cs",
        "using UnityEngine;",
        f"public sealed class {presenter_name} : MonoBehaviour",
        "{",
        "    [SerializeField] private GameObject view;",
        "}",
    )
    _write_lines(
        project_path / "Assets" / "Scripts" / "FlowController.cs",
        "using UnityEngine;",
        "public sealed class FlowController : MonoBehaviour {}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
