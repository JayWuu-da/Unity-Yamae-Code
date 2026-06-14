import re
from pathlib import Path

from .unity_profile_common import iter_project_files, relative_path
from .unity_profile_types import (
    AudioImportSetting,
    GraphicsDefaults,
    ImporterValue,
    MobilePcMismatch,
    ModelImportSetting,
    SpriteImportSetting,
    TextureImportSetting,
    TexturePlatformSetting,
)


def detect_graphics_defaults(project_path: Path) -> GraphicsDefaults:
    texture_meta_count = 0
    platform_overrides: dict[str, int] = {}
    large_textures: list[str] = []
    texture_import_settings: list[TextureImportSetting] = []
    sprite_import_settings: list[SpriteImportSetting] = []
    audio_import_settings: list[AudioImportSetting] = []
    model_import_settings: list[ModelImportSetting] = []
    mobile_pc_mismatches: list[MobilePcMismatch] = []
    for path in iter_project_files(project_path, "*.meta"):
        content = path.read_text(encoding="utf-8", errors="replace")
        if "TextureImporter:" in content:
            texture_meta_count += 1
            _count_platform_overrides(content, platform_overrides)
            _append_large_texture(project_path, path, content, large_textures)
            setting = parse_texture_import_settings(project_path, path, content)
            texture_import_settings.append(setting)
            sprite_setting = parse_sprite_import_settings(project_path, path, content)
            if sprite_setting:
                sprite_import_settings.append(sprite_setting)
            mismatch = mobile_pc_mismatch(setting)
            if mismatch:
                mobile_pc_mismatches.append(mismatch)
        if "AudioImporter:" in content:
            audio_import_settings.append(parse_audio_import_settings(project_path, path, content))
        if "ModelImporter:" in content:
            model_import_settings.append(parse_model_import_settings(project_path, path, content))
    return {
        "texture_meta_count": texture_meta_count,
        "platform_overrides": platform_overrides,
        "large_textures": large_textures[:25],
        "texture_import_settings": texture_import_settings[:25],
        "sprite_import_settings": sprite_import_settings[:25],
        "audio_import_settings": audio_import_settings[:25],
        "model_import_settings": model_import_settings[:25],
        "mobile_pc_mismatches": mobile_pc_mismatches[:25],
    }


def parse_texture_import_settings(
    project_path: Path,
    path: Path,
    content: str,
) -> TextureImportSetting:
    platforms: dict[str, TexturePlatformSetting] = {}
    current_target = ""
    for raw_line in content.splitlines():
        line = raw_line.strip()
        target_match = re.match(r"-?\s*buildTarget:\s*([A-Za-z0-9_]+)", line)
        if target_match:
            current_target = target_match.group(1)
            platforms[current_target] = {}
            continue
        if not current_target or ":" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split(":", 1)]
        platforms[current_target][texture_key(key)] = parse_texture_value(raw_value)
    return {
        "path": relative_path(project_path, path),
        "platforms": platforms,
    }


def parse_sprite_import_settings(
    project_path: Path,
    path: Path,
    content: str,
) -> SpriteImportSetting | None:
    values = parse_root_importer_values(
        content,
        {
            "spriteMode": "sprite_mode",
            "spritePixelsToUnits": "pixels_per_unit",
            "mipmapEnabled": "mipmap_enabled",
            "isReadable": "is_readable",
        },
    )
    sprite_mode = values.get("sprite_mode")
    if sprite_mode in {None, 0, "0"}:
        return None
    values["sprite_mode"] = sprite_mode_name(sprite_mode)
    return {
        "path": relative_path(project_path, path),
        **values,
    }


def parse_audio_import_settings(project_path: Path, path: Path, content: str) -> AudioImportSetting:
    return {
        "path": relative_path(project_path, path),
        **parse_root_importer_values(
            content,
            {
                "loadType": "load_type",
                "compressionFormat": "compression_format",
                "quality": "quality",
                "preloadAudioData": "preload_audio_data",
            },
        ),
    }


def parse_model_import_settings(project_path: Path, path: Path, content: str) -> ModelImportSetting:
    return {
        "path": relative_path(project_path, path),
        **parse_root_importer_values(
            content,
            {
                "meshCompression": "mesh_compression",
                "isReadable": "is_readable",
                "optimizeMeshPolygons": "optimize_mesh_polygons",
                "importBlendShapes": "import_blend_shapes",
            },
        ),
    }


def parse_root_importer_values(content: str, key_map: dict[str, str]) -> dict[str, ImporterValue]:
    values: dict[str, ImporterValue] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("- ") or ":" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split(":", 1)]
        if key in key_map:
            values[key_map[key]] = parse_texture_value(raw_value)
    return values


def texture_key(key: str) -> str:
    mapping = {
        "maxTextureSize": "max_texture_size",
        "textureCompression": "texture_compression",
        "compressionQuality": "compression_quality",
        "crunchedCompression": "crunched_compression",
    }
    return mapping.get(key, key)


def parse_texture_value(value: str) -> ImporterValue:
    if re.fullmatch(r"\d+\.\d+", value):
        return float(value)
    if re.fullmatch(r"\d+", value):
        return int(value)
    return value


def sprite_mode_name(value: int | str) -> str:
    mapping = {
        1: "Single",
        2: "Multiple",
        3: "Polygon",
        "1": "Single",
        "2": "Multiple",
        "3": "Polygon",
    }
    return mapping.get(value, str(value))


def mobile_pc_mismatch(setting: TextureImportSetting) -> MobilePcMismatch | None:
    platforms = setting.get("platforms", {})
    android = platforms.get("Android", {})
    iphone = platforms.get("iPhone", {})
    standalone = platforms.get("Standalone", {})
    mobile_formats = {android.get("format"), iphone.get("format")} - {None, ""}
    standalone_format = standalone.get("format")
    if standalone_format and mobile_formats and standalone_format not in mobile_formats:
        return {
            "path": setting["path"],
            "reason": "mobile_pc_format_mismatch",
            "mobile_formats": sorted(str(item) for item in mobile_formats),
            "standalone_format": standalone_format,
        }
    return None


def _count_platform_overrides(content: str, platform_overrides: dict[str, int]) -> None:
    for target in re.findall(r"buildTarget:\s*([A-Za-z0-9_]+)", content):
        platform_overrides[target] = platform_overrides.get(target, 0) + 1


def _append_large_texture(
    project_path: Path,
    path: Path,
    content: str,
    large_textures: list[str],
) -> None:
    size_match = re.search(r"maxTextureSize:\s*(\d+)", content)
    if size_match and int(size_match.group(1)) >= 4096:
        large_textures.append(relative_path(project_path, path))
