"""Context selector - provides only relevant files and rule cards for a task."""

from pathlib import Path
from typing import Any

from .constants import GENERATED_FOLDERS
from .profile_cache import cached_profile_inventory, cached_script_paths, load_cached_profile
from .risk_checks import (
    check_data_contract,
    check_execution_path,
    check_graphics_platform,
    check_ui_interaction,
    has_task_keyword,
    normalize_task_text,
)
from .semantic_index import runtime_safety_hints


class ContextSelector:
    def __init__(self, project_path: Path, config: dict[str, Any]):
        self.project_path: Path = project_path
        self.config: dict[str, Any] = config
        ctx_config = config.get("context", {})
        self.max_memory_chars: int = int(ctx_config.get("max_memory_chars", 2000))
        self.max_preview_lines: int = int(ctx_config.get("max_preview_lines", 50))
        self.max_files: int = int(ctx_config.get("max_files", 10))
        self.max_file_size: int = int(ctx_config.get("max_file_size", 100000))

    def select(self, task: str, risk_report: dict[str, Any], mode: str) -> dict[str, Any]:
        """Select relevant context for the task."""
        relevant_files: list[str] = []
        summaries: list[dict[str, Any]] = []
        profile = load_cached_profile(self.project_path)
        context = {
            "task_brief": task,
            "risk_report": risk_report,
            "mode": mode,
            "rule_cards": self._select_rule_cards(risk_report),
            "relevant_files": relevant_files,
            "summaries": summaries,
            "unity_facts": self._select_unity_facts(task, profile),
            "fact_limits": self._fact_limits(),
            "manual_checks": self._manual_checks(task, mode),
            "project_memory": self._load_nearest_memory(task),
        }

        target_files = self._infer_target_files(task, profile)
        for f in target_files:
            full_path = self.project_path / f
            if full_path.exists():
                relevant_files.append(f)
                if f.endswith(".cs") and full_path.stat().st_size < self.max_file_size:
                    try:
                        content = full_path.read_text(encoding="utf-8")
                        summaries.append(
                            {
                                "path": f,
                                "type": "csharp",
                                "lines": len(content.splitlines()),
                                "preview": "\n".join(
                                    content.splitlines()[: self.max_preview_lines]
                                ),
                            }
                        )
                    except OSError:
                        pass

        return context

    def _select_rule_cards(self, risk_report: dict[str, Any]) -> list[str]:
        return risk_report.get("required_rule_cards", ["unity.global"])

    def _select_unity_facts(self, task: str, profile: dict[str, Any]) -> dict[str, Any]:
        fact_keys = ["render_pipeline", "input_system", "platform_targets", "asset_summary"]
        task_text = normalize_task_text(task)
        if check_ui_interaction(task_text, []):
            fact_keys.append("ui_system")
        if check_graphics_platform(task_text, []):
            fact_keys.append("graphics_defaults")
        if has_task_keyword(
            task_text,
            [
                "mvp",
                "mvc",
                "presenter",
                "controller",
                "manager",
                "service",
                "architecture",
                "refactor",
            ],
        ):
            fact_keys.append("architecture_patterns")
        selected = {key: profile.get(key, {}) for key in fact_keys}
        selected["asset_summary"] = self._task_focused_asset_summary(
            task_text,
            selected.get("asset_summary", {}),
            profile.get("runtime_asset_signals", {}),
        )
        if has_task_keyword(task_text, ["visual", "runtime asset", "resources.load", "prefab"]):
            selected["runtime_asset_signals"] = profile.get("runtime_asset_signals", {})
        safety = runtime_safety_hints(
            task,
            self.project_path,
            inventory=cached_profile_inventory(self.project_path, profile),
        )
        if safety:
            selected["runtime_safety"] = safety
        return selected

    def _fact_limits(self) -> dict[str, str | list[str]]:
        return {
            "source": (
                "Only discovered facts and discovered files from the current Unity project "
                "profile, static scan, context selection, and task-focused file reads."
            ),
            "unknown_policy": (
                "If a project file, prefab, scene, listener, generated source, or convention "
                "is not discovered, report it as unknown instead of inferring it."
            ),
            "editor_probe_required_for": [
                (
                    "Run `kunity-yamae inspect --editor-probe --json` or "
                    "equivalent Unity evidence for:"
                ),
                "Inspector object references",
                "prefab override intent",
                "persistent listener target validity",
                "missing serialized reference certainty",
                "PlayMode, Game View, build, or visual behavior claims",
            ],
            "no_claim_without_evidence": (
                "Do not claim Unity Editor, PlayMode, build, Game View, or Inspector "
                "verification unless that tier actually ran and produced evidence."
            ),
        }

    def _manual_checks(self, task: str, mode: str) -> list[str]:
        task_text = normalize_task_text(task)
        checks: list[str] = []
        if check_ui_interaction(task_text, []):
            checks.append(
                "Verify EventSystem, GraphicRaycaster, interactable state, and raycast blockers."
            )
        if check_execution_path(task_text, []):
            checks.append(
                "Trace the real user path before editing: entry point, open/create call, "
                "prefab or listener binding, controller reset, lock conditions, and final renderer."
            )
        if check_data_contract(task_text, []):
            checks.append(
                "Verify source rows, display keys, request/response DTOs, "
                "output shape, merge rules, and response apply path."
            )
        if has_task_keyword(task_text, ["prefab", "scene", "hierarchy"]):
            checks.append(
                "Verify prefab overrides, missing scripts, active hierarchy, "
                "and serialized references."
            )
        if check_graphics_platform(task_text, []):
            checks.append(
                "Compare Android, iOS, and PC import overrides before recommending changes."
            )
        if mode in ("asset_safe", "migration"):
            checks.append(
                "Run Unity Editor/manual inspection before claiming visual or Inspector behavior."
            )
        if has_task_keyword(
            task_text,
            ["visual", "runtime asset", "resources.load", "resources load"],
        ):
            checks.append(
                "Use Unity MCP for refresh, tests, Game View screenshot, hierarchy, "
                "and console checks."
            )
            checks.append(
                "Verify Resources.Load paths against discovered Resources folders, "
                "runtime asset lifetime, spawn caps, recursion guards, and collider side effects."
            )
        return checks

    def _task_focused_asset_summary(
        self,
        task_lower: str,
        asset_summary: dict[str, Any],
        runtime_asset_signals: dict[str, Any],
    ) -> dict[str, Any]:
        compact = dict(asset_summary)
        prefabs = asset_summary.get("prefabs", [])
        if not isinstance(prefabs, list):
            compact["prefabs"] = []
            return compact
        focused = [
            prefab
            for prefab in prefabs
            if isinstance(prefab, str)
            and not prefab.startswith("Library/")
            and self._matches_task_asset(task_lower, prefab)
        ]
        if focused:
            compact["prefabs"] = focused[: self.max_files]
        else:
            compact["prefabs"] = [
                prefab
                for prefab in prefabs[: self.max_files]
                if isinstance(prefab, str) and not prefab.startswith("Library/")
            ]
        if runtime_asset_signals:
            compact["runtime_asset_summary"] = runtime_asset_signals.get("summary", {})
        return compact

    @staticmethod
    def _matches_task_asset(task_lower: str, path: str) -> bool:
        path_lower = path.lower()
        task_tokens = {token for token in task_lower.replace("/", " ").split() if len(token) > 2}
        return any(token in path_lower for token in task_tokens)

    def _infer_target_files(self, task: str, profile: dict[str, Any]) -> list[str]:
        task_words = self._search_words(task)
        files: list[str] = []
        for relative_path in cached_script_paths(profile):
            script_path = self.project_path / relative_path
            if self._is_in_generated(script_path):
                continue
            name_words = self._search_words(Path(relative_path).stem)
            if task_words & name_words:
                files.append(relative_path)
        return files[: self.max_files]

    @staticmethod
    def _search_words(text: str) -> set[str]:
        normalized = normalize_task_text(text)
        words = {token for token in normalized.split() if len(token) > 2}
        compact = normalized.replace(" ", "")
        if len(compact) > 2:
            words.add(compact)
        return words

    def _load_nearest_memory(self, task: str) -> str | None:
        candidates = [
            self.project_path / "AGENTS.md",
            self.project_path / "Assets" / "UNITY_AGENTS.md",
        ]
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")[: self.max_memory_chars]
        return None

    def _is_in_generated(self, path: Path) -> bool:
        parts = path.relative_to(self.project_path).parts
        return bool(GENERATED_FOLDERS & set(parts))
