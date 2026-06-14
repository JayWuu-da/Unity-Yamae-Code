# /k-unity-yamae

Compatibility command for the primary `.claude/skills/k-unity-yamae/SKILL.md`
skill. Use it before Unity production edits when slash commands are preferred.
It forwards the task text into the K-Unity-Yamae harness context and plan flow.

Use only discovered facts and discovered files found in the current Unity
project. Report missing project structure as unknown. Use `kunity-yamae
inspect --editor-probe --json` before claiming Inspector, prefab, scene, or
listener certainty.

```powershell
kunity-yamae context --pretty "$ARGUMENTS"
kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json
```

When mutation is requested, ask for a unified diff and validate it with:

```powershell
kunity-yamae run "$ARGUMENTS" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```
