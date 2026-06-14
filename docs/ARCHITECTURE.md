# K-Unity-Yamae - Architecture Documentation

## System Overview

K-Unity-Yamae is an AI-agent Unity harness. It does not replace AI coding agents; Codex App/CLI and Claude Code Desktop/CLI use it from the target Unity project root for Unity-specific safety guardrails.

```
┌─────────────────────────────────────────────────────────┐
│        AI agent in the target Unity project root          │
│              "Rename PlayerStats.hitpoints to health"    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│                  Task Intake                              │
│            Normalize task, detect intent                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│              Unity Project Scanner                        │
│  Detect discovered static facts and file signals          │
│  Cache: .unity-harness/project-profile.json              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│                Risk Classifier                            │
│  Input: task text + diff + profile                       │
│  Output: risk_score (0-100), mode, triggers, rules       │
│                                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐           │
│  │ 0-29     │ 30-59    │ 60-79    │ 80-100   │           │
│  │ Fast     │ Standard │ Asset    │ Migration│           │
│  │ Patch    │          │ Safe     │          │           │
│  └──────────┴──────────┴──────────┴──────────┘           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│              Mode Policy                                  │
│  Select enforcement level based on risk score             │
│  Determine: plan required, guards active, verification    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│            Context Selector                               │
│  Select: relevant files, rule cards, project memory      │
│  Limit context to what's needed for the task             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│          Execution Controller                             │
│  One writer agent at a time                              │
│  Optional read-only scouts for analysis                  │
│                                                          │
│  ┌──────────────────┬─────────────────────────────────┐ │
│  │ Codex App/CLI    │ Claude Code Desktop/CLI          │ │
│  │ repo skills      │ repo skills + slash command      │ │
│  └──────────────────┴─────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│              File Guard / Diff Guard                      │
│  Intercept edits, apply Unity-specific guards:           │
│  • Meta guard: .meta pairing, GUID continuity            │
│  • YAML guard: block protected file writes               │
│  • Serialization guard: detect field renames             │
│  • Boundary guard: Editor/runtime separation             │
│  • Asmdef guard: assembly graph impact                   │
│  • Addressables guard: string-key path changes           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│              Unity Verifier                               │
│  Tier 0: Static guards only                              │
│  Tier 1: Unity batchmode compile/import                  │
│  Tier 2: EditMode tests                                  │
│  Tier 3: PlayMode tests                                  │
│  Tier 4: Custom Editor probes (-executeMethod)           │
│  Tier 5: Build validation                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│             Evidence Ledger                               │
│  Append-only JSONL event log                             │
│  Records: file changes, guard results, verification,     │
│           commands, manual checks, errors                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       v
┌──────────────────────────────────────────────────────────┐
│            Completion Report                              │
│  Output: markdown + JSON                                 │
│  Sections: summary, changed files, risk decisions,       │
│            guards run, verification, manual checks,       │
│            limitations, final statement                   │
└─────────────────────────────────────────────────────────┘
```

---

## Risk Model

### Risk Score Calculation

```
risk_score = min(100, file_risk + action_risk + semantic_unity_risk)
```

### File Risk Table

| Pattern | Base Risk | Reason |
|---------|-----------|--------|
| `Assets/**/*.cs` | +10 to +45 | C# varies from low to high risk |
| `Assets/**/*.asmdef` | +55 | Changes compile graph |
| `Assets/**/*.meta` | +80 | Contains GUID/import metadata |
| `Assets/**/*.unity` | +85 | Scene serialization |
| `Assets/**/*.prefab` | +85 | Prefab serialization |
| `Assets/**/*.asset` | +70 | ScriptableObject/settings |
| `ProjectSettings/**` | +80 | Global project behavior |
| `Packages/manifest.json` | +75 | Package versions |

### Semantic Triggers

| Trigger | Risk Score | Examples |
|---------|-----------|----------|
| Serialized field rename | +70 | "Rename X.hitpoints to health" |
| MonoBehaviour lifecycle | +20 | "Add start delay to spawner" |
| Editor/runtime boundary | +25 | "Add custom inspector" |
| Resources/Addressables | +30 | "Change Resources.Load path" |
| Assembly definition | +50 | "Change asmdef references" |
| Package/settings change | +45 | "Upgrade Input System" |
| Asset move | +50 | "Move prefabs to new folder" |
| YAML edit | +55 | "Edit prefab YAML" |

