# /k-unity-yamae

Use this command before Unity production edits. It forwards the task text into
the K-Unity-Yamae harness context and plan flow.

```powershell
kunity-yamae context --pretty "$ARGUMENTS"
kunity-yamae run "$ARGUMENTS" --plan-only --verify-dry-run --json
```

When mutation is requested, ask for a unified diff and validate it with:

```powershell
kunity-yamae run "$ARGUMENTS" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```
