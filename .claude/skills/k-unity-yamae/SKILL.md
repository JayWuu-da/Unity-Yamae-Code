---
name: k-unity-yamae
description: Unity harness workflow for Claude Code Desktop and Claude CLI.
---

# K-Unity-Yamae

Use this skill for Unity work in Claude Code Desktop or Claude CLI when this
project has K-Unity-Yamae installed.
This primary Claude skill is the preferred Claude surface; the slash command
is a compatibility wrapper.

Use only discovered facts and discovered files found in the current Unity
project. If a file, prefab, scene, listener, or Inspector relationship is not
found, report it as unknown until `kunity-yamae inspect --editor-probe --json`
or equivalent Unity evidence runs.

Windows setup expectations:
- Run commands in Windows PowerShell.
- Install Git for Windows for reliable shell and git behavior.
- Keep desktop/CLI handoff and Unity batchmode checks explicit.

Baseline commands:

```powershell
kunity-yamae providers doctor --json
kunity-yamae context --pretty "$ARGUMENTS"
kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json
```

For model-generated edits, produce a unified diff and validate it through
the guarded patch flow:

```powershell
kunity-yamae run "$ARGUMENTS" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

Do not directly edit Unity YAML assets or .meta files. Do not claim Editor,
PlayMode, build, or Inspector validation unless that tier actually ran.
