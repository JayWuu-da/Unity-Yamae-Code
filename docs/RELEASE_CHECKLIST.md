# K-Unity-Yamae Release Checklist

## Local Quality Gate

Run before tagging or handing the harness to an AI agent for a Unity production repo:

```bash
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```

## Agent-Facing Copy Checks

`release-check --json` must report `agent_facing_copy` with all checks passing:

- English and Korean README files describe the AI-agent workflow from git URL to target Unity project root.
- Codex and Claude entrypoints state that context contains discovered facts and discovered files only.
- Primary docs describe the shared inventory as discovered files, tool capabilities, and bounded generic semantic signals.
- Primary docs mention `kunity-yamae tools list --json` and non-mutating `kunity-yamae orchestrate ... --plan-only --verify-dry-run --json` as concrete AI-agent orchestration tools.
- Primary docs mention the explicit v2 surfaces: `tools list --schema v2 --json`, `orchestrate ... --execute-loop --schema v2 --verify-dry-run --json`, and `verify --dry-run --quality-gate --json`.
- Static scanner limits are documented as signals, not Inspector proof.
- Static and planned evidence do not prove Inspector object references, prefab override intent, PlayMode behavior, Game View state, or build success.
- Do not claim Unity Editor, PlayMode, build, or Inspector verification unless that tier actually ran and produced evidence.
- Primary docs avoid path placeholders and subcommand-level project options.
- Model-backend credential setup language and scratch planning/evidence artifacts are absent from tracked files.
- Harness output cleanup receipts stay under `.unity-harness/cache/`, `.unity-harness/reports/`, or `.unity-harness/last-*`; scratch planning/evidence artifacts stay untracked.

## Harness Smoke Checks

Use a fixture or disposable Unity project:

```bash
python tests/fixtures/make_unity_project.py --kind ui-graphics-architecture --out tmp/release-fixture --git-init
kunity-yamae --project tmp/release-fixture scan --json
kunity-yamae --project tmp/release-fixture risk "Fix prefab button raycast" --json
kunity-yamae --project tmp/release-fixture context --pretty "Fix prefab button raycast"
kunity-yamae --project tmp/release-fixture providers doctor --json
kunity-yamae --project tmp/release-fixture run "Fix prefab button raycast" --plan-only --verify-dry-run --json
kunity-yamae --project tmp/release-fixture tools list --schema v2 --json
kunity-yamae --project tmp/release-fixture orchestrate "Inspect neutral runtime component" --execute-loop --schema v2 --verify-dry-run --json
kunity-yamae --project tmp/release-fixture verify --dry-run --quality-gate --json
```

## Unity Editor Checks

Only claim these checks when Unity actually ran:

```bash
kunity-yamae --project <unity-project> inspect --editor-probe --json
kunity-yamae --project <unity-project> verify --compile-only
kunity-yamae --project <unity-project> verify --editmode
kunity-yamae --project <unity-project> verify --playmode
```

If Unity is not installed or batchmode fails, report static scan and guard
coverage only.

## Agent Integration Checks

Run these from Windows PowerShell when validating Codex App/CLI or Claude Code
Desktop/CLI entrypoints. Claude Code Desktop should have Git for Windows
available before opening a local Unity repository.

```bash
kunity-yamae --project <unity-project> init-agent --target both --dry-run --json
kunity-yamae --project <unity-project> init-agent --target both --write
```

Confirm generated files:

- `AGENTS.md`
- `CLAUDE.md`
- `.agents/skills/k-unity-yamae/SKILL.md`
- `.claude/skills/k-unity-yamae/SKILL.md`
- `.claude/commands/kunity-yamae.md`

Confirm generated files match `kunity_yamae/desktop_integration.py` and route
Unity edits through plan-only checks or local guarded patch handoff.

## Guarded Edit Checks

For Codex/Claude/LazyCodex-style patch handoff:

```bash
kunity-yamae --project <unity-project> propose-edit "Task" --patch-file proposed.diff --json
kunity-yamae --project <unity-project> propose-edit "Task" --patch-file proposed.diff --apply --json
kunity-yamae --project <unity-project> guard-diff --json
```

Hard failures must block application or roll back the patch.
