# Unity Mobile Harness Extension

This extension keeps K-Unity-Yamae's existing risk, context, guarded patch, and Unity verification contracts, and adds a mobile-game-specific decision layer.

## Goal

Use the strongest model only when the task needs architectural, integration, native-build, monetization, identity, privacy, or recovery reasoning. Deterministic inspection should consume no model tokens, while bounded low-risk changes can be delegated to a cheaper worker.

## Execution lanes

| Lane | Typical work | Rule |
| --- | --- | --- |
| `local` | package/version inspection, deterministic scans | no model call |
| `worker` | bounded low-risk code/UI change with explicit acceptance criteria | narrow context, guarded patch only |
| `architect` | IAP, Firebase Auth/linking, AdMob/UMP, native build/crash, migration | installed SDK evidence first |
| `reviewer` | moderate-risk worker output | review before application |
| `human` | repeated failures or blocked automation | stop automatic retry |

`harness.mobile.route` is advisory and never grants write permission. Existing patch guards and Unity verification remain authoritative.

## Knowledge cards

`harness.mobile.knowledge` performs deterministic local retrieval from `kunity_yamae/data/mobile_packs.json`. Each card contains version scope, review date, official/source URLs, source facts, and local safety policy.

Initial coverage:

- UniTask / coroutine lifecycle
- Google Mobile Ads / UMP / rewarded ads
- Unity IAP v5
- Firebase Auth, Google sign-in, Apple sign-in, account linking
- Android/iOS native dependency, IL2CPP, Gradle/Xcode crash/build diagnostics

Knowledge cards are guidance, not API compatibility certification. Installed package versions and native dependency graphs must be observed before SDK code is proposed.

## Tool calls

```text
harness.mobile.route
  input: {"task": "Fix IAP v5 transaction logging", "failure_count": 0}

harness.mobile.knowledge
  input: {"query": "Firebase Apple login account linking", "top_k": 4}
```

Expected routing examples:

- `Read manifest and inspect package versions` -> `local` when Unity risk is low.
- `Fix one UI label typo` -> `worker` when risk is bounded.
- `Fix IAP v5 transaction logging` -> `architect` regardless of a small textual diff.
- `Change AdMob rewarded callback` -> `architect`.
- Two failed automatic attempts -> `human`.

## Next integration step

The next change should feed `harness.mobile.route` and `harness.mobile.knowledge` into orchestration planning without weakening the existing orchestration schema. Model IDs must remain configuration, not hard-coded policy. Token/cost measurements should be recorded from the provider execution layer rather than estimated from role names.
