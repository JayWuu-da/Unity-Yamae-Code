from typing import TypedDict

ImporterValue = int | float | str


class TexturePlatformSetting(TypedDict, total=False):
    max_texture_size: ImporterValue
    texture_compression: ImporterValue
    compression_quality: ImporterValue
    crunched_compression: ImporterValue
    format: ImporterValue


class TextureImportSetting(TypedDict):
    path: str
    platforms: dict[str, TexturePlatformSetting]


class SpriteImportSetting(TypedDict, total=False):
    path: str
    sprite_mode: ImporterValue
    pixels_per_unit: ImporterValue
    mipmap_enabled: ImporterValue
    is_readable: ImporterValue


class AudioImportSetting(TypedDict, total=False):
    path: str
    load_type: ImporterValue
    compression_format: ImporterValue
    quality: ImporterValue
    preload_audio_data: ImporterValue


class ModelImportSetting(TypedDict, total=False):
    path: str
    mesh_compression: ImporterValue
    is_readable: ImporterValue
    optimize_mesh_polygons: ImporterValue
    import_blend_shapes: ImporterValue


class MobilePcMismatch(TypedDict):
    path: str
    reason: str
    mobile_formats: list[str]
    standalone_format: ImporterValue


class GraphicsDefaults(TypedDict):
    texture_meta_count: int
    platform_overrides: dict[str, int]
    large_textures: list[str]
    texture_import_settings: list[TextureImportSetting]
    sprite_import_settings: list[SpriteImportSetting]
    audio_import_settings: list[AudioImportSetting]
    model_import_settings: list[ModelImportSetting]
    mobile_pc_mismatches: list[MobilePcMismatch]
