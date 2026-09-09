# Unity worker efficiency: research and implementation

Research date: 2026-09-09. Scope: Unity-Yamae-Code, not a replacement harness.

## Objective and evidence boundary

Optimize **verified tasks per total spend and elapsed time**, including discovery, planning,
worker attempts, retries, tools, review and Unity verification. Short replies alone are not the
objective. Unity-specific capability of any named model remains unmeasured in this repository.
No paid inference, Codex subagent execution, Unity Editor or device test was run for this change.

The implementation adds a bounded preparation path and deterministic operation proposals.
It does not implement a new model backend, automatic Editor writes or a claim of lower real-world
model costs. Existing guarded patches and evidence tiers remain authoritative.

## External findings and resulting decisions

| Primary evidence | Finding supported by the source | Yamae design decision (not a measured model result) |
| --- | --- | --- |
| OpenAI latency guide [1] | Output length, request count and model choice affect latency; small models can need detailed prompts or examples. | Remove narration and repeated discovery, not required Unity facts; use local code for fixed operations. |
| Astra model guidance [2] | Skills/AGENTS instructions, detailed writing, delegation and overly broad testing merit task-specific calibration. | Keep a small worker contract, choose one preparation path and run appropriate checks rather than every command on every edit. |
| Astra model page [3] | Reasoning effort has model-specific supported values; cache writes have their own price. | Do not invent parameter support or infer spend from a role label; keep rates external. |
| Codex subagent documentation [4] | Parallel agents have separate work/context overhead and can increase tokens. | No mandatory subagent per task; parallelize independent reads, keep one writer. |
| Repository context experiment [5] | Additional context/instructions can increase cost and reduce success in the studied setup. | Do not copy every SDK guide into every prompt. |
| Repository context experiment [6] | A different empirical setup found efficiency improvements with AGENTS.md. | Context is neither universally beneficial nor harmful; compare task classes and retain useful project constraints. |
| Unity serialization/prefab APIs [7,8] | Unity provides structured Editor APIs for serialized data and prefab contents. | Prefer typed operation proposals and a live adapter over textual YAML rewrites. |
| UGUI layout guidance [9] | Resolution, anchors and scaling are explicit layout concerns. | Require an observed UI template, chosen UI system and target resolutions. |
| Reasoning guidance [10] | Direct goals and constraints are preferable to forced reasoning transcripts. | Ask for a patch/proposal or precise missing facts, not a narrated chain of thought. |

These publications use different agents, repositories and metrics. Neither AGENTS.md study
establishes an Astra/Unity performance effect. The experiments are research, not a universal
configuration recipe. Official documentation was checked online; the current Astra guidance
was visible in the fresh search-index result while an opened cached copy of the same guide
still showed an older model section. Only specifically retrieved Astra statements are used.

## Astra-specific adaptation

Public documentation supports treating Astra as a candidate for difficult integration,
architecture and cross-file decisions, but does not establish its accuracy on this project's
prefab graph, monetization lifecycle or native mobile builds. Its documented sensitivity to
instructions motivates auditing generated entrypoints, not assuming internal self-knowledge.

The harness now avoids suggesting all preparation commands are a checklist. Harness Python
tests belong to edits of this repository; they are not a prerequisite for every target Unity
change. Completion prose defaults to changed paths, actual checks and blockers. Worker outputs
are diffs or operation proposals, without a repeated tutorial. This is a prompt convention,
not a hard output-token cap, and does not bound hidden reasoning tokens.

Astra's supported effort values start at `low`, not `none` [3]. This change does not silently
change a user's chosen model, reasoning effort or Codex configuration. Native subagent model
selection and Responses API options require an explicit, separately tested adapter.

## Implemented work paths

### 1. Explicit source work order

`worker-pack` reads one work order and the exact supplied source ranges. It does not crawl the
repository, invoke an LLM, spawn agents, rewrite assets or fetch documentation online.
A parent agent must first establish scope; that discovery overhead still counts in a real eval.

Required facts: task, recipe, write paths, acceptance criteria and source ranges for code edits.
Async work additionally needs lifetime ownership. Selected SDKs require a resolved lock version
or an installed source excerpt; git/package URLs are not passed through as version strings.
Observed manifest declarations and lock resolutions are kept distinct.

The stable prefix contains general scope/evidence rules. The variable payload contains the
current task, hashes, exact code, selected guidance and required checks. No parent transcript,
full tool catalog, full repository or unconditional SDK encyclopedia is copied in.

The 16,000-byte default is an **UTF-8 byte budget, not a model-token limit**. If critical context
cannot fit, return `needs_context` rather than truncate a method, acceptance rule or guard.
This gate cannot prove that a planner selected all semantically necessary callers; the worker
must request missing contracts rather than invent them.

### 2. Deterministic prefab/UI proposal

When an asset operation is fully specified, `planned_local` contains `bind_reference` or
`instantiate_template`. There is **no worker prompt and no model call**. UI plans require the
existing template, UI system, parent, layout contract and target resolutions.

