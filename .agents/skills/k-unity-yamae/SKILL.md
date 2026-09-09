---
name: k-unity-yamae
description: Unity harness workflow for Codex App and Codex CLI on Windows.
---

# K-Unity-Yamae

Completion: changed paths, actual checks, blockers; expand only on request.
Keep necessary verification; shorten narration, not safety evidence.
Use this skill when Codex App or Codex CLI is asked to inspect, plan, edit,
or verify a Unity project that has K-Unity-Yamae installed.

This is an AI-agent Unity harness skill, not a human-facing CLI tutorial.
Use only discovered facts and discovered files found in the current Unity project.
Treat the shared inventory as bounded generic semantic signals, not Inspector proof.
If a file, prefab, scene, listener, or Inspector relationship is not found,
report it as unknown until `kunity-yamae inspect --editor-probe --json` or
equivalent Unity evidence runs.

Command reference for Windows PowerShell; do NOT execute every command for each task.
Prefer `kunity-yamae worker-pack --request-file task.json --json` for bounded work.
A needs_context/escalated packet is not permission to invoke a cheap worker.
For planned_local, use the operation proposal; do not call a worker.

```powershell
kunity-yamae providers doctor --json
kunity-yamae tools list --json
kunity-yamae tools list --schema v2 --json
kunity-yamae context --pretty "$TASK"
kunity-yamae run "$TASK" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "$TASK" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "$TASK" --execute-loop --schema v2 --verify-dry-run --json
kunity-yamae verify --dry-run --quality-gate --json
```

For model-generated edits, ask for a unified diff and route the output through the
guarded flow:

```powershell
kunity-yamae run "$TASK" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

Do not edit Unity assets directly when the guarded patch flow is available.
`kunity-yamae orchestrate` is non-mutating and only prepares handoff evidence.
The explicit v2 execution loop is also non-mutating; it records trace, metrics, memory, and disabled Player adapter status under `.unity-harness/`.
Keep outputs under `.unity-harness/cache/` and `.unity-harness/reports/`,
or `.unity-harness/last-*`; do not track scratch planning/evidence artifacts.
Do not claim Unity Editor, PlayMode, build, or Inspector verification unless run.