### Mode Selection

| Score Range | Mode | Plan | Guards | Verification |
|-------------|------|------|--------|-------------|
| 0-29 | Fast Patch | No | Minimal | Static only |
| 30-59 | Standard | Short | Relevant rules | Compile/import |
| 60-79 | Asset-Safe | Required | Active | Compile + tests |
| 80-100 | Migration | Detailed | Full | All tiers |

---

## Guard System

### Guarded Proposed Edit Flow

`kunity-yamae propose-edit` is the lightweight tool-loop surface for Codex App,
Claude Code, and LazyCodex-style callers. The caller supplies a unified diff
instead of granting direct write permission.

```text
desktop/CLI agent proposes unified diff
  -> git apply --check in temporary worktree
  -> apply patch in temporary worktree
  -> DiffGuard checks the resulting git diff
  -> hard_failure blocks the real workspace
  -> --apply repeats check and applies to the real workspace only when clean
```

The temporary worktree is removed after evaluation. If a post-apply guard fails
in the real workspace, the patch is reversed and the result is reported as
`rolled_back`.

### Guard Execution Order

1. **Meta Guard**: Check .meta pairing and GUID continuity
2. **Yaml Guard**: Block/warn on protected YAML file writes
3. **Boundary Guard**: Check Editor/runtime assembly separation
4. **Asmdef Guard**: Check assembly definition graph impact
5. **Addressables Guard**: Check Resources/Addressables path changes
6. **Serialization Guard**: Detect serialized field renames (requires old/new content)
7. **Diff Guard**: Orchestrate all guards against git diff

### Guard Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| `hard_failure` | Must fix before proceeding | Block operation |
| `warning` | Should fix, may proceed with caution | Warn user |
| `info` | Notable, no action required | Log only |

---

## Verification Tiers

| Tier | Name | Command | What it Proves |
|------|------|---------|---------------|
| 0 | Static | Guards only | No textual hazards |
| 1 | Compile | `Unity -batchmode -quit` | Scripts compile |
| 2 | EditMode | `Unity -runTests -testPlatform EditMode` | Editor logic works |
| 3 | PlayMode | `Unity -runTests -testPlatform PlayMode` | Runtime behavior works |
| 4 | Custom | `Unity -executeMethod HarnessChecks.RunAll` | Project invariants pass |
| 4a | Editor Inspect | `Unity -executeMethod HarnessChecks.RunEditorInspection` | Persistent listener targets, prefab overrides, and missing serialized references are captured to JSON |
| 5 | Build | `Unity -buildTarget X` | Build pipeline works |
| M | Manual | Inspector/scene check | Visual verification |

`verify --dry-run --json` returns planned Unity command lines without launching
Unity. Reports and run payloads must not claim compile, EditMode, PlayMode, or
build validation unless the corresponding Unity command actually ran.

---

## Unity Facts Coverage

The default scanner is intentionally lightweight and does not require opening
Unity. It reads discovered static facts and signals from project files:

- UI and hierarchy facts: scene count, prefab count, EventSystem and
  GraphicRaycaster counts, button-like prefab wiring, CanvasGroup presence, and
  missing script markers.
- Graphics facts: render pipeline hints, texture importer defaults,
  platform-specific Android/iPhone/Standalone overrides, compression quality,
  crunched compression, and mobile/PC mismatch warnings.
- Architecture hints: MVP/MVC/manager/service naming patterns, presenter/view
  file candidates, controller candidates, ScriptableObject candidates, and a
  confidence warning that naming alone is not ownership proof.

`inspect --editor-probe --json` temporarily stages an Editor script and runs a
Unity batchmode `-executeMethod` probe. That tier can report Inspector-level
facts such as persistent listener targets, prefab override counts, and missing
serialized object references. If Unity is unavailable or the probe fails, the
report keeps the static facts and marks `editor_probe.status` accordingly.

