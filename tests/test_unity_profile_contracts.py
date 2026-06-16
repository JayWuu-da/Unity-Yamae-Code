from pathlib import Path

from kunity_yamae.unity_profile_graphics import (
    detect_graphics_defaults,
    mobile_pc_mismatch,
    parse_texture_import_settings,
)


def test_texture_import_parser_returns_typed_contract(tmp_path: Path) -> None:
    from kunity_yamae.unity_profile_types import TextureImportSetting

    content = (
        "TextureImporter:\n"
        "  platformSettings:\n"
        "  - buildTarget: Standalone\n"
        "    maxTextureSize: 4096\n"
        "    format: DXT5\n"
        "  - buildTarget: Android\n"
        "    maxTextureSize: 1024\n"
        "    format: ETC2\n"
    )
    path = tmp_path / "Assets" / "Textures" / "SampleTexture.png.meta"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")

    setting: TextureImportSetting = parse_texture_import_settings(tmp_path, path, content)

    assert setting["path"] == "Assets/Textures/SampleTexture.png.meta"
    assert setting["platforms"]["Standalone"].get("max_texture_size") == 4096


def test_mobile_pc_mismatch_returns_typed_contract() -> None:
    from kunity_yamae.unity_profile_types import MobilePcMismatch, TextureImportSetting

    setting: TextureImportSetting = {
        "path": "Assets/SampleTexture.png.meta",
        "platforms": {
            "Standalone": {"format": "DXT5"},
            "Android": {"format": "ETC2"},
        },
    }

    mismatch: MobilePcMismatch | None = mobile_pc_mismatch(setting)

    assert mismatch == {
        "path": "Assets/SampleTexture.png.meta",
        "reason": "mobile_pc_format_mismatch",
        "mobile_formats": ["ETC2"],
        "standalone_format": "DXT5",
    }


def test_graphics_defaults_returns_named_contract(tmp_path: Path) -> None:
    from kunity_yamae.unity_profile_types import GraphicsDefaults

    graphics: GraphicsDefaults = detect_graphics_defaults(tmp_path)

    assert graphics["texture_meta_count"] == 0
    assert graphics["platform_overrides"] == {}
    assert graphics["texture_import_settings"] == []
