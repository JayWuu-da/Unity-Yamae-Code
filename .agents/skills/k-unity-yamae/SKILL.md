---
name: k-unity-yamae
description: Unity harness workflow for Codex App and Codex CLI on Windows.
---

# K-Unity-Yamae

Use this skill when Codex App or Codex CLI is asked to inspect, plan, edit,
or verify a Unity project that has K-Unity-Yamae installed.

Run these from Windows PowerShell at the Unity project root:

```powershell
kunity-yamae providers doctor --json
kunity-yamae context --pretty "$TASK"
kunity-yamae run "$TASK" --plan-only --verify-dry-run --json
```

For model-generated edits, ask for a unified diff and route the output through
the guarded flow:

```powershell
kunity-yamae run "$TASK" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

Do not edit Unity assets directly when the guarded patch flow is available.
Do not claim Unity Editor, PlayMode, or build verification unless that tier
actually ran.
