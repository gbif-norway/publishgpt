# Cost review, 17 October 2026

Independent review by Claude Opus 5.5, requested by the project owner. The reviewer received an architecture summary, existing and pending controls, and dataset 578 telemetry. It did not inspect source code or production directly. Suggestions below are proposals, not implemented changes or measured savings.

## Notes on the review

- The review applies Sol prices to combined Sol/Luna totals in its preliminary decomposition. Recorded per-model accounting remains authoritative. Cache-write spend was approximately $3.12, not $3.31: 2,477,436 Sol Flex write tokens at $1.25/M plus 168,210 Luna Standard write tokens at $0.125/M.
- Repeated cache writes alone do not prove waste. Diagnose cache expiry, history compaction, user/source changes, and stage transitions before changing cache boundaries.
- The paused duplicate mappings are a validation finding during reconciliation, not sufficient evidence by themselves that maintenance is non-idempotent.
- Checks must include their full semantic dependencies before prior findings can safely be reused. Changed data can invalidate conclusions about unchanged rows.
- A fresh generated package needs validated stable identity and source coverage; preserve the current valid package until its replacement passes checks.
- Deterministic projection is appropriate only after mapping and supported loss handling are explicit. Semantic mapping must remain evidence-based.
- No further Luna task migration is authorized. Current pending changes keep task assignments, use GPT-6.1 Sol Flex and Luna Flex, and raise the dataset ceiling to $7.

## Reviewer response

# Architecture Review: ChatIPT Cost Savings (Dataset 578)

## Known facts (from your evidence)

- **The quality gate is the dominant cost.** It used USD 2.84 of 5.02 (57%) across 69 calls. The next four stages together cost about USD 2.08.
- **Model upgrades help little.** The 6.1 upgrade and the Luna Flex move together save about USD 0.19 (≈3.8%).
- **Output is a minor cost.** All output, including reasoning, was 163k tokens, roughly USD 0.82 at Sol output price. Most spend is input context.
- **Average call size is large.** Each call averaged about 36.8k input tokens: ≈18.8k cached-read, ≈13.9k cache-write and ≈4.1k uncached (if cached and write tokens are subsets of input).
- **The run ended in a broken state.** Maintenance hit the ceiling with duplicate old/new event and occurrence mappings still present.

## Challenges to your assumptions

**1. Cache writes, not model choice, appear to be the main lever (hypothesis).**
- At Sol 6 prices, 2.65M write tokens cost about USD 3.31, which is most of the bill.
- My decomposition gives ≈USD 5.26, not 5.02. Verify how your usage fields nest before relying on this.
- If it holds, each written token was read only about 1.35 times on average. That suggests frequent prefix churn.
- The 6.1 upgrade only cuts the read price (USD 0.177 ≈ 3.57M × 0.05). It does nothing for write cost.
- Converting a churned write into a read saves about USD 1.20/M, which is far more than any model swap.

**2. Compaction that drops batches of 8 may itself cause churn (hypothesis).**
- Removing earlier history invalidates everything after the removal point.
- The whole remaining tail is then rewritten at the write price.
- Stage hand-overs that change the system prompt or tool set would do the same.

**3. Reasoning effort is probably a secondary cost.**
- Raising the gate to xhigh mainly risks more turns, not more reasoning tokens per turn.
- Measure turns per gate run, not just reasoning tokens.

**4. "Checks rerun only for changed packages" applies to deterministic checks.**
- The 69 gate calls suggest the model-level review is not equally scoped to what changed.

**5. Raising the ceiling treats the symptom.**
- The final state shows non-idempotent maintenance (duplicated mappings), not just budget exhaustion.

## Recommendations, ranked by expected savings ÷ risk

### 1. Make the cache prefix stable and stop writing orphan prefixes
**Expected savings:** highest. **Quality risk:** none, because the content is identical.

- Order the prompt as:
  1. Stable shared tools and schema
  2. Common instructions
  3. Stage-specific instructions
  4. Append-only history
  5. Dynamic state
- Keep tool definitions identical across stages where possible. Mark unavailable tools in instructions instead of removing them.
- Compact only at stage boundaries, where the prefix breaks anyway.
- Alternatively, append a summary and let old turns expire at the next boundary, rather than deleting mid-stage.
- Don't put a tail breakpoint on calls unlikely to be followed in the same thread within the cache lifetime. Examples are terminal turns, stage transitions and final approval.