The existing Editor inspection report is filtered to the selected asset. It is not a complete
object graph and has no guaranteed current identity, so the plan explicitly records those
limits. Before applying, a future live adapter must resolve unique objects and components,
check types and expected old values, honor Undo/prefab semantics, save/reload and run the
relevant interaction/visual checks. This adapter is not implemented in this change.

The deterministic proposal does not prove the chosen objects match the user's intent. An
ambiguous desired design still requires a planner or user decision; no fake default target is
invented. No direct Unity YAML or .meta modification is permitted.

### 3. Freshness and failure handling

`check_packet_freshness` hashes all read source files and metadata, including missing metadata
so that later file creation invalidates the preparation. Prefab/template metadata and the
Editor report are included where used. This is a callable precondition helper, not an automatic
patch-application hook. A hash match does not prove live Editor identity or runtime behavior.

File reads reject traversal, noncanonical paths and symlinks, and have size/range limits. These
checks are not an OS sandbox or a guarantee against a hostile concurrent filesystem mutation.

A first failed worker attempt escalates to architect; a second stops at human. Keyword-based
routing remains advisory, not a calibrated capability classifier. Word boundaries avoid
accidentally matching `ump` inside `jump`. Missing facts are not successful verification.

### 4. Local host speed

The shared inventory previously traversed generated directories with `rglob` and filtered
afterwards. It now prunes those directories before descent and skips symlinks. Matching fallback
source selection respects file/count limits and avoids an unnecessary inventory collection when
context already has candidates. The mobile routing handler no longer scans a project whose
profile the current risk classifier does not use.

### 5. Usage accounting

`worker_metrics.py` accepts normalized observed counters. It does not collect provider usage.
Input totals include cache reads/writes; output totals include reasoning, so reasoning must not
be charged twice. Unknown counters or required prices yield unknown cost, never zero.
Failed attempts count toward cost per verified task. Per-attempt p50/p95 are not advertised as
end-to-end task latency. API cost equivalents are not a ChatGPT subscription bill.

The fixed prefix is cache-friendly structure, not an implemented cache policy or a guaranteed
hit. Cache behavior and write charges depend on the model/API [3,11]. Do not pad prompts to get
a cache threshold or pay to cache constantly changing suffixes without a measured benefit.

## Repeatable evaluation

Run the local fixture benchmark:

```powershell
python -m kunity_yamae.efficiency_benchmark
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```

The benchmark compares the same task, policies, acceptance criteria and hashes with a full
600-line synthetic source versus an explicit 8-line range. It separately checks whether the
old first-50-lines preview contains the edit target. It reports bytes, not model-token savings.
It also compares generated-directory traversal over 1,000 synthetic generated files and checks
that the resulting inventory is identical. Timing is a warm local-filesystem median only.

### Required model/Unity eval before a savings claim

Use isolated copies of the same pinned Unity project and work orders for four conditions:
(1) existing harness, (2) concise-output instruction only, (3) bounded packets/recipes,
(4) bounded packets plus measured model routing. Keep model snapshot, tools, validation and
completion criteria fixed within each comparison. Include discovery and planner overhead.

Cover surgical C# edits, async cancellation/pool reuse, ordinary/nested/variant prefab cases,
UGUI/UI Toolkit layouts, API-version mismatch, and ambiguous/missing evidence. Include both
success and refusal/clarification cases. Do not force real purchases, live ads or login flows
in an automated benchmark; use approved test fixtures and environments.

Collect total and cached input, cache writes, output/reasoning, every failed attempt, tool calls,
review time, total task wall time, verification tier, out-of-scope edits and first-pass success.
Measure at least several repeated runs per condition and report uncertainty and task breakdown.
A smaller packet that loses correctness is a regression. Promotion requires unchanged safety
and success criteria plus evidence of lower total cost or end-to-end latency. No numerical
performance threshold is claimed as achieved by the current fixture tests.

## References

[1] OpenAI, Latency optimization: https://developers.openai.com/api/docs/guides/latency-optimization

[2] OpenAI, Model guidance / Using GPT-6 Astra: https://developers.openai.com/api/docs/guides/latest-model

[3] OpenAI, GPT-6 Astra model: https://developers.openai.com/api/docs/models/gpt-6-astra

[4] OpenAI, Codex subagents: https://developers.openai.com/codex/subagents/

[5] Gloaguen et al., Evaluating AGENTS.md (2026): https://arxiv.org/abs/2602.11988

[6] Lulla et al., On the Impact of AGENTS.md (2026): https://arxiv.org/abs/2601.20404

[7] Unity, SerializedObject: https://docs.unity3d.com/6000.0/Documentation/ScriptReference/SerializedObject.html

[8] Unity, LoadPrefabContents: https://docs.unity3d.com/6000.0/Documentation/ScriptReference/PrefabUtility.LoadPrefabContents.html

[9] Unity, Designing UI for multiple resolutions: https://docs.unity3d.com/Packages/com.unity.ugui@2.0/manual/HOWTO-UIMultiResolution.html

[10] OpenAI, Reasoning best practices: https://developers.openai.com/api/docs/guides/reasoning-best-practices

[11] OpenAI, Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
