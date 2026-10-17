# Dataset 578: cache reuse report

Read-only production export analysed locally. No workflow reruns or model calls.
Exported 2026-10-17 12:11:05.240642+00:00. Times below use Africa/Johannesburg (UTC+02:00).

**190 calls; $5.017632 recorded cost.** Input cost: ordinary $0.7511, cache reads $0.3536, cache writes **$3.1178**. Output $0.7951. Component totals differ from recorded totals only by per-call rounding.

## Main findings

- **Repeated flat reuse is the main signal.** In Pre-publication quality gate, 68 of 68 calls after the first gpt-6-sol call read exactly 21,981 cached tokens. That stage alone spent $1.9320 on cache writes.
- There are 4 drops of at least 5,000 cached tokens. Only 1 occurs without a model switch or a long gap. See the separate drop table below.
- The immediate next investigation is why cached reuse does not grow with the conversation in the quality gate. Existing records locate the symptom but cannot identify the changing prompt section or quantify avoidable spend.

### Example quality-gate sequence

These calls use the same model and opening fingerprint. Reads stay flat while write volume grows and falls.

| Usage ID | Time (SAST) | Input | Cache read | Cache write |
|---|---|---:|---:|---:|
| 2758 | 2026-10-06T16:51:50+02:00 | 33,190 | 21,981 | 8,845 |
| 2791 | 2026-10-06T17:04:21+02:00 | 45,502 | 21,981 | 18,756 |
| 2826 | 2026-10-06T17:24:22+02:00 | 51,196 | 21,981 | 23,764 |

## By workflow stage

Read/write shares are token-weighted percentages of input. Flat-read calls reuse exactly the same token count as the preceding comparable call while writing at least 5,000 tokens. They are indicators, not proven wasted spend.

| Stage | Calls | Read % | Write % | Write cost | Total cost | Flat-read calls |
|---|---:|---:|---:|---:|---:|---:|
| Data structure exploration | 4 | 56.0 | 40.6 | $0.0019 | $0.0036 | 0 |
| Data content exploration | 10 | 59.1 | 33.9 | $0.0441 | $0.0736 | 1 |
| Data suitability assessment | 1 | 0.0 | 100.0 | $0.0010 | $0.0011 | 0 |
| Data transformation | 31 | 50.7 | 33.3 | $0.3028 | $0.5741 | 24 |
| Data validation and refinement | 19 | 53.3 | 31.7 | $0.2194 | $0.3990 | 12 |
| Publication package preparation | 25 | 56.0 | 29.6 | $0.3170 | $0.5902 | 20 |
| Pre-publication quality gate | 70 | 43.9 | 46.8 | $1.9320 | $2.8426 | 66 |
| Final Review & Publication | 3 | 18.7 | 67.7 | $0.0075 | $0.0095 | 0 |
| Data maintenance | 27 | 70.4 | 20.9 | $0.2921 | $0.5240 | 16 |

## Repeated cache-read boundaries

| Stage / model | Calls after first with same fingerprint/model | Most common read boundary | Calls at that boundary |
|---|---:|---:|---:|
| Data structure exploration / gpt-6-luna (agent 2348) | 3 | 7,090 | 3 |
| Data content exploration / gpt-6-sol (agent 2349) | 9 | 6,828 | 9 |
| Data transformation / gpt-6-sol (agent 2351) | 30 | 12,301 | 30 |
| Data validation and refinement / gpt-6-sol (agent 2352) | 17 | 20,182 | 17 |
| Publication package preparation / gpt-6-sol (agent 2353) | 24 | 19,543 | 23 |
| Pre-publication quality gate / gpt-6-sol (agent 2354) | 68 | 21,981 | 68 |
| Data maintenance / gpt-6-sol (agent 2375) | 8 | 31,329 | 8 |
| Data maintenance / gpt-6-sol (agent 2375) | 17 | 31,438 | 17 |

## Large drops in cache reads

Threshold: 5,000 fewer cached tokens than the previous call for the same agent. Model switches and long gaps are shown separately from unexplained drops.

| Usage ID | Time (SAST) | Stage | Read drop | Current read / write | Approx. gap | Context |
|---|---|---|---:|---:|---:|---|
| 3154 | 2026-10-15T13:16:52+02:00 | Data maintenance | 31,329 | 0 / 36,471 | 158927.1 s | opening fingerprint changed; gap >=30 minutes; expiry plausible; read drop >=5000 tokens |
| 2820 | 2026-10-06T17:21:25+02:00 | Pre-publication quality gate | 21,981 | 0 / 53,061 | 61.4 s | model switch; opening fingerprint changed; read drop >=5000 tokens |
| 2725 | 2026-10-06T16:44:09+02:00 | Data validation and refinement | 20,182 | 0 / 31,658 | 122.3 s | model switch; opening fingerprint changed; read drop >=5000 tokens |
| 2741 | 2026-10-06T16:48:26+02:00 | Publication package preparation | 9,671 | 19,543 / 11,243 | 0.3 s | read drop >=5000 tokens; unexplained short-gap drop |

## Limits of this measurement

Provider diagnostic types: {'missing': 12, 'unavailable': 171, 'cache_hit': 6, 'comparison_response_not_found': 1}. Nonempty diagnostics frequently say unavailable; their presence does not establish a cause.
The stored opening fingerprint includes model, reasoning effort, temperature, tools and opening instructions. It does not hash the rendered conversation history. Identical fingerprints therefore do not prove identical cached content or a particular cache breakpoint.
Equal cached-token counts suggest a stable reuse boundary; these records cannot establish which prompt section ends at that boundary, or whether writes contain previously seen tokens. New history, compaction, changed user evidence, cache expiry and provider behaviour remain possible explanations.
Gap estimates subtract recorded model duration from the next usage timestamp. They are approximate. User/upload counts use metadata only and do not establish the full semantic dependencies of a change.
No dollar amount is labelled avoidable without a controlled comparison. Short gaps under 30 minutes are an investigation heuristic, not evidence that the cache must still exist.

## Reproduce locally

Run this script in Docker against the retained metadata-only export. The script makes no network or database calls. Raw dataset values, user message text, filenames and model prompts are excluded from the export.

The full call sequence is in [dataset-578-timeline.csv](dataset-578-timeline.csv).
