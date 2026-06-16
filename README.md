# K-Unity-Yamae

**K-Unity-Yamae is an AI-agent Unity harness for Codex App/CLI and Claude Code Desktop/CLI on Windows.**

It is not a human-facing standalone Unity CLI. Its command surface exists so an AI agent can receive this repository's git URL, set up the harness, open a target Unity project, and run deterministic preflight, context, plan, guard, and verification commands from the current Unity project root.

The harness reports discovered facts and discovered files only. Static scan and context output are signals from the target project files; they do not prove Inspector object references, prefab override intent, persistent listener targets, PlayMode behavior, or build success. Those claims require `editor-probe`, Unity MCP, batchmode, PlayMode, or build evidence.

## Agent Bootstrap

A fresh Codex or Claude agent should use this flow after the user provides the git URL:

```powershell
git clone <K-Unity-Yamae git URL> K-Unity-Yamae
cd K-Unity-Yamae
python -m pip install -e .
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli providers doctor --json
```

Then the agent opens or changes directory to the target Unity project:

```powershell
cd <current Unity project root>
kunity-yamae init-agent --target both --write --json
kunity-yamae providers doctor --json
```

If the console script is not on PATH, use the module form from the harness checkout:

```powershell
python -m kunity_yamae.cli init-agent --target both --write --json
python -m kunity_yamae.cli providers doctor --json
```

`init-agent --write` refuses to overwrite existing agent guidance by default. When a target project already has `AGENTS.md`, `CLAUDE.md`, `.agents/skills/k-unity-yamae/SKILL.md`, `.claude/skills/k-unity-yamae/SKILL.md`, or `.claude/commands/kunity-yamae.md`, agents should inspect the dry-run output and merge intentionally instead of forcing overwrite.

## Agent Entrypoints

K-Unity-Yamae writes project-local guidance for the AI surfaces that actually consume it:

| Surface | Entrypoint | Agent behavior |
| --- | --- | --- |
| Codex App | `AGENTS.md` + `.agents/skills/k-unity-yamae/SKILL.md` | Open the Unity project folder in Codex App. |
| Codex CLI | `AGENTS.md` + `.agents/skills/k-unity-yamae/SKILL.md` | Run `codex` from the current Unity project root. |
| Claude Code Desktop | `CLAUDE.md` + `.claude/skills/k-unity-yamae/SKILL.md` | Open the Unity project folder in Claude Code Desktop. |
| Claude CLI | `CLAUDE.md` + `.claude/skills/k-unity-yamae/SKILL.md` + `.claude/commands/kunity-yamae.md` | Run `claude` from the project root; the slash command is compatibility around the primary skill. |

Git for Windows is recommended for Claude Code Desktop/CLI and Codex CLI sessions so shell and git-diff behavior are consistent in PowerShell.

## Agent Command Surface

These commands are deterministic primitives for the AI agent. They should be run from the current Unity project root unless the agent is testing a fixture with the root option.

```powershell
kunity-yamae providers doctor --json
kunity-yamae tools list --json
kunity-yamae tools list --schema v2 --json
kunity-yamae context --pretty "Fix prefab button raycast"
kunity-yamae risk --json "Fix prefab button raycast"
kunity-yamae run "Fix prefab button raycast" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "Fix prefab button raycast" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "Fix prefab button raycast" --execute-loop --schema v2 --verify-dry-run --json
kunity-yamae verify --dry-run --quality-gate --json
kunity-yamae inspect --json
kunity-yamae inspect --editor-probe --json
kunity-yamae install --codex --claude
```

For explicit project-path tests, put `--project` before the command:

```powershell
kunity-yamae --project <unity-project> init-agent --target both --dry-run --json
kunity-yamae --project <unity-project> run "Fix prefab button raycast" --plan-only --verify-dry-run --json
```

For model-produced edits, the agent should request a unified diff and route it through the guarded patch flow:

```powershell
kunity-yamae run "Fix prefab button raycast" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

## What Scan And Context Read

`scan`, `context`, `risk`, and `run --plan-only` inspect discovered project files such as:

- `ProjectSettings/ProjectVersion.txt`
- `Packages/manifest.json`
- `.asmdef` files
- C# scripts and test assemblies
- scenes, prefabs, and selected serialized text signals
- protected/generated paths
- UI, graphics, VFX, and architecture naming signals

The shared inventory is a repo-neutral list of discovered files, command/tool capabilities, and bounded generic semantic signals. It is suitable for planning and risk triage, but static scan and plan output do not prove Inspector object references, prefab override intent, persistent listener targets, PlayMode behavior, Game View state, or build success.

`tools --schema v2` and `orchestrate --execute-loop --schema v2` are explicit
agent-runtime surfaces. They add structured permissions, evidence tiers,
observability events, session memory artifacts, and Editor/Player adapter status
without making source or Unity asset changes. The Player adapter is disabled by
default, reports `unavailable`, and is reserved for explicit development-build
bridges only.

These are discovered static facts. Missing files, unrecognized project conventions, private runtime wiring, generated code that is not present, and Inspector-only relationships remain unknown until an agent runs the right Unity evidence tier.

Use `kunity-yamae inspect --editor-probe --json` when a claim depends on Inspector object graphs, prefab overrides, persistent listener targets, missing serialized references, or UI component state. Do not claim Unity Editor, PlayMode, Game View, build, or Inspector verification unless that tier actually ran and produced evidence.

## Unity Safety Model

The harness is intentionally conservative around Unity assets:

- `.meta` GUID continuity matters.
- `.unity`, `.prefab`, `.asset`, `.controller`, and `.anim` files contain serialized object graphs.
- Serialized field renames require migration care such as `[FormerlySerializedAs]`.
- Runtime assemblies must not depend on `UnityEditor`.
- Resources and Addressables use string keys that must be traced before edits.
- One writer agent should mutate a Unity project at a time; read-only analysis can run in parallel.

Risk mode selection is based on file risk, task semantics, and discovered facts:

| Mode | Typical work | Harness behavior |
| --- | --- | --- |
| Fast Patch | low-risk C# text edits | minimal static guard |
| Standard | ordinary Unity code fixes | context, rule cards, planned verification |
| Asset-Safe | prefab, scene, UI, resources, asmdef, package-sensitive work | stricter guards and manual checks |
| Migration | serialized field/class/asset rename or project-wide change | migration guidance and high verification demand |

## Architecture And Module Map

Deep implementation details live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Key modules:

- `cli_run_payload.py`
- `cli_run_steps.py`
- `unity_verification_plan.py`
- `unity_verification_steps.py`
- `unity_verification_support.py`
- `unity_profile_graphics.py`
- `unity_profile_common.py`
- `unity_profile_architecture.py`

## Release Checks

Maintainers and agents validating this repository should run:

```powershell
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```

`release-check --json` validates package data, desktop/CLI entrypoints, local-patch availability, and agent-facing copy contracts. It must stay free of model-backend credential setup language and must not treat scratch planning or evidence artifacts as tracked project files.

Harness-generated caches and reports must stay under `.unity-harness/cache/`, `.unity-harness/reports/`, or `.unity-harness/last-*`. Scratch planning/evidence artifacts such as `.omo/`, `.omx/`, `plans/`, and `evidence/` are local work receipts and must not become tracked project artifacts.

## License

MIT License.
