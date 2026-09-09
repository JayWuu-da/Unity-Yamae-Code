import json

import pytest

from kunity_yamae.worker_packet import check_packet_freshness, prepare_worker_packet

from .test_worker_packet import object_request, prepare, put
from .test_worker_packet import project as project
from .test_worker_packet import request_data as request_data


def test_missing_metadata_replaced_with_symlink_invalidates_packet(project, request_data):
    packet = prepare(project, request_data)
    (project / "Packages/packages-lock.json").symlink_to(project / "Packages/manifest.json")
    assert "Packages/packages-lock.json" in check_packet_freshness(project, packet)


def test_local_operation_preserves_task_and_acceptance(project):
    data = object_request(project, "prefab_bind")
    data["acceptance"].append("Do not change unrelated bindings or UI layout.")
    packet = prepare_worker_packet(project, data)
    assert packet["status"] == "planned_local"
    assert packet["payload"]["task"] == data["task"]
    assert packet["payload"]["acceptance"] == data["acceptance"]


@pytest.mark.parametrize("old", [True, 123, {}, "", "a" * 1001])
def test_invalid_old_reference_refuses_local_plan(project, old):
    data = object_request(project, "prefab_bind")
    data["object_contract"]["expected_old_value"] = old
    assert prepare_worker_packet(project, data)["status"] == "needs_context"


def test_oversized_editor_facts_not_silently_truncated(project):
    data = object_request(project, "prefab_bind")
    relative = ".unity-harness/reports/editor-inspection.json"
    report = json.loads((project / relative).read_text())
    report["uiComponentStates"]["components"][0]["long_fact"] = "x" * 7000
    put(project, relative, json.dumps(report))
    packet = prepare_worker_packet(project, data)
    assert packet["status"] == "needs_context" and "payload" not in packet
