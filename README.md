# K-Unity-Yamae

**A thin, risk-adaptive Unity agent harness for AI coding agents.**

K-Unity-Yamae is a Python-based safety layer for Codex App/CLI and Claude Code Desktop/CLI Unity work. It provides repo-local skills, project instructions, guarded patch handoff, Unity-specific risk classification, serialized artifact guards, Unity batchmode verification, and evidence-tracked completion reports.

---

## Table of Contents

- [Philosophy](#philosophy)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Commands](#cli-commands)
- [Risk Model](#risk-model)
- [Risk Modes](#risk-modes)
- [Unity Guards](#unity-guards)
- [Verification Tiers](#verification-tiers)
- [Desktop and CLI Integrations](#desktop-and-cli-integrations)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Rule Cards](#rule-cards)
- [Evidence Ledger](#evidence-ledger)
- [Unity Editor Integration](#unity-editor-integration)
- [Advanced Topics](#advanced-topics)
- [Inspired By](#inspired-by)
- [License](#license)

---

## Philosophy

> Adopt the discipline, not the ceremony.

- **Low-risk C# edits should be fast.** No mandatory deep interview or full planning loop for a typo fix.
- **Asset/serialization changes should be strict.** Strong guardrails for .meta, .unity, .prefab, .asset, .asmdef, and serialized fields.
- **Verification must be honest.** Never claim Editor or Play Mode validation unless it actually ran.
- **One writer at a time.** Parallel read-only analysis is fine; parallel asset mutation is not.
- **Report what you did, not what you hoped happened.**

---

## Architecture

```
User Task
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  Task Intake                             │
│           Normalize task, detect intent                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Unity Project Scanner                       │
│  Detect: version, packages, assemblies, scenes, tests   │
│  Cache: .unity-harness/project-profile.json             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                Risk Classifier                           │
│  Input: task text + git diff + project profile          │
│  Output: risk_score (0-100), mode, triggers, rules      │
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐          │
│  │ 0-29     │ 30-59    │ 60-79    │ 80-100   │          │
│  │ Fast     │ Standard │ Asset    │ Migration│          │
│  │ Patch    │          │ Safe     │          │          │
│  └──────────┴──────────┴──────────┴──────────┘          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Context Selector                            │
│  Select: relevant files, rule cards, project memory     │
│  Inject: file previews, Unity-specific guidance         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Execution Controller                          │
│  One writer agent at a time                             │
│  Optional read-only scouts for analysis                 │
│                                                         │
│  ┌──────────────────┬────────────────────────────────┐ │
│  │ Codex App/CLI    │ Claude Code Desktop/CLI         │ │
│  │ repo skills      │ repo skills + slash command     │ │
│  └──────────────────┴────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          File Guard / Diff Guard                         │
│  Intercept edits, apply Unity-specific guards:          │
│  • Meta guard: .meta pairing, GUID continuity           │
│  • YAML guard: block protected file writes              │
│  • Serialization guard: detect field renames            │
│  • Boundary guard: Editor/runtime separation            │
│  • Asmdef guard: assembly graph impact                  │
│  • Addressables guard: string-key path changes          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Unity Verifier                              │
│  Tier 0: Static guards only                             │
│  Tier 1: Unity batchmode compile/import                 │
│  Tier 2: EditMode tests                                 │
│  Tier 3: PlayMode tests                                 │
│  Tier 4: Custom Editor probes (-executeMethod)          │
│  Tier 5: Build validation                               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│             Evidence Ledger                              │
│  Append-only JSONL event log                            │
│  Records: file changes, guard results, verification,    │
│           commands, manual checks, errors                │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Completion Report                             │
│  Output: markdown + JSON                                │
│  Sections: summary, changed files, risk decisions,      │
│            guards run, verification tiers, manual checks │
└─────────────────────────────────────────────────────────┘
```

---

## Installation

### Official Releases

GitHub Releases are the official installation source for K-Unity-Yamae.
Use the latest release from:

https://github.com/JayWuu-da/K-Unity-Yamae/releases

### From Source (Contributors)

```bash
# Clone the repository
git clone https://github.com/JayWuu-da/K-Unity-Yamae.git
cd K-Unity-Yamae

# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Dependencies

**Core dependencies** (always installed):
- `pyyaml>=6.0` - YAML config parsing
- `click>=8.0` - CLI framework
- `rich>=13.0` - Terminal formatting

### Requirements

- Python >= 3.10
- Git (for diff guards and git status checks)
- Unity Editor (for verification tiers 1-5, optional for tier 0)
- Windows users should run examples in PowerShell. Git for Windows is recommended
  for Codex App/CLI and Claude Code Desktop/CLI sessions because both workflows
  rely on git diff and shell behavior.

---

## Quick Start

### 0. Install Codex and Claude Code entrypoints

```bash
kunity-yamae install --codex --claude
kunity-yamae init-agent --target both --write
```

This writes repo-local entry files for Codex App/CLI and Claude Code Desktop/CLI so both agents can call the same Unity-aware harness instead of relying on a long pasted prompt.

On Windows, run these commands from PowerShell at the Unity project root. For
Claude Code Desktop, install Git for Windows before opening the project so the
Code tab can use the local repository and terminal reliably.

### 1. Scan your Unity project

```bash
kunity-yamae scan --project /path/to/your/unity/project
```

This detects Unity version, packages, assemblies, scenes, and protected paths. Results are cached to `.unity-harness/project-profile.json`.

### 2. Classify task risk

```bash
kunity-yamae risk "Rename PlayerStats.hitpoints to health"
```

Output:
```
╭─ Risk Report ─────╮
│ Task    │ Rename PlayerStats.hitpoints to health
│ Score   │ 80
│ Mode    │ migration
│ Triggers│ Serialized field/class rename
│ Rules   │ unity.serialized-field-rename
╰───────────────────╯
```

### 3. Run the full pipeline

```bash
kunity-yamae run "Fix enemy spawn delay bug" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

This runs the guarded local handoff: risk classification -> local patch read -> guard evaluation -> JSON report.

### 4. Individual commands

```bash
# Build a task context pack for Codex App/CLI or Claude Code
kunity-yamae context --pretty "Fix UI raycast and Android texture compression"

# Get a lightweight, non-mutating run plan
kunity-yamae run "Fix ShopPresenter button raycast" --plan-only --verify-dry-run --json

# Validate a proposed unified diff before applying it
kunity-yamae propose-edit "Fix ShopPresenter" --patch-file proposed.diff --json
kunity-yamae propose-edit "Fix ShopPresenter" --patch-file proposed.diff --apply --json

# Inspect hierarchy, prefabs, UI, and graphics import facts
kunity-yamae inspect --json

# Run Unity Editor API probe first, then merge richer Inspector facts
kunity-yamae inspect --editor-probe --json

# Diagnose desktop/CLI entrypoint readiness
kunity-yamae providers doctor --json

# Validate a model-produced patch through the local guarded handoff
kunity-yamae run "Fix null check in DamageCalculator" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json

# Run verification only
kunity-yamae verify --compile-only
kunity-yamae verify --editmode
kunity-yamae verify --playmode

# Check git diff for Unity hazards
kunity-yamae guard-diff

# View last report
kunity-yamae report --last
```

---

## CLI Commands

### `kunity-yamae install`

Write lightweight repo-local skill entrypoints for Codex App/CLI and Claude Code.

```bash
kunity-yamae install --codex --claude
kunity-yamae install          # defaults to both
kunity-yamae install --codex  # Codex skill only
kunity-yamae install --claude # Claude skill and command only
```

**Output:** `.agents/skills/k-unity-yamae/SKILL.md` and/or `.claude/skills/k-unity-yamae/SKILL.md` plus `.claude/commands/kunity-yamae.md`.

### `kunity-yamae scan`

Build or refresh the Unity project profile.

```bash
kunity-yamae scan --project ./MyUnityGame
kunity-yamae scan --deep          # Include assembly graph analysis
kunity-yamae scan --write-memory  # Write UNITY_AGENTS.md files
kunity-yamae scan --json          # Machine-readable profile
```

**Output:** Project version, packages, assemblies, scenes, protected patterns.

### `kunity-yamae context`

Build the compact task context pack used before a Codex App/CLI or Claude Code edit.

```bash
kunity-yamae context --pretty "Fix UI raycast and Android texture compression"
kunity-yamae context --deep --pretty "Audit prefab hierarchy and scene references"
```

**Output:** JSON with risk mode, rule cards, selected Unity facts, relevant files, and manual checks.

### `kunity-yamae risk`

Classify task risk before mutation.

```bash
kunity-yamae risk "Rename PlayerStats.hitpoints to health"
kunity-yamae risk --diff  # Include current git diff in classification
kunity-yamae risk "Fix prefab button raycast" --json
```

**Output:** Risk score (0-100), mode, triggers, required rule cards, blocked operations, verification plan.

### `kunity-yamae inspect`

Inspect hierarchy, prefab, UI, and graphics import facts without editing the project.

```bash
kunity-yamae inspect --json
kunity-yamae inspect --editor-probe --json
```

**Output:** Scene count, prefab instance count, missing script prefab count, EventSystem/GraphicRaycaster counts, texture platform overrides, render pipeline, input system, and `editor_probe` status. With `--editor-probe`, the harness temporarily stages its Editor probe under `Assets/Editor/KUnityYamaeHarness/`, runs `KUnityYamae.Editor.HarnessChecks.RunEditorInspection` in batchmode, merges persistent listener targets, prefab override counts, and missing serialized object references from `.unity-harness/reports/editor-inspection.json`, then removes the staged probe files.

### `kunity-yamae providers doctor`

Diagnose Codex App/CLI and Claude Code Desktop/CLI entrypoint readiness.

```bash
kunity-yamae providers doctor --json
```

**Output:** generated entrypoint path readiness, Windows guidance, and the local `local-patch` handoff. It performs local file checks only.

### `kunity-yamae work`

Run a task through the local guarded patch backend.

```bash
kunity-yamae work "Fix enemy spawn delay" --agent local-patch
kunity-yamae run "Add health bar UI" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

**Options:**
- `--agent` - Agent backend (`local-patch` only; Codex and Claude run through their own desktop/CLI apps)
- `--mode` - Force a specific mode (fast_patch, standard, asset_safe, migration)
- `--auto` - Auto-select mode from risk score

### `kunity-yamae run`

Run the full pipeline (risk -> work -> verify -> guard -> report).

```bash
kunity-yamae run "Rename PlayerStats.hitpoints to health" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
kunity-yamae run "Fix typo in comments" --agent local-patch --no-verify --no-guard
kunity-yamae run "Fix UI button" --plan-only --verify-dry-run --json
```

**Options:**
- `--agent` - Agent backend
- `--verify` / `--no-verify` - Enable/disable verification (default: enabled)
- `--guard` / `--no-guard` - Enable/disable guard checks (default: enabled)
- `--plan-only` - Build scan/risk/context/guard/verify plan without agent execution
- `--provider-check` - Fail fast when the selected desktop/CLI handoff is not ready
- `--verify-dry-run` - Include Unity command lines without launching Unity

### `kunity-yamae verify`

Run Unity-aware checks without editing.

```bash
kunity-yamae verify --compile-only
kunity-yamae verify --editmode
kunity-yamae verify --playmode
kunity-yamae verify --build StandaloneWindows64
kunity-yamae verify --custom-method Company.Project.Editor.HarnessChecks.RunAll
kunity-yamae verify --compile-only --dry-run --json
```

### `kunity-yamae guard-diff`

Inspect current git diff for Unity-specific hazards.

```bash
kunity-yamae guard-diff
kunity-yamae guard-diff --json
```

**Checks:** Meta pairing, GUID continuity, YAML writes, Editor/runtime boundaries, asmdef changes, Addressables paths.

### `kunity-yamae propose-edit`

Validate a unified diff in a temporary git worktree before applying it to the real project.

```bash
kunity-yamae propose-edit "Fix UI raycast" --patch-file proposed.diff --json
kunity-yamae propose-edit "Fix UI raycast" --patch-file proposed.diff --apply --json
```

**Output:** `unity-harness.proposed-edit.v1` with `ready_to_apply`, `blocked`, `invalid_patch`, `applied`, or `rolled_back`. Hard failures from Unity guards block application.

### `kunity-yamae report`

Show the last task report.

```bash
kunity-yamae report --last
```

---

## Risk Model

### Risk Score Calculation

```
risk_score = min(100, file_risk + action_risk + semantic_unity_risk)
```

### File Risk Table

| File Pattern | Base Risk | Reason |
|-------------|-----------|--------|
| `Assets/**/*.cs` | +10 to +45 | C# varies from low to high risk |
| `Assets/**/*.asmdef` | +55 | Changes compile graph |
| `Assets/**/*.asmref` | +55 | Changes compile graph |
| `Assets/**/*.meta` | +80 | Contains GUID/import metadata |
| `Assets/**/*.unity` | +85 | Scene serialization |
| `Assets/**/*.prefab` | +85 | Prefab serialization |
| `Assets/**/*.asset` | +70 | ScriptableObject/settings |
| `Assets/**/*.controller` | +75 | Animator serialization |
| `Assets/**/*.anim` | +75 | Animation serialization |
| `ProjectSettings/**` | +80 | Global project behavior |
| `Packages/manifest.json` | +75 | Package versions |

### Semantic Unity Triggers

| Trigger | Risk Score | Example Tasks |
|---------|-----------|---------------|
| Serialized field rename | +70 | "Rename hitpoints to health" |
| MonoBehaviour lifecycle | +20 | "Add start delay to spawner" |
| Editor/runtime boundary | +25 | "Add custom inspector" |
| Resources/Addressables | +30 | "Change Resources.Load path" |
| Execution path tracing | +20 | "Fix popup route or controller reset path" |
| Data contract/payload | +30 | "Verify reward table localization and packet payload" |
| Assembly definition | +50 | "Change asmdef references" |
| Package/settings change | +45 | "Upgrade Input System" |
| Asset move | +50 | "Move prefabs to new folder" |
| YAML edit | +55 | "Edit prefab YAML" |

### Action Risk Modifiers

| Action | Risk | Examples |
|--------|------|----------|
| Fix/bug/typo | +5 | "Fix null check", "Fix typo" |
| Add/create/implement | +15 | "Add health bar", "Implement damage" |
| Refactor/restructure | +25 | "Refactor combat system" |
| Default | +10 | Any other task |

---

## Risk Modes

| Mode | Score Range | Plan Required | Guards Active | Verification |
|------|-------------|---------------|---------------|-------------|
| **Fast Patch** | 0-29 | No | Minimal | Static only |
| **Standard** | 30-59 | Short | Relevant rules | Compile/import |
| **Asset-Safe** | 60-79 | Required | Active | Compile + tests |
| **Migration** | 80-100 | Detailed | Full | All tiers |

### Mode Behaviors

**Fast Patch (0-29):**
- No planning required
- Minimal rule injection
- Quick C# edits only
- Static guards run
- Compile check if cheap/available

**Standard (30-59):**
- Short plan recommended
- Relevant Unity rules injected
- MonoBehaviour/UI/gameplay edits
- Compile/import check recommended
- Targeted tests if available

**Asset-Safe (60-79):**
- Plan required
- Protected-file guard active
- Prefab/scene references, asmdef edits
- Editor tools touching assets
- Verification required or explicit manual-check gap

**Migration (80-100):**
- Detailed migration plan required
- Full guardrails active
- Rollback strategy needed
- Strong evidence requirements
- Manual review checklist required

---

## Unity Guards

### Meta Guard

Ensures .meta files stay paired with assets and validates GUID continuity.

```python
# Checks performed:
- Asset added without matching .meta file -> hard_failure
- Asset deleted without deleting .meta -> warning
- .meta deleted without deleting asset -> warning
- .meta added without matching asset -> hard_failure
- GUID changed in .meta file -> hard_failure
- GUID removed from .meta file -> hard_failure
```

### YAML Guard

Blocks or warns on direct writes to protected Unity YAML artifacts.

**Protected extensions:** `.unity`, `.prefab`, `.asset`, `.controller`, `.anim`, `.overrideController`, `.playable`

| Mode | Behavior |
|------|----------|
| Fast Patch / Standard | `hard_failure` - Block |
| Asset-Safe / Migration | `warning` - Allow with caution |

### Serialization Guard

Detects serialized field renames and checks for `[FormerlySerializedAs]` migration attributes.

```python
# Detects:
- Public field renamed in MonoBehaviour/ScriptableObject
- [SerializeField] field renamed
- Field renamed without [FormerlySerializedAs]
- Field removed (possible data loss)
```

### Boundary Guard

Prevents UnityEditor references in runtime assemblies.

```python
# Detects:
- using UnityEditor outside Editor folder/asmdef
- Fully-qualified UnityEditor usage without #if UNITY_EDITOR
- [MenuItem], [ContextMenu], [CustomEditor], [InitializeOnLoad] in runtime code
- Runtime assembly referencing Editor assembly via asmdef
```

### Asmdef Guard

Detects assembly definition changes and their graph impact.

```python
# Checks:
- Runtime assembly referencing Editor assembly
- Platform include/exclude changes
- Define constraint changes
- Unsafe code enabled
- Auto-referenced changes
- Graph impact (direct + transitive references)
```

### Addressables Guard

Flags Resources/Addressables string-key path changes.

```python
# Detects:
- Resources.Load("...") path changed
- Addressables.LoadAssetAsync key changed
- Asset moved under/out of Resources folder
- Scene name/path changed in build settings
```

### Diff Guard

Orchestrator that runs all guards against the current git diff.

```python
# Runs:
1. Meta guard (git status for add/delete/move)
2. Meta guard (GUID continuity in diff)
3. YAML guard (protected file writes in diff)
4. Addressables guard (path changes in diff)
5. Boundary guard (Editor/runtime violations in changed .cs files)
6. Asmdef guard (assembly definition changes)
```

---

## Verification Tiers

| Tier | Name | Command | What it Proves |
|------|------|---------|---------------|
| 0 | Static | Guards only | No textual hazards |
| 1 | Compile | `Unity -batchmode -quit` | Scripts compile |
| 2 | EditMode | `Unity -runTests -testPlatform EditMode` | Editor logic works |
| 3 | PlayMode | `Unity -runTests -testPlatform PlayMode` | Runtime behavior works |
| 4 | Custom | `Unity -executeMethod HarnessChecks.RunAll` | Project invariants pass |
| 5 | Build | `Unity -buildTarget X` | Build pipeline works |
| M | Manual | Inspector/scene check | Visual verification |

### Verification by Mode

| Mode | Minimum | Recommended | Manual |
|------|---------|-------------|--------|
| Fast Patch | Static | Compile | Usually none |
| Standard | Static + compile | EditMode tests | PlayMode if lifecycle changed |
| Asset-Safe | Static + compile | EditMode + PlayMode | Required for asset changes |
| Migration | Static + compile + migration checks | EditMode + PlayMode + build | Required |

---

## Desktop and CLI Integrations

K-Unity-Yamae does not run remote model calls inside the harness. Codex and Claude stay
in their own desktop or CLI applications, while this harness supplies the
Unity-aware commands, risk checks, and guarded patch validation those apps can
invoke.

| Surface | Repo entrypoint | How it is used |
|---------|-----------------|----------------|
| Codex App | `.agents/skills/k-unity-yamae/SKILL.md` + `AGENTS.md` | Open the Unity project folder in Codex App. |
| Codex CLI | `.agents/skills/k-unity-yamae/SKILL.md` + `AGENTS.md` | Run `codex` from the Unity project root. |
| Claude Code Desktop | `.claude/skills/k-unity-yamae/SKILL.md` + `CLAUDE.md` | Open the project folder in the Code tab. |
| Claude CLI | `.claude/commands/kunity-yamae.md` + `.claude/skills/k-unity-yamae/SKILL.md` | Run `claude` from the project root and invoke `/k-unity-yamae`. |
| Local guarded handoff | `local-patch` | Validate unified diffs with Unity guards before applying. |

### Agent Configuration

The only executable harness backend is the local guarded patch handoff:

```yaml
agents:
  default: local-patch
  backends:
    local-patch:
      enabled: true
```

---

## Configuration

### Configuration Hierarchy

```
config/default.yml           (built-in defaults)
        ↓ overridden by
.unity-harness/config.yml    (project-specific)
        ↓ overridden by
--config <path>              (CLI override)
        ↓ overridden by
Environment variables        (${VAR} resolution)
```

### Project-Specific Configuration

Create `.unity-harness/config.yml` in your Unity project root:

```yaml
harness:
  default_mode: auto
  git_diff_timeout: 30

unity:
  executable: auto  # or full path to Unity
  allow_batchmode: true
  custom_validation_method: Company.Project.Editor.HarnessChecks.RunAll

risk:
  low_max: 29
  standard_max: 59
  asset_safe_max: 79
  migration_min: 80

verification:
  timeouts:
    compile: 300
    tests: 600
    build: 1800

agents:
  default: local-patch
  backends:
    local-patch:
      enabled: true
```

### All Configuration Keys

See `config/default.yml` for the complete configuration reference.

**Key sections:**
- `harness` - General harness settings
- `unity` - Unity project and executable settings
- `risk` - Risk score thresholds
- `protected_files` - File patterns to protect
- `file_risk_scores` - Risk scores per file pattern
- `verification` - Verification timeouts and behavior
- `serialization` - Serialization detection settings
- `context` - Context selection limits
- `scanner` - Scanner truncation limits
- `reporting` - Report generation settings
- `agents` - Agent backend configuration

---

## Project Structure

The README stays at the operator level. See `docs/ARCHITECTURE.md` for the full
module map.

| Area | Main modules |
| --- | --- |
| CLI surface | `cli.py`, `cli_run.py`, `cli_verify.py`, `cli_release_check.py` |
| Run workflow | `cli_run_payload.py`, `run_pipeline.py`, `cli_run_steps.py` |
| Unity verification | `verifier.py`, `unity_verification_contracts.py`, `unity_verification_plan.py`, `unity_verification_steps.py`, `unity_verification_support.py` |
| Unity project facts | `unity_profile.py`, `unity_profile_types.py`, `unity_profile_graphics.py`, `unity_profile_architecture.py`, `unity_profile_common.py` |
| Safety guards | `guards/`, `guarded_edits.py`, `risk.py`, `risk_checks.py` |
| Agent adapters | `agents/` |
| Tests and docs | `tests/`, `docs/` |

---

## Rule Cards

Rule cards are markdown files that provide Unity-specific guidance to AI agents. They are loaded and injected into agent prompts based on the task's risk triggers.

### Available Rule Cards

| Rule Card | File | When Injected |
|-----------|------|---------------|
| `unity.global` | `global_rules.md` | Always |
| `unity.serialized-field-rename` | `serialized_field_rename.md` | Field rename detected |
| `unity.meta-guid` | `meta_guid.md` | Asset move/delete detected |
| `unity.prefab-scene-yaml` | `prefab_scene_yaml.md` | YAML edit detected |
| `unity.asmdef` | `asmdef.md` | Assembly definition change |
| `unity.editor-runtime-boundary` | `editor_runtime_boundary.md` | Editor code in runtime |
| `unity.resources-addressables` | `resources_addressables.md` | Resources/Addressables change |

### Rule Card Content Example

**`serialized_field_rename.md`:**
```markdown
# unity.serialized-field-rename

**Trigger:**
- A public field in MonoBehaviour/ScriptableObject is renamed.
- A [SerializeField] or [SerializeReference] field is renamed.

**Required:**
- Add [FormerlySerializedAs("oldName")] on the new field.
- Report the old name, new name, declaring type.
- Run compile/import verification if Unity is available.

**Forbidden:**
- Do not manually rewrite scene/prefab YAML to force migration.
- Do not claim Inspector values are preserved unless a migration path exists.
```

---

## Evidence Ledger

The evidence ledger records all events during a task execution to a JSONL file.

### Event Types

| Event | Description |
|-------|-------------|
| `task_started` | Task begins with mode and risk report |
| `file_changed` | A file was modified with reason |
| `guard_result` | A guard check result |
| `verification_tier` | A verification check result |
| `manual_check` | A manual check requirement |
| `command` | A command was executed |
| `agent_output` | Agent produced output |
| `agent_error` | Agent encountered an error |
| `task_completed` | Task finished |

### Ledger File

Location: `.unity-harness/last-ledger.jsonl`

Each line is a JSON object:
```json
{"event": "task_started", "utc": "2026-06-11T12:00:00Z", "task": "Fix bug", "mode": "fast_patch", "risk_score": 15}
{"event": "file_changed", "path": "Assets/Game/DamageCalculator.cs", "reason": "null check fix"}
{"event": "guard_result", "guard": "meta_pair", "status": "pass", "details": "No issues"}
{"event": "verification_tier", "tier": "1", "name": "compile/import", "status": "passed"}
{"event": "task_completed", "status": "completed", "total_events": 5}
```

---

## Unity Editor Integration

### HarnessChecks.cs

The `Editor/HarnessChecks.cs` file provides project-specific validation that can be run via Unity's `-executeMethod` flag.

**Setup:**
1. For `kunity-yamae inspect --editor-probe --json`, no permanent copy is required; the probe is staged temporarily.
2. For custom project validation, copy `Editor/HarnessChecks.cs`, `Editor/EditorInspectionProbe.cs`, and `Editor/EditorInspectionJson.cs` to your Unity project's `Assets/Editor/` folder
3. Update the namespace to match your project
4. Configure in `.unity-harness/config.yml`:
   ```yaml
   unity:
     custom_validation_method: YourProject.Editor.HarnessChecks.RunAll
   ```

**What it checks:**
- Missing scripts in build scenes
- ScriptableObject loading validation
- Addressable key validation (stub)
- Editor inspection JSON for persistent listener targets, prefab override summaries, and missing serialized object references

**Running:**
```bash
kunity-yamae verify --custom-method YourProject.Editor.HarnessChecks.RunAll
kunity-yamae inspect --editor-probe --json
```

---

## Advanced Topics

Keep the README focused on setup and command usage. Detailed extension examples,
architecture notes, risk model rationale, and release checks live in:

- `docs/ARCHITECTURE.md`
- `docs/ANALYSIS.md`
- `docs/RELEASE_CHECKLIST.md`

---

## Inspired By

- **[Gajae-Code](https://github.com/Yeachan-Heo/gajae-code)**: Interview before guessing, plan before mutation, evidence-based completion, tmux-native execution
- **[LazyCodex](https://github.com/code-yeongyu/lazycodex)**: Project memory, verified loops, hooks, model routing, skill system
- **[Unity Documentation](https://docs.unity3d.com)**: Asset metadata, serialization rules, command-line automation, Test Framework

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/JayWuu-da/K-Unity-Yamae.git
cd K-Unity-Yamae
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
