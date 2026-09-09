from pathlib import Path

import pytest

import kunity_yamae.project_files as inventory_module
from kunity_yamae.mobile_knowledge import retrieve_mobile_knowledge
from kunity_yamae.mobile_routing import route_mobile_task
from kunity_yamae.project_files import ProjectFileInventory


def test_inventory_prunes_before_descent_and_keeps_package_source(tmp_path, monkeypatch):
    for name in ("Assets/A.cs", "Packages/com.vendor.b/B.cs", "Library/deep/Skip.cs",
                 "Temp/deep/Skip.cs", ".git/objects/Skip.cs"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// fixture", encoding="utf-8")
    visited = []
    original = inventory_module.os.walk

    def tracked_walk(*args, **kwargs):
        for entry in original(*args, **kwargs):
            visited.append(Path(entry[0]).relative_to(tmp_path).as_posix())
            yield entry

    monkeypatch.setattr(inventory_module.os, "walk", tracked_walk)
    result = ProjectFileInventory.collect(tmp_path)
    assert result.relative_paths(result.scripts) == ["Assets/A.cs", "Packages/com.vendor.b/B.cs"]
    assert not any(part in name for name in visited for part in ("Library", "Temp", ".git"))


def test_inventory_skips_symlink_files_and_directories(tmp_path):
    (tmp_path / "Assets").mkdir()
    (tmp_path / "Assets/A.cs").write_text("// real", encoding="utf-8")
    (tmp_path / "Assets/Loop").symlink_to(tmp_path, target_is_directory=True)
    (tmp_path / "Assets/Alias.cs").symlink_to(tmp_path / "Assets/A.cs")
    result = ProjectFileInventory.collect(tmp_path)
    assert result.relative_paths(result.scripts) == ["Assets/A.cs"]


def test_lexical_matches_do_not_turn_jump_into_ump():
    assert route_mobile_task("Fix jump height", risk_score=10).role == "worker"
    assert retrieve_mobile_knowledge("Fix jump height") == []
    assert retrieve_mobile_knowledge("Fix FirebaseAuth login")[0]["id"] == "firebase-auth"


@pytest.mark.parametrize("value", [True, -1, "4", 0, 21])
def test_knowledge_budget_validates_integer(value):
    with pytest.raises(ValueError):
        retrieve_mobile_knowledge("IAP", top_k=value)
