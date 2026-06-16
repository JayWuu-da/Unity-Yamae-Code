from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_scan_reports_name_derived_architecture_signals_without_ownership_claim(
    tmp_path: Path,
) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    architecture = profile["architecture_patterns"]

    assert architecture["detected"] == []
    assert "Assets/Scripts/SamplePresenter.cs" in architecture["presenters"]
    assert "Assets/Scripts/FlowController.cs" in architecture["controllers"]
    assert {
        "path": "Assets/Scripts/SamplePresenter.cs",
        "role": "presenter",
        "source": "filename",
        "confidence": "low",
    } in architecture["role_signals"]
    assert {
        "path": "Assets/Scripts/FlowController.cs",
        "role": "controller",
        "source": "filename",
        "confidence": "low",
    } in architecture["role_signals"]
    assert architecture["confidence"] == "low"
    assert "Do not assume architecture ownership from names alone." in architecture["warnings"]


def test_scan_reports_low_confidence_for_ambiguous_architecture(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path, ambiguous_architecture=True)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    architecture = profile["architecture_patterns"]

    assert architecture["confidence"] in {"low", "medium"}
    assert "Do not assume architecture ownership from names alone." in architecture["warnings"]
