# K-Unity-Yamae

These instructions apply when Codex App or Codex CLI opens this repository.

Before Unity harness edits:

```powershell
python -m pytest -q
python -m ruff check .
kunity-yamae providers doctor --json
```

When testing generated Unity-project entrypoints, use:

```powershell
kunity-yamae --project <unity-project> init-agent --target both --dry-run --json
kunity-yamae --project <unity-project> run "$TASK" --plan-only --verify-dry-run --json
```

Rules:
- Use Windows PowerShell command syntax.
- Keep generated assistant entrypoints aligned with `kunity_yamae/desktop_integration.py`.
- Treat scan/context output as discovered facts and discovered files found in the current Unity project.
- Treat the shared inventory as a bounded list of discovered files, tool capabilities, and generic semantic signals.
- Report missing or undiscovered Unity project structure as unknown instead of guessing.
- Use `kunity-yamae inspect --editor-probe --json` before claiming Inspector, prefab, scene, or listener certainty.
- Prefer unified diffs for model-produced patches and route them through `--guarded-agent-patch`.
- Keep harness outputs under `.unity-harness/cache/`, `.unity-harness/reports/`, or `.unity-harness/last-*`; do not track scratch planning/evidence artifacts.
- Do not directly edit Unity YAML assets or `.meta` files.
- Do not claim Unity Editor, PlayMode, build, or Inspector verification unless that tier actually ran and produced evidence.
