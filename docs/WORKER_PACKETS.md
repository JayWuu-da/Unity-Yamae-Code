# Bounded worker packets

Choose one preparation path. Use this path when the parent agent already knows the target
files/ranges. Use existing context/risk/orchestration discovery for unknown scope instead of
running all preparation paths in sequence. This command invokes neither Unity nor a model.

## Code work order

Example paths below are illustrative: replace them with observed project paths and exact line
numbers. Store local work orders in `.unity-harness/cache/`, not tracked project source.

```json
{
  "kind": "code_patch",
  "task": "Fix the indicated label text without changing behavior",
  "write_paths": ["Assets/Scripts/HudCaption.cs"],
  "slices": [
    {"path": "Assets/Scripts/HudCaption.cs", "start": 70, "end": 95}
  ],
  "acceptance": ["Only the requested text changes", "Unity compile and focused UI check pass"],
  "package_ids": [],
  "failure_count": 0
}
```

From the target Unity project:

```powershell
kunity-yamae worker-pack --request-file .unity-harness/cache/task.json --json
# Only for a prepared code packet; emit the prompt once, without the metadata envelope:
kunity-yamae worker-pack --request-file .unity-harness/cache/task.json --prompt-only
```

`harness.worker.prepare` in the existing tool registry accepts the same object. Do not send both
the JSON envelope and the rendered prompt to a worker. Do not invoke the command twice merely
to obtain both forms; a caller can render an already prepared packet with `render_worker_prompt`.

| Status | Meaning | Caller action |
| --- | --- | --- |
| `prepared` | Bounded code/async proposal context is available | Send only the rendered prompt to a configured worker if generation is necessary. |
| `planned_local` | Fully specified prefab/UI operation was planned without an LLM | No worker call; obtain live adapter validation and review. |
| `needs_context` | Required input absent, invalid or over budget | Provide the specific missing facts or split the work. |
| `escalated` | Sensitive scope/risk or failed attempts | Architect review or human stop; no automatic same-worker retry. |
| `invalid_request` | CLI input could not be parsed/validated | Correct the work-order schema. |

Exit codes: 0 for prepared/planned-local JSON; 2 for invalid input; 3 for missing/escalated work
or a prompt-only request that cannot supply a worker prompt. A success exit is not evidence of
Unity execution. `model_called`, `applied` and `unity_verified` remain false.

## Async recipe

Set `kind` to `async_patch` and `lifetime` to `destroy`, `disable`, `pool` or `session`.
Include installed API signatures and relevant callers in the source ranges. A package listed in
`package_ids` needs a resolved package-lock version or a `Packages/<id>/...` source excerpt.
Imported DLL SDKs without those facts need further inspection; a matching name is not proof.

## Prefab and UI work orders

These produce deterministic **proposals**, not mutations. Set exactly one existing `.prefab`
or `.unity` write path. An existing `unity-harness.editor-inspection.v1` report must contain
facts for that asset at `.unity-harness/reports/editor-inspection.json`. Target asset/meta
and UI template/meta files must be present. Report freshness and complete identity remain unknown.

For `prefab_bind`, supply an `object_contract` with `source_hierarchy`, `source_component`,
`property_path`, `target_hierarchy`, `target_component` and `expected_old_value` (null or an
observed identity). The resulting operation is `bind_reference`; no model is called.

For `ui_create`, supply `ui_system` (`ugui` or `uitoolkit`), `template_asset` (existing prefab or
UXML), `parent_hierarchy`, `layout_contract` and `target_resolutions`. The resulting operation is
`instantiate_template`. A caller must not infer fonts, art direction, scene ownership or identity
from a filename. UI Toolkit template instantiation still needs a future compatible live adapter.

## Limits and integration

Config key `efficiency.max_prompt_bytes` defaults to 16000 (UTF-8 bytes). Source reads are limited
to 1 MB/file, 8 ranges/request and 160 lines/range; code edits allow at most 4 target files.
Required content is never truncated to fit. Traversal/symlink reads and raw Unity YAML ranges
are rejected. The library helper `check_packet_freshness` rechecks observed hashes; callers must
invoke it immediately before guarded application. This PR does not add that application hook.

The old guarded-patch and live-verification paths are retained. There is no automatic Codex
spawn, model selection, Editor write, SDK initialization or screenshot capture in this path.
See `EFFICIENCY_RESEARCH.md` for the research, limitations and actual-model evaluation design.
