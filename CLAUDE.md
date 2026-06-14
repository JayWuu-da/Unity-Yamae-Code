# K-Unity-Yamae

These instructions apply when Claude Code Desktop or Claude CLI opens this repository.

Use Windows PowerShell commands. Git for Windows is recommended so Claude shell and git operations behave consistently.

Before changing Python, templates, or docs:

```powershell
python -m pytest -q
python -m ruff check .
```

For generated Unity-project integrations:

```powershell
kunity-yamae --project <unity-project> init-agent --target both --dry-run --json
kunity-yamae --project <unity-project> providers doctor --json
```

Keep `.agents/skills/k-unity-yamae/SKILL.md`, `.claude/skills/k-unity-yamae/SKILL.md`, and `.claude/commands/kunity-yamae.md` aligned with `kunity_yamae/desktop_integration.py`.

Rules:
- Treat scan/context output as discovered facts and discovered files found in the current Unity project.
- Report missing or undiscovered Unity project structure as unknown instead of guessing.
- Use `kunity-yamae inspect --editor-probe --json` before claiming Inspector, prefab, scene, or listener certainty.

Never report Unity Editor, PlayMode, build, or Inspector verification unless that tier actually ran and produced evidence.
