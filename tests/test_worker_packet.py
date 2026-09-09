import json
from copy import deepcopy
from pathlib import Path

import pytest
from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.tool_catalog import build_default_tool_registry
from kunity_yamae.worker_context import project_file, read_slices
from kunity_yamae.worker_packet import (
    check_packet_freshness,
    prepare_worker_packet,
    render_worker_prompt,
)


def put(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    put(tmp_path, "ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 6000.3.8f1\n")
    put(tmp_path, "Packages/manifest.json", '{"dependencies":{}}')
    put(tmp_path, "Assets/View.cs", "\n".join(f"// line {i}" for i in range(1, 101)))
    put(tmp_path, "Assets/Other.cs", "UNRELATED_SOURCE_DO_NOT_INCLUDE")
    return tmp_path


@pytest.fixture
def request_data():
    return {"kind": "code_patch", "task": "Fix the visible text typo",
            "write_paths": ["Assets/View.cs"],
            "acceptance": ["Only the selected text changes; compile succeeds."],
            "slices": [{"path": "Assets/View.cs", "start": 76, "end": 84}]}


def prepare(project, data, config=None):
    packet = prepare_worker_packet(project, data, config)
    assert packet["status"] == "prepared", packet
    return packet


def test_exact_source_and_single_prompt(project, request_data):
    packet = prepare(project, request_data)
    prompt = render_worker_prompt(packet)
    assert "// line 80" in prompt and "// line 10" not in prompt
    assert "UNRELATED_SOURCE" not in prompt
    assert prompt.count("TASK_DATA") == 1
    assert packet["budget"]["prompt_bytes"] == len(prompt.encode("utf-8"))
    assert packet["budget"]["token_count"] is None
    assert not any(packet[x] for x in ("model_called", "applied", "unity_verified"))
    assert not list(project.glob(".unity-harness/**/*"))


def test_critical_data_not_silently_truncated(project, request_data):
    packet = prepare_worker_packet(project, request_data,
                                   {"efficiency": {"max_prompt_bytes": 1024}})
    assert packet["status"] == "needs_context"
    assert packet["budget"]["truncated"] is False
    assert "payload" not in packet and "prefix" not in packet
    with pytest.raises(ValueError):
        render_worker_prompt(packet)


def test_duplicate_ranges_deduplicated(project, request_data):
    request_data["slices"] *= 2
    packet = prepare(project, request_data)
    assert len(packet["payload"]["sources"]) == 1


def test_prefix_stable_but_task_is_variable(project, request_data):
    first = prepare(project, request_data)
    request_data["task"] = "Fix the other visible text typo"
    second = prepare(project, request_data)
    assert first["prefix_sha256"] == second["prefix_sha256"]
    assert render_worker_prompt(first) != render_worker_prompt(second)


@pytest.mark.parametrize("field", ["acceptance", "write_paths", "task", "kind"])
def test_required_contract_not_inferred(project, request_data, field):
    request_data.pop(field)
    with pytest.raises(ValueError):
        prepare_worker_packet(project, request_data)


def test_missing_target_source_refuses_guess(project, request_data):
    request_data["slices"] = []
    packet = prepare_worker_packet(project, request_data)
    assert packet["status"] == "needs_context" and "payload" not in packet


def test_missing_unity_version_refuses_guess(project, request_data):
    (project / "ProjectSettings/ProjectVersion.txt").unlink()
    assert prepare_worker_packet(project, request_data)["status"] == "needs_context"


def test_every_input_hash_and_creation_checked(project, request_data):
    packet = prepare(project, request_data)
    assert check_packet_freshness(project, packet) == []
    put(project, "Packages/packages-lock.json", '{"dependencies":{}}')
    assert check_packet_freshness(project, packet) == ["Packages/packages-lock.json"]
    put(project, "Assets/View.cs", "changed outside selected lines too")
    assert "Assets/View.cs" in check_packet_freshness(project, packet)


def test_git_package_locator_never_leaks_and_source_can_supply_evidence(project, request_data):
    name = "com.vendor.async"
    request_data["package_ids"] = [name]
    put(project, "Packages/manifest.json", json.dumps({"dependencies": {
        name: "https://secret:credential@example.invalid/sdk.git"}}))
    packet = prepare_worker_packet(project, request_data)
    assert packet["status"] == "needs_context"
    put(project, f"Packages/{name}/Awaiter.cs", "public struct Awaiter {}")
    request_data["slices"].append({"path": f"Packages/{name}/Awaiter.cs", "start": 1, "end": 1})
    prompt = render_worker_prompt(prepare(project, request_data))
    assert "credential@example" not in prompt and "secret:" not in prompt
    assert '"resolution":"unknown"' in prompt


def test_async_requires_explicit_lifetime(project, request_data):
    request_data["kind"] = "async_patch"
    assert prepare_worker_packet(project, request_data)["status"] == "needs_context"
    request_data["lifetime"] = "pool"
    packet = prepare(project, request_data)
    assert packet["payload"]["lifetime"] == "pool"


def test_money_scope_and_retry_escalate(project, request_data):
    request_data["task"] = "Fix IAP transaction logging"
    assert prepare_worker_packet(project, request_data)["route"]["role"] == "architect"
    request_data["task"] = "Fix text typo"
    for failed, role in ((1, "architect"), (2, "human")):
        request_data["failure_count"] = failed
        packet = prepare_worker_packet(project, request_data)
        assert packet["status"] == "escalated" and packet["route"]["role"] == role
        assert "payload" not in packet


@pytest.mark.parametrize("path", ["../x.cs", "/tmp/x.cs", "Assets/../../x.cs",
                                  "Assets/x.cs:stream", "Assets/./x.cs", "Assets//x.cs",
                                  "Assets/.git/config", "Assets/\\x.cs", "."])
def test_noncanonical_and_escape_paths_refused(project, path):
    with pytest.raises(ValueError):
        project_file(project, path)


def test_symlink_and_eof_refused(project, request_data, tmp_path):
    (project / "Assets/Link.cs").symlink_to(project / "Assets/View.cs")
    with pytest.raises(ValueError):
        read_slices(project, [{"path": "Assets/Link.cs", "start": 1, "end": 1}])
    request_data["slices"][0]["end"] = 101
    assert prepare_worker_packet(project, request_data)["status"] == "needs_context"


def test_korean_budget_is_bytes_not_character_or_token_count(project, request_data):
    request_data["task"] = "선택한 문구의 오타 수정"
    packet = prepare(project, request_data)
    prompt = render_worker_prompt(packet)
    assert packet["budget"]["prompt_bytes"] > len(prompt)
    assert packet["budget"]["token_count_kind"] == "not_measured"


def object_request(project, kind):
    asset = "Assets/Hud.prefab"
    put(project, asset, "synthetic prefab fixture; not executable Unity YAML")
    put(project, asset + ".meta", "guid: 1234567890abcdef1234567890abcdef")
    report = {"schema": "unity-harness.editor-inspection.v1", "uiComponentStates": {
        "components": [{"assetPath": asset, "gameObjectPath": "Hud/Bar",
                        "componentType": "Slider"},
                       {"assetPath": "Assets/Unrelated.prefab", "componentType": "IGNORE_ME"}]}}
    put(project, ".unity-harness/reports/editor-inspection.json", json.dumps(report))
    return {"kind": kind, "task": "Connect the indicated HUD reference",
            "write_paths": [asset], "acceptance": ["Binding survives save and reload."],
            "object_contract": {"source_hierarchy": "Hud", "source_component": "HealthView",
                                "property_path": "slider", "target_hierarchy": "Hud/Bar",
                                "target_component": "Slider", "expected_old_value": None}}


def test_prefab_packet_is_proposal_not_editor_verification(project):
    data = object_request(project, "prefab_bind")
    packet = prepare_worker_packet(project, data)
    assert packet["status"] == "planned_local"
    assert packet["route"]["role"] == "local"
    assert "prefix" not in packet and packet["execution_ready"] is False
    prompt = json.dumps(packet)
    assert "IGNORE_ME" not in prompt
    assert packet["payload"]["editor_excerpt"]["complete_object_graph"] is False
    assert packet["unity_verified"] is False and packet["applied"] is False
    put(project, "Assets/Hud.prefab.meta", "guid: changed")
    assert "Assets/Hud.prefab.meta" in check_packet_freshness(project, packet)


def test_prefab_missing_report_or_contract_stops(project):
    data = object_request(project, "prefab_bind")
    data["object_contract"].pop("expected_old_value")
    assert prepare_worker_packet(project, data)["status"] == "needs_context"
    (project / ".unity-harness/reports/editor-inspection.json").unlink()
    assert prepare_worker_packet(project, data)["status"] == "needs_context"


def test_ui_requires_reusable_template_and_layout(project):
    data = object_request(project, "ui_create")
    data["task"] = "Create a small panel from the specified template"
    data["object_contract"] = {"ui_system": "ugui", "template_asset": "Assets/Panel.prefab",
                               "parent_hierarchy": "Hud", "layout_contract": "Stretch to parent",
                               "target_resolutions": "1080x1920 and 1440x2560"}
    assert prepare_worker_packet(project, data)["status"] == "needs_context"
    put(project, "Assets/Panel.prefab", "synthetic template")
    put(project, "Assets/Panel.prefab.meta", "guid: template")
    packet = prepare_worker_packet(project, data)
    assert packet["status"] == "planned_local"
    assert "Assets/Panel.prefab" in packet["payload"]["base_sha256"]
    assert packet["payload"]["operation"]["op"] == "instantiate_template"


def test_cli_and_registry_reach_same_preparation_path(project, request_data):
    request_path = project / "request.json"
    request_path.write_text(json.dumps(request_data), encoding="utf-8")
    runner = CliRunner()
    args = ["--project", str(project), "worker-pack", "--request-file", str(request_path)]
    result = runner.invoke(main, args + ["--json"])
    assert result.exit_code == 0, result.output
    packet = json.loads(result.output)
    assert packet["status"] == "prepared"
    direct = runner.invoke(main, args + ["--prompt-only"])
    assert direct.exit_code == 0 and direct.output.strip() == render_worker_prompt(packet)
    registry = build_default_tool_registry({}, project)
    tool = registry.call("harness.worker.prepare", deepcopy(request_data))
    assert tool["result"]["status"] == "prepared"
    bad = registry.call("harness.worker.prepare", {"kind": []})
    assert bad["status"] == "failed"
