CODEX_SKILL_PATH = ".agents/skills/k-unity-yamae/SKILL.md"
CLAUDE_SKILL_PATH = ".claude/skills/k-unity-yamae/SKILL.md"
CLAUDE_COMMAND_PATH = ".claude/commands/kunity-yamae.md"


def codex_init_files() -> dict[str, str]:
    return {
        "AGENTS.md": agents_md(),
        CODEX_SKILL_PATH: codex_skill(),
    }


def claude_init_files() -> dict[str, str]:
    return {
        "CLAUDE.md": claude_md(),
        CLAUDE_SKILL_PATH: claude_skill(),
        CLAUDE_COMMAND_PATH: claude_command(),
    }


def codex_install_files() -> dict[str, str]:
    return {CODEX_SKILL_PATH: codex_skill()}


def claude_install_files() -> dict[str, str]:
    return {
        CLAUDE_SKILL_PATH: claude_skill(),
        CLAUDE_COMMAND_PATH: claude_command(),
    }


def agents_md() -> str:
    return "\n".join(
        [
            "# K-Unity-Yamae",
            "",
            "These instructions apply when Codex App or Codex CLI opens this Unity project.",
            "",
            "Before Unity production edits:",
            "",
            "```powershell",
            'kunity-yamae context --pretty "$TASK"',
            'kunity-yamae risk --json "$TASK"',
            "```",
            "",
            "Use the harness plan before mutation when the change touches Unity behavior:",
            "",
            "```powershell",
            'kunity-yamae run "$TASK" --plan-only --verify-dry-run --json',
            "```",
            "",
            "For model-produced or pasted output, prefer a unified diff and route it",
            "through the guarded patch flow:",
            "",
            "```powershell",
            (
                'kunity-yamae run "$TASK" --agent local-patch --patch-file proposed.diff '
                "--guarded-agent-patch --json"
            ),
            "```",
            "",
            "Quality gates for repo changes:",
            "",
            "```powershell",
            "python -m pytest -q",
            "python -m ruff check .",
            "```",
            "",
            "Rules:",
            "- Use Windows PowerShell command syntax in examples.",
            "- Run `kunity-yamae providers doctor --json` before desktop/CLI handoff work.",
            (
                "- Treat scan/context output as discovered facts and discovered files "
                "found in the current Unity project."
            ),
            "- Report missing or undiscovered project structure as unknown instead of guessing.",
            "- Use `kunity-yamae inspect --editor-probe --json` only when Inspector, prefab,",
            "  scene, or listener certainty is required.",
            "- Do not directly edit Unity YAML assets or .meta files.",
            "- Do not claim Unity Editor, PlayMode, build, or Inspector verification unless",
            "  that tier actually ran and produced evidence.",
        ]
    )


def codex_skill() -> str:
    return "\n".join(
        [
            "---",
            "name: k-unity-yamae",
            "description: Unity harness workflow for Codex App and Codex CLI on Windows.",
            "---",
            "",
            "# K-Unity-Yamae",
            "",
            "Use this skill when Codex App or Codex CLI is asked to inspect, plan, edit,",
            "or verify a Unity project that has K-Unity-Yamae installed.",
            "",
            "This is an AI-agent Unity harness skill, not a human-facing CLI tutorial.",
            "Use only discovered facts and discovered files found in the current Unity project.",
            "If a file, prefab, scene, listener, or Inspector relationship is not found,",
            "report it as unknown until `kunity-yamae inspect --editor-probe --json` or",
            "equivalent Unity evidence runs.",
            "",
            "Run these from Windows PowerShell at the Unity project root:",
            "",
            "```powershell",
            "kunity-yamae providers doctor --json",
            'kunity-yamae context --pretty "$TASK"',
            'kunity-yamae run "$TASK" --plan-only --verify-dry-run --json',
            "```",
            "",
            "For model-generated edits, ask for a unified diff and route the output through",
            "the guarded flow:",
            "",
            "```powershell",
            (
                'kunity-yamae run "$TASK" --agent local-patch --patch-file proposed.diff '
                "--guarded-agent-patch --json"
            ),
            "```",
            "",
            "Do not edit Unity assets directly when the guarded patch flow is available.",
            "Do not claim Unity Editor, PlayMode, or build verification unless that tier",
            "actually ran.",
        ]
    ) + "\n"


