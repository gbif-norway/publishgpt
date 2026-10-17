# Cache history investigation, 17 October 2026

Found two interacting problems in the request builder. Claude Opus 5.5 independently reviewed the diagnosis and then reviewed the local patch. A fix is prepared in the shared checkout; it has not been deployed.

## Why reuse stayed flat

1. Each request marked the opening prompt and the newest history item, rebuilding both markers from scratch. The next request removed the old history marker. In explicit-only mode, OpenAI looks for cache matches at the marked endpoints in the current request. An unchanged prefix alone is insufficient when its saved endpoint is no longer a lookup candidate. This follows the documented [prefix matching rules](https://developers.openai.com/api/docs/guides/prompt-caching#how-prefix-matching-works).
2. Retaining just the previous newest marker would still be insufficient. When a tool turn leaves the two-turn full-detail window, its large arguments or output become compacted. That changes content before the previous newest endpoint, invalidating that prefix. Earlier tests checked unchanged content but did not check whether matching cache endpoints were eligible.

This explains the structural failure reproduced locally and is consistent with dataset 578's repeated 21,981-token quality-gate reads. Historical usage records do not prove the exact token boundary or quantify avoidable spend.

## Local change

The history renderer identifies the end of the previous and current compacted regions. The request builder marks those endpoints, the fixed opening, and the latest eligible history item, using at most four breakpoints. The previous compacted endpoint remains eligible on the following request; the current one becomes the next reusable checkpoint.

Short user-only histories retain the previous endpoint and the newest one without filling every spare cache slot. Text history uses a consistent wire representation. Attachment parts are copied before marking; files and images remain unchanged. The mutable per-turn state remains outside all cache breakpoints.

Conversation text, compaction limits, eight-turn history trimming, task/model assignments, effort, and workflow validation are preserved. No database migration is required. Existing conversations may get a one-time cache miss after the wire-format change.

## Verification

The local regression uses the real history renderer and request builder with model calls mocked. A small fake cache compares exact request prefixes with only cache annotations removed; it preserves string/list distinctions. It implements the documented endpoint-selection rule, not the provider's tokenizer, routing, storage or billing.

Across 26 synthetic turns, the old marker selection never reuses history beyond the opening. The new selection reuses history on ordinary turns after startup, with expected misses when the retained history is trimmed at turns 17 and 25. First compaction can also cause an initial miss. This comparison isolates endpoint selection using consistent serialization, not historical provider responses.

All **82 targeted tests passed**. Coverage includes large and small results, parallel and missing/out-of-order tool replies, source replacement and recovery, appended user messages, both PDF attachment paths, mutation prevention, the four-marker limit, exclusion of dynamic state, and older-model compatibility. The suite also includes the existing schema/history, usage accounting, request adapter and workflow tests.

Claude's final review highlighted test normalization hiding string/list changes and possible mutation of hydrated attachment parts. Both were addressed. Additional regressions cover PDF attachment index stability and older-model string representations.

## What remains to measure

No OpenAI inference calls, production mutations or dataset reruns were made for this investigation. The regression establishes request structure, not a measured dollar saving. After the user's next deployment, use the existing usage report to compare cached reads, cache writes and total input cost on new runs. Cache reads should extend beyond the opening between intentional history resets; actual provider behaviour and net savings still need observation.

See the [original dataset 578 report](dataset-578.md) and [per-call timeline](dataset-578-timeline.csv) for the historical evidence.