Facts that are not discovered in the current Unity project root remain unknown.
Naming patterns, static YAML/text markers, and cached profile data are not
project ownership proof and are not Inspector proof.

---

## Desktop/CLI Integration Contract

K-Unity-Yamae intentionally keeps model execution outside the harness. Codex App,
Codex CLI, Claude Code Desktop, and Claude CLI read repo-local guidance and use
the harness commands from the Unity project root.

The only executable harness backend is `local-patch`. It accepts a unified diff
through `run --agent local-patch --patch-file proposed.diff --guarded-agent-patch`
and sends that diff through Unity-aware guard evaluation before optional apply.

New model integrations should be added as desktop/CLI entrypoints or skills, not
as in-process backend adapters in `AGENT_REGISTRY`.

---

## Configuration Hierarchy

```
config/default.yml           (built-in defaults)
    ↓ overridden by
.unity-harness/config.yml    (project-specific)
    ↓ overridden by
--config <path>              (CLI override)
    ↓ overridden by
Environment variables        (${VAR} resolution)
```

---

## Data Flow

### Risk Classification Flow

```
Task text
  → _check_serialized_field_rename() → +70 if match
  → _check_monoBehaviour_lifecycle() → +20 if match
  → _check_editor_runtime_boundary() → +25 if match
  → _check_resources_addressables()  → +30 if match
  → _check_asmdef_change()           → +50 if match
  → _check_package_settings()        → +45 if match
  → _check_asset_move()              → +50 if match
  → _check_yaml_edit()               → +55 if match
  → _classify_action()               → +5 to +25
  → _classify_diff_risk()            → +0 to +60
  → sum → min(100, total) → risk_score
```

### Verification Flow

```
verify(compile_check, editmode, playmode, build, custom)
  → _find_unity_executable()
  → for each enabled check:
      → build command line
      → subprocess.run(timeout=...)
      → _parse_unity_log()
      → return {name, status, passed, details, log_path}
  → collect all results
```

---

## File Structure

```
K-Unity-Yamae/
├── kunity_yamae/           # Main package
│   ├── cli.py             # CLI entry point (Click)
│   ├── config.py          # Config loader (YAML merge + env vars)
│   ├── scanner.py         # Unity project scanner
│   ├── risk.py            # Risk classifier (regex-based)
│   ├── modes.py           # Mode policy
│   ├── cli_run.py         # run command entrypoint
│   ├── cli_run_config.py  # run command per-invocation config overrides
│   ├── cli_run_payload.py # plan-only/context-only payload builder
│   ├── cli_run_steps.py   # run command execution steps
│   ├── run_pipeline.py    # mutating run use-case orchestration
│   ├── verifier.py        # Unity verifier facade
│   ├── unity_verification_contracts.py  # typed verifier contracts
│   ├── unity_verification_plan.py     # Unity dry-run command planner
│   ├── unity_verification_steps.py    # Unity batchmode execution steps
│   ├── unity_verification_support.py  # Unity log/executable helpers
│   ├── unity_profile.py               # Unity facts facade
│   ├── unity_profile_common.py        # Shared profile file helpers
│   ├── unity_profile_types.py         # typed Unity profile structures
│   ├── unity_profile_graphics.py      # Graphics/importer facts
│   ├── unity_profile_architecture.py  # Architecture naming facts
│   ├── reporter.py        # Completion report writer
│   ├── ledger.py          # Evidence ledger (JSONL)
│   ├── context.py         # Context selector
│   ├── guards/            # Unity-specific guards
│   │   ├── meta_guard.py
│   │   ├── yaml_guard.py
│   │   ├── serialization_guard.py
│   │   ├── boundary_guard.py
│   │   ├── asmdef_guard.py
│   │   ├── addressables_guard.py
│   │   └── diff_guard.py
│   ├── agents/            # AI agent adapters
│   │   ├── base.py
│   │   └── local_patch_agent.py
│   └── rules/             # Rule card markdown files
├── config/                # Default configuration
├── Editor/                # Unity Editor validation script
├── tests/                 # Test suite
└── docs/                  # Documentation
```
