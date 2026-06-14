# K-Unity-Yamae Current Analysis

**Date:** June 11, 2026

K-Unity-Yamae is an AI-agent Unity harness for Codex App/CLI and Claude Code Desktop/CLI on Windows. It keeps the agent loop light by doing fast static project discovery from the target Unity project root first, then escalating only when Unity-specific risk appears.

## Implemented Surface

| Area | Current capability |
| --- | --- |
| Project scan | Discovered static facts: Unity version, packages, assemblies, scenes, tests, protected/generated paths |
| Unity facts | UI system signals, prefab wiring hints, graphics importer settings, platform texture overrides, architecture naming patterns |
| Risk model | Fast Patch, Standard, Asset-Safe, Migration modes with rule-card selection |
| Agent integration | Codex App/CLI and Claude Code Desktop/CLI entrypoints plus offline `local-patch` handoff |
| Guarded edits | Unified diff evaluation in a detached git worktree before optional apply |
| Editor probe | Batchmode source for inspector listeners, missing references, prefab overrides, UI component state |
| Verification | Static guards, Unity command planning, Editor probe stage, dry-run reporting |
| Reporting | Evidence ledger, guard reports, release check JSON |

## Unity Focus

The harness is intentionally biased toward production Unity risks:

- `.meta` and GUID continuity
- `.unity`, `.prefab`, `.asset`, `.controller`, `.anim` serialized artifact safety
- `[SerializeField]` rename detection and migration prompts
- runtime versus `UnityEditor` boundary checks
- asmdef dependency impact
- UI prefab wiring, EventSystem/GraphicRaycaster/CanvasGroup signals
- texture, sprite, audio, and model importer settings for mobile and PC decisions
- MVP/MVC/controller/manager/service naming signals without overclaiming ownership

## Current Limits

Editor-level object graph facts require Unity batchmode execution. Static YAML/text inspection is useful for triage, but it cannot fully prove Inspector object references, prefab override intent, or persistent listener target validity. Those claims are only valid when the Editor probe report exists.

Static scan and context output are discovered facts and signals only. Missing project files, generated code, private runtime wiring, and project-specific conventions must be reported as unknown until the agent obtains stronger Unity evidence.

Mutation remains intentionally conservative. Model-produced or pasted unified diffs should use `run --guarded-agent-patch`, which routes the patch through guard evaluation before applying.

## Quality Gates

Release readiness is checked with:

```bash
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```
