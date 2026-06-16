# /k-unity-yamae

Compatibility command for the primary `.claude/skills/k-unity-yamae/SKILL.md` skill.
Use it before Unity production edits when slash commands are preferred.
It forwards the task text into the K-Unity-Yamae harness context and plan flow.

Use only discovered facts and discovered files found in the current Unity
project. Treat the shared inventory as bounded generic semantic signals, not
Inspector, PlayMode, or build proof. Report missing project structure as unknown.
Use `kunity-yamae tools list --json` for concrete tool availability and
`kunity-yamae orchestrate` for non-mutating handoff evidence. Use `kunity-yamae
inspect --editor-probe --json` before claiming Inspector, prefab, scene, or
listener certainty.

```powershell
kunity-yamae context --pretty "$ARGUMENTS"
kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "$ARGUMENTS" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "$ARGUMENTS" --execute-loop --schema v2 --verify-dry-run --json
kunity-yamae verify --dry-run --quality-gate --json
```

When mutation is requested, ask for a unified diff and validate it with:

```powershell
kunity-yamae run "$ARGUMENTS" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

Keep outputs under `.unity-harness/cache/` and `.unity-harness/reports/`,
or `.unity-harness/last-*`; do not track scratch planning/evidence artifacts.
Do not claim Unity Editor, PlayMode, build, or Inspector verification unless run.