def claude_md() -> str:
    return "\n".join(
        [
            "# K-Unity-Yamae",
            "",
            "These instructions apply when Claude Code Desktop or Claude CLI opens this",
            "Unity project.",
            "",
            "Use Windows PowerShell commands. Git for Windows is recommended so Claude",
            "Code shell tools and git diff checks behave consistently.",
            "",
            "Treat scan/context output as discovered facts and discovered files found in",
            "the current Unity project. Report missing project structure as unknown. Use",
            "`kunity-yamae inspect --editor-probe --json` before claiming Inspector, prefab,",
            "scene, or listener certainty.",
            "",
            "Before Unity edits:",
            "",
            "```powershell",
            'kunity-yamae context --pretty "$ARGUMENTS"',
            "kunity-yamae providers doctor --json",
            "```",
            "",
            "Keep Unity batchmode and desktop/CLI handoff checks opt-in unless the task risk",
            "requires them. Never report Editor, PlayMode, build, or Inspector verification",
            "unless that tier actually ran and produced evidence.",
        ]
    )


def claude_skill() -> str:
    return "\n".join(
        [
            "---",
            "name: k-unity-yamae",
            "description: Unity harness workflow for Claude Code Desktop and Claude CLI.",
            "---",
            "",
            "# K-Unity-Yamae",
            "",
            "Use this skill for Unity work in Claude Code Desktop or Claude CLI when this",
            "project has K-Unity-Yamae installed.",
            "This primary Claude skill is the preferred Claude surface; the slash command",
            "is a compatibility wrapper.",
            "",
            "Use only discovered facts and discovered files found in the current Unity",
            "project. If a file, prefab, scene, listener, or Inspector relationship is not",
            "found, report it as unknown until `kunity-yamae inspect --editor-probe --json`",
            "or equivalent Unity evidence runs.",
            "",
            "Windows setup expectations:",
            "- Run commands in Windows PowerShell.",
            "- Install Git for Windows for reliable shell and git behavior.",
            "- Keep desktop/CLI handoff and Unity batchmode checks explicit.",
            "",
            "Baseline commands:",
            "",
            "```powershell",
            "kunity-yamae providers doctor --json",
            'kunity-yamae context --pretty "$ARGUMENTS"',
            'kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json',
            "```",
            "",
            "For model-generated edits, produce a unified diff and validate it through",
            "the guarded patch flow:",
            "",
            "```powershell",
            (
                'kunity-yamae run "$ARGUMENTS" --agent local-patch '
                "--patch-file proposed.diff --guarded-agent-patch --json"
            ),
            "```",
            "",
            "Do not directly edit Unity YAML assets or .meta files. Do not claim Editor,",
            "PlayMode, build, or Inspector validation unless that tier actually ran.",
        ]
    ) + "\n"


def claude_command() -> str:
    return "\n".join(
        [
            "# /k-unity-yamae",
            "",
            "Compatibility command for the primary `.claude/skills/k-unity-yamae/SKILL.md`",
            "skill. Use it before Unity production edits when slash commands are preferred.",
            "It forwards the task text into the K-Unity-Yamae harness context and plan flow.",
            "",
            "Use only discovered facts and discovered files found in the current Unity",
            "project. Report missing project structure as unknown. Use `kunity-yamae",
            "inspect --editor-probe --json` before claiming Inspector, prefab, scene, or",
            "listener certainty.",
            "",
            "```powershell",
            'kunity-yamae context --pretty "$ARGUMENTS"',
            'kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json',
            "```",
            "",
            "When mutation is requested, ask for a unified diff and validate it with:",
            "",
            "```powershell",
            (
                'kunity-yamae run "$ARGUMENTS" --agent local-patch '
                "--patch-file proposed.diff --guarded-agent-patch --json"
            ),
            "```",
        ]
    ) + "\n"