**Measure:**
- Write:read ratio per stage.
- Write tokens per call.
- "Orphan writes": prefix hashes written but never read.
- Write spikes aligned with compaction events and stage changes.

### 2. Restructure the quality gate into scoped, ledger-backed checks
**Expected savings:** high. **Risk:** low to medium.

- Replace the single long agent loop with a fixed checklist. Example check areas: event identity/joins, dates, taxonomy, occurrence status, coverage/omissions, geography, EML.
- Each check runs with a fresh minimal context: the deterministic report, the relevant artifact slice and prior findings for that check.
- Persist findings in a ledger keyed by the hashes of each check's inputs.
- On re-entry, rerun only checks whose input hashes changed. Carry forward accepted findings verbatim.
- Keep xhigh only for checks where semantic error is harmful. Don't reduce scrutiny; reduce re-reading.

**Measure:**
- Calls and input tokens per gate run.
- Gate runs per package hash.
- Share of checks rerun with unchanged inputs (target: zero).
- Recall regression: replay dataset 578's known defects (country-coordinate conflicts, abundance-as-date corruption, incomplete metadata) through the new gate and confirm every one is still caught.

### 3. Run maintenance as a deterministic diff plus idempotent replay
**Expected savings:** medium to high. **Quality gain:** likely.

- Before any model call, compute a row-level source diff keyed by source IDs or row hashes: unchanged, modified, added, removed.
  - For 2426 → 2389 rows, at least 37 net removals.
- Store the transformation as a replayable mapping specification.
- Regenerate DwC-DP from scratch on the new source rather than editing in place. That structurally prevents old/new duplicate mappings.
- The model reviews only the diff, schema-affecting changes and new ambiguities.

**Measure:**
- Maintenance calls per revision.
- Duplicate-ID count after replay (must be 0).
- Gate checks invalidated per revision.

### 4. Fingerprint every call to separate necessary rework from loops
This directly answers your rework-versus-loop question.

- Record per call:
  - Hashes of sources, mapping, package and metadata at call start.
  - Hashes of any artifact the call writes.
  - The trigger: a user message with new files or corrections, a validator result, or self-initiated.
- Classify each call:
  - **Necessary:** inputs changed since the last same-task call because of a user-supplied source or correction.
  - **Redundant:** inputs unchanged and outputs unchanged, or a read-only tool call with identical arguments and state hash.
  - **Oscillation:** the output hash returns to an earlier value (A→B→A).
  - **Unresolved loop:** the same validator error persists across 3 or more calls with changing artifacts.
- Short-circuit identical read-only tool calls with "unchanged since call N".

**Measure:** USD by class for dataset 578 retrospectively, as far as your logs allow, then for new datasets. This also tells you whether proposals 2 and 3 address real waste.

### 5. Stage-level progress budgets and checkpoints before the ceiling
**Expected savings:** medium. **Risk:** low.

- Give each stage a soft budget expressed as "N calls without an artifact-hash change or a reduced error count".
- On breach, take a deterministic checkpoint: save state, then show the user a summary of unresolved items and a decision point.
- This prevents spending the last dollars mid-mutation, which is how dataset 578 ended with duplicates.

**Measure:**
- Stages ending at ceiling versus at checkpoint.
- Datasets left with failing validation at stop.

### 6. Make the DwC-A projection deterministic
**Expected savings:** medium (package preparation was USD 0.59 over 25 calls). **Risk:** medium.

- Projecting DwC-DP to DwC-A star schema is largely mechanical. Implement it in code.
- Reserve the model for EML narrative grounded in the evidence ledger and for flagging lossy projections.
- This is a hypothesis: first inspect which tools those 25 calls actually used.

**Measure:**
- Package preparation calls and USD.
- Field-level diff between the model-built and code-built archives on past datasets before switching.

## What I could not determine

- Which gate calls ran on prompts that predate your bounded audit/recovery instructions.
- How many gate runs were triggered by legitimate user corrections.
- Exact cache semantics (lifetime, write accounting).

Proposal 4's retrospective classification should come first. It turns these unknowns into data.
