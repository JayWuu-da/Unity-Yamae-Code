import re
from collections.abc import Sequence
from typing import Final

WORD_CHARS: Final = "a-z0-9_"


def normalize_task_text(task: str) -> str:
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", task)
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
    spaced = re.sub(r"[_/\\-]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def has_task_keyword(task_text: str, keywords: Sequence[str]) -> bool:
    return any(
        re.search(
            rf"(?<![{WORD_CHARS}]){re.escape(normalize_task_text(keyword))}(?![{WORD_CHARS}])",
            task_text,
        )
        is not None
        for keyword in keywords
    )


def check_serialized_field_rename(task_text: str, triggers: list[str]) -> int:
    rename_patterns = [
        r"rename\s+[\w\s.]+\s+to\s+\w+",
        r"change\s+[\w\s.]+\s+field\s+\w+\s+to\s+\w+",
        r"field\s+\w+\s+rename",
        r"serialized\s+field\s+rename",
    ]
    for pattern in rename_patterns:
        if re.search(pattern, task_text):
            triggers.append("Serialized field/class rename (asmdef risk)")
            return 70
    return 0


def check_mono_behaviour_lifecycle(task_text: str, triggers: list[str]) -> int:
    lifecycle_methods = [
        "awake",
        "onenable",
        "on enable",
        "start",
        "update",
        "fixedupdate",
        "fixed update",
        "lateupdate",
        "late update",
        "ondisable",
        "on disable",
        "ondestroy",
        "on destroy",
        "onvalidate",
        "on validate",
    ]
    for method in lifecycle_methods:
        if has_task_keyword(task_text, [method]):
            triggers.append(f"MonoBehaviour lifecycle ({method.replace(' ', '')})")
            return 20
    if has_task_keyword(task_text, ["reset()", "monobehaviour reset", "mono behaviour reset"]):
        triggers.append("MonoBehaviour lifecycle (reset)")
        return 20

    lifecycle_behaviors = [
        "spawn",
        "spawning",
        "wait",
        "waiting",
        "coroutine",
        "invoke",
        "timer",
        "delay",
        "interval",
        "loop",
        "callback",
    ]
    for behavior in lifecycle_behaviors:
        if has_task_keyword(task_text, [behavior]):
            triggers.append(f"MonoBehaviour behavior ({behavior})")
            return 25
    return 0


def check_editor_runtime_boundary(task_text: str, triggers: list[str]) -> int:
    editor_keywords = [
        "editor script",
        "custom inspector",
        "editor window",
        "property drawer",
        "editor utility",
        "unityeditor",
        "unity editor",
    ]
    if has_task_keyword(task_text, editor_keywords):
        triggers.append("Editor/runtime boundary")
        return 25
    return 0


def check_resources_addressables(task_text: str, triggers: list[str]) -> int:
    if has_task_keyword(
        task_text,
        ["resources.load", "resources load", "addressable", "addressables"],
    ):
        triggers.append("Resources/Addressables path change")
        return 30
    return 0


def check_ui_interaction(task_text: str, triggers: list[str]) -> int:
    keywords = [
        "ui",
        "button",
        "buttons",
        "onclick",
        "on click",
        "canvas",
        "raycast",
        "eventsystem",
        "event system",
        "recttransform",
        "rect transform",
    ]
    if has_task_keyword(task_text, keywords):
        triggers.append("Unity UI interaction/hierarchy")
        return 25
    return 0


def check_execution_path(task_text: str, triggers: list[str]) -> int:
    keywords = [
        "route",
        "routing",
        "popup",
        "openpopup",
        "open popup",
        "createpopup",
        "create popup",
        "shortcut",
        "listener",
        "binding",
        "controller reset",
        "reset path",
        "tab",
        "lock condition",
    ]
    if has_task_keyword(task_text, keywords):
        triggers.append("Unity execution path tracing")
        return 20
    return 0


def check_data_contract(task_text: str, triggers: list[str]) -> int:
    keywords = [
        "table",
        "tables",
        "dto",
        "shape",
        "shapes",
        "response",
        "responses",
        "contract",
        "contracts",
        "server",
        "backend",
        "merge",
    ]
    if has_task_keyword(task_text, keywords):
        triggers.append("Unity data contract")
        return 30
    return 0


def check_graphics_platform(task_text: str, triggers: list[str]) -> int:
    keywords = [
        "texture",
        "compression",
        "astc",
        "etc2",
        "ios",
        "android",
        "pc",
        "shader",
        "mipmap",
    ]
    if has_task_keyword(task_text, keywords):
        triggers.append("Graphics/import platform settings")
        return 35
    return 0


def check_architecture_pattern(task_text: str, triggers: list[str]) -> int:
    keywords = ["mvp", "mvc", "presenter", "controller", "game manager", "eventbus", "service"]
    if has_task_keyword(task_text, keywords):
        triggers.append("Unity architecture pattern")
        return 20
    return 0


def check_asmdef_change(task_text: str, triggers: list[str]) -> int:
    if has_task_keyword(task_text, ["asmdef", "assembly definition"]):
        triggers.append("Assembly definition (asmdef) change")
        return 50
    return 0


def check_package_settings(task_text: str, triggers: list[str]) -> int:
    package_action = has_task_keyword(task_text, ["upgrade", "update", "add"])
    if has_task_keyword(task_text, ["package"]) and package_action:
        triggers.append("Package change")
        return 45
    if has_task_keyword(task_text, ["projectsettings", "project settings"]):
        triggers.append("ProjectSettings change")
        return 45
    return 0


def check_asset_move(task_text: str, triggers: list[str]) -> int:
    move_patterns = [
        r"move\s+\w+\s+(to|into)",
        r"relocate",
        r"reorganize.*folder",
        r"move.*prefab",
        r"move.*asset",
        r"move.*scene",
    ]
    for pattern in move_patterns:
        if re.search(pattern, task_text):
            triggers.append("Asset move/rename")
            return 50
    return 0


def check_yaml_edit(task_text: str, triggers: list[str]) -> int:
    yaml_patterns = [
        r"edit\s+.*\.(unity|prefab|asset|controller|anim)",
        r"yaml\s+(edit|write|modify)",
        r"direct.*yaml",
    ]
    for pattern in yaml_patterns:
        if re.search(pattern, task_text):
            triggers.append("Direct YAML edit")
            return 55
    return 0


def classify_action(task_text: str) -> int:
    if has_task_keyword(task_text, ["fix", "bug", "typo", "null check"]):
        return 5
    if has_task_keyword(task_text, ["add", "create", "implement", "write"]):
        return 15
    if has_task_keyword(task_text, ["refactor", "restructure", "reorganize"]):
        return 25
    return 10


def classify_diff_risk(diff: str, triggers: list[str]) -> int:
    risk = 0
    if ".meta" in diff:
        triggers.append("Diff touches .meta files")
        risk += 60
    if ".unity" in diff or ".prefab" in diff:
        triggers.append("Diff touches scene/prefab files")
        risk += 50
    if ".asmdef" in diff:
        triggers.append("Diff touches assembly definitions")
        risk += 40
    if "[SerializeField]" in diff or "[SerializeReference]" in diff:
        triggers.append("Diff modifies serialized fields")
        risk += 35
    if "FormerlySerializedAs" in diff:
        triggers.append("Diff adds migration attributes")
        risk += 20
    return risk
