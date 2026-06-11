from .risk_checks import (
    check_architecture_pattern,
    check_asmdef_change,
    check_asset_move,
    check_data_contract,
    check_editor_runtime_boundary,
    check_execution_path,
    check_graphics_platform,
    check_mono_behaviour_lifecycle,
    check_package_settings,
    check_resources_addressables,
    check_serialized_field_rename,
    check_ui_interaction,
    check_yaml_edit,
    classify_action,
    classify_diff_risk,
    normalize_task_text,
)


class RiskClassifier:
    def __init__(self, config: dict):
        self.config = config
        self.risk_config = config.get("risk", {})
        self.file_risk_scores = config.get("file_risk_scores", {})

    def classify(self, task: str, profile: dict, diff: str = "") -> dict:
        triggers: list[str] = []
        file_risk = 0
        semantic_risk = 0
        task_text = normalize_task_text(task)

        semantic_risk += check_serialized_field_rename(task_text, triggers)
        semantic_risk += check_mono_behaviour_lifecycle(task_text, triggers)
        semantic_risk += check_editor_runtime_boundary(task_text, triggers)
        semantic_risk += check_resources_addressables(task_text, triggers)
        semantic_risk += check_ui_interaction(task_text, triggers)
        semantic_risk += check_execution_path(task_text, triggers)
        semantic_risk += check_data_contract(task_text, triggers)
        semantic_risk += check_graphics_platform(task_text, triggers)
        semantic_risk += check_architecture_pattern(task_text, triggers)
        semantic_risk += check_asmdef_change(task_text, triggers)
        semantic_risk += check_package_settings(task_text, triggers)
        semantic_risk += check_asset_move(task_text, triggers)
        semantic_risk += check_yaml_edit(task_text, triggers)

        if diff:
            file_risk += classify_diff_risk(diff, triggers)

        total_risk = min(100, file_risk + classify_action(task_text) + semantic_risk)
        mode = self._select_mode(total_risk)

        return {
            "schema": "unity-harness.risk-report.v1",
            "task": task,
            "risk_score": total_risk,
            "mode": mode,
            "triggers": triggers,
            "required_rule_cards": self._select_rule_cards(triggers),
            "blocked_operations": self._get_blocked_operations(mode),
            "required_verification": self._select_verification(mode),
            "rationale": self._generate_rationale(total_risk, mode, triggers),
        }

    def _select_mode(self, risk_score: int) -> str:
        if risk_score <= self.risk_config.get("low_max", 29):
            return "fast_patch"
        if risk_score <= self.risk_config.get("standard_max", 59):
            return "standard"
        if risk_score <= self.risk_config.get("asset_safe_max", 79):
            return "asset_safe"
        return "migration"

    def _get_blocked_operations(self, mode: str) -> list[str]:
        protected = self.config.get("protected_files", {})
        block = protected.get("block_direct_write", [])
        if mode in ("fast_patch", "standard"):
            return block + protected.get("escalate_direct_write", [])
        if mode == "asset_safe":
            return block
        return []

    def _select_rule_cards(self, triggers: list[str]) -> list[str]:
        rules = ["unity.global"]
        trigger_rule_map = {
            "Serialized field/class rename": "unity.serialized-field-rename",
            "MonoBehaviour lifecycle": "unity.monobehaviour-lifecycle",
            "Editor/runtime boundary": "unity.editor-runtime-boundary",
            "Resources/Addressables path change": "unity.resources-addressables",
            "Unity UI interaction/hierarchy": "unity.ui",
            "Unity execution path tracing": "unity.execution-path",
            "Unity data contract/payload": "unity.data-contracts",
            "Graphics/import platform settings": "unity.graphics-platform",
            "Unity architecture pattern": "unity.architecture-patterns",
            "Assembly definition change": "unity.asmdef",
            "Asset move/rename": "unity.meta-guid",
            "Direct YAML edit": "unity.prefab-scene-yaml",
            "Diff touches .meta files": "unity.meta-guid",
            "Diff touches scene/prefab files": "unity.prefab-scene-yaml",
            "Diff modifies serialized fields": "unity.serialized-field-rename",
        }
        for trigger in triggers:
            for key, rule in trigger_rule_map.items():
                if key in trigger and rule not in rules:
                    rules.append(rule)
        return rules

    def _select_verification(self, mode: str) -> list[str]:
        verification = ["static guards"]
        if mode in ("standard", "asset_safe", "migration"):
            verification.append("Unity compile/import")
        if mode in ("asset_safe", "migration"):
            verification.extend(["EditMode tests", "PlayMode tests"])
        if mode == "migration":
            verification.append("Build validation")
        return verification

    def _generate_rationale(self, risk_score: int, mode: str, triggers: list[str]) -> str:
        lines = [f"Risk score {risk_score} -> {mode} mode."]
        if triggers:
            lines.append(f"Triggers: {', '.join(triggers[:5])}.")
        if risk_score < 30:
            lines.append("Low Unity-specific risk; fast patch appropriate.")
        elif risk_score < 60:
            lines.append("Moderate risk; standard verification recommended.")
        elif risk_score < 80:
            lines.append("Significant Unity risk; asset-safe guards required.")
        else:
            lines.append("High risk; migration-level guardrails and evidence required.")
        return " ".join(lines)
