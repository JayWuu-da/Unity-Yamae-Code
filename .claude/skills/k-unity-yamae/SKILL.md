---
name: k-unity-yamae
description: Unity harness workflow for Claude Code Desktop and Claude CLI.
---

# K-Unity-Yamae

Use this skill for Unity work in Claude Code Desktop or Claude CLI when this project
has K-Unity-Yamae installed.
This primary Claude skill is the preferred Claude surface; the slash command is a
compatibility wrapper.

Use only discovered facts and discovered files found in the current Unity
project. Treat the shared inventory as bounded generic semantic signals, not
Inspector object reference proof, prefab override proof, PlayMode proof, or
build proof. If a file, prefab, scene, listener, or Inspector relationship is not
found, report it as unknown until `kunity-yamae inspect --editor-probe --json`
or equivalent Unity evidence runs.

Windows setup expectations:
- Run commands in Windows PowerShell.
- Install Git for Windows for reliable shell and git behavior.
- Keep desktop/CLI handoff and Unity batchmode checks explicit.

Baseline commands:

```powershell
kunity-yamae providers doctor --json
kunity-yamae tools list --json
kunity-yamae tools list --schema v2 --json
kunity-yamae context --pretty "$ARGUMENTS"
kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "$ARGUMENTS" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "$ARGUMENTS" --execute-loop --schema v2 --verify-dry-run --json
kunity-yamae verify --dry-run --quality-gate --json
```

For model-generated edits, produce a unified diff and validate it through the guarded
patch flow:

```powershell
kunity-yamae run "$ARGUMENTS" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

`kunity-yamae orchestrate` is non-mutating and only prepares handoff evidence.
The explicit v2 execution loop is also non-mutating; it records trace, metrics, memory, and disabled Player adapter status under `.unity-harness/`.
Keep outputs under `.unity-harness/cache/` and `.unity-harness/reports/`,
or `.unity-harness/last-*`; do not track scratch planning/evidence artifacts.
Do not directly edit Unity YAML assets or .meta files. Do not claim Editor,
PlayMode, build, or Inspector validation unless that tier actually ran.
