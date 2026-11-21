# Specification: Tier-2 LLM Second-Opinion Pass for Taḥwīl-Aware Isnad Extraction

**Track ID:** `tier2_llm_isnad_reconciliation_20260612`
**Type:** Feature (data engineering — chain extraction coverage uplift)
**Priority:** P0 (coverage floor for K6 multi-branch corpus; gates downstream re-runs of Phase 6b on the parent track)
**Created:** 2026-06-12
**Depends on:** `uniform_isnad_extraction_20260609` (Phases 1 + 2 — canonical Tier-1 extractor module and `_compute_chain_indx` integration must exist)
**Blocks:** `uniform_isnad_extraction_20260609` Phase 6b (mode-repair) re-runs against the K6 multi-branch subset until Tier-2 lands, otherwise repair locks in the Tier-1-only floor
**Parallel-safe with:** `uniform_isnad_extraction_20260609` Phases 4 (resolver enrichment) and 5 (UI multi-chain rendering)

---

## 1. Overview

Adds a Tier-2 LLM reconciliation phase on top of the rule-based Tier-1 extractor (candidate C, LCS-suffix) in `datasets/hadith-data/extract_isnad_unified.py`. The Tier-2 pass fires **only** on Tier-1 outputs that fail specific suspicion checks (single-narrator branches when ح present, branch-count mismatch with ح-count, no convergence in a multi-branch row, low resolver-rate). It calls Claude Sonnet 4.6 with schema-validated JSON output, runs every emitted narrator through a hallucination guard against `all_rawis.csv`, and reconciles the LLM output back into the existing `|`-delimited `chain_indx` format without ever silently overwriting Tier-1.

This track operationalizes the architectural recommendation from the 2026-06-12 research mission whose synthesis lives at `.omc/research/uniform-isnad/research-session/report.md`. The mission concluded — across five parallel scientist stages — that **guaranteed taḥwīl-aware coverage is provably unreachable** (classical literature itself underspecifies ح semantics; ~5–15% of taḥwīl hadiths are genuinely ambiguous in source), so the honest architecture is a three-tier hybrid:

```
TIER 1 (rule-based, ~85% coverage) — candidate C from uniform_isnad_extraction_20260609
TIER 2 (LLM second opinion, lifts the FLOOR on the residual)   ← THIS TRACK
TIER 3 (HITL queue, the irreducible ambiguous residual)        — existing er-staging.jsonl flow
```

### 1.1 What this track does NOT promise

- **Not 100% coverage.** Per Stage 3 of the research, classical isnad in raw form is not context-free; the 5–15% residual is structural, not a tooling failure. Spec promises "highest achievable" with a clear HITL escalation path for the irreducible residual.
- **Not a replacement for Tier-1.** Tier-1 (candidate C) remains primary. Tier-2 fires only on suspicious rows. The published SOTA on linear isnad extraction is Bahgat et al. 2009 (P=91% / R=88% on 100 Bukhari hadiths, unreleased); our project's Tier-1 already sits at Jaccard median 0.845 on 5 fixtures — at or above SOTA. **Tier-2 exists to lift the FLOOR (p25 Jaccard 0.625), not the ceiling.**
- **Not a fine-tuned model.** Per Stage 2, fine-tuning needs 1,000–3,000 annotated isnad sentences (100–300 hrs of labor) to expect 80–90% F1 — worse worst-case than Claude Sonnet 4.6 at $8/run.

## 2. Background

### 2.1 Why a second-opinion pass, not a replacement

Stage 4 of the research found that LLM extraction has known, repeatable failure modes on classical isnad: hallucinated narrators (~3–5% phantom entities in GPT-4 Arabic NER per Ghaddar et al. 2023), inconsistent name normalization, unreliable pronoun/elision handling, and silent failures (malformed JSON without error signal). These are exactly the failures that break downstream graph merge if the LLM output is trusted blind. So Tier-2 is gated on:

1. A **suspicion detector** that only escalates rows Tier-1 likely mishandled (keeps cost down + keeps blast radius bounded)
2. A **hallucination guard** that requires every emitted narrator to resolve to a `scholar_indx` in `all_rawis.csv` or be tombstoned as a `:NameMention` per the existing HITL flow (no silent insertion of phantom narrators into the graph)
3. A **reconciliation policy** that prefers Tier-2 surviving narrators but always logs the diff — never a silent overwrite of Tier-1

### 2.2 What the parent track left in place

After `uniform_isnad_extraction_20260609` Phases 1 + 2:

- `datasets/hadith-data/extract_isnad_unified.py` exports `extract_isnad_branches(text_ar) → list[list[str]]` (candidate C, LCS-suffix) and `resolve_branches_to_indxs(branches, exact_index, blocked_index) → list[list[str]]`.
- `datasets/hadith-data/regen_unified_csvs.py` exposes `_compute_chain_indx(text_ar, fallback_sanad_list, exact_index, blocked_index, stats) → str` as the single chain_indx writer across all source paths.
- `chain_indx` CSV cells use `|`-separated branches, `,`-separated within-branch (FR-2.1 of parent).
- Tier-1 floor stats from Phase 0.5 Round-2: branch-count accuracy 1.000, Jaccard median 0.845, **Jaccard p25 0.625** — the floor Tier-2 is designed to lift.

### 2.3 Cost envelope from the research mission

Stage 4 sized the cost ceiling precisely:

| Scope | Token budget | $/row | Total |
|---|---|---|---|
| Per-row LLM call | ~500 in + 200 out @ $3/$15 per MTok | ~$0.0045 | — |
| Full K6 multi-branch corpus (1,768 rows), all triggering Tier-2 | — | $0.0045 | **~$8 worst case** |
| Full 99k corpus, all triggering Tier-2 | — | $0.0045 | ~$450 |
| Full 99k corpus with the suspicion filter (~5% trigger rate expected) | — | — | **$15–25 realistic** |

The hard cost ceiling (NFR / FR-6) caps this at **$50/run** to guarantee no runaway pass.

## 3. Functional Requirements

### FR-1 — Suspicion detector

**FR-1.1** — New module `datasets/hadith-data/tier2_llm/suspicion.py` exports:

```python
def is_suspicious(
    tier1_branches: list[list[str]],
    tier1_resolved: list[list[str]],
    text_ar: str,
) -> tuple[bool, str | None]:
    """Decide whether a row's Tier-1 output should trigger Tier-2.

    Returns (True, reason) if the row is suspicious, (False, None) otherwise.
    The `reason` string is one of the canonical suspicion-reason codes below
    and is emitted into the per-row audit log.
    """
```

**FR-1.2 — Trigger conditions.** Any ONE of the following triggers Tier-2:

| Code | Condition |
|---|---|
| `tahweel_no_branch` | ح present in `text_ar` (per `audit_tahweel_stats.py` regex) but `len(tier1_branches) == 1` (Tier-1 detected no taḥwīl when one is present) |
| `branch_count_mismatch` | `len(tier1_branches) != count_of_ح(text_ar) + 1` (branch count doesn't match ح-marker count) |
| `short_branch` | Any branch has `len(narrators) < 2` (suspiciously short — likely over-stripping) |
| `no_convergence` | Multi-branch row but candidate C's LCS-suffix returned empty (no detectable shared post-convergence segment) |
| `low_resolution` | Any branch has `len(resolved) / len(branches[i]) < 0.4` (lots of unmatchable surface forms — Tier-1 may have split badly) |

**FR-1.3 — ح-counting helper.** Reuse the detector regex shared with `audit_tahweel_stats.py` and the parent track's FR-1.1 step 1. Do not redefine.

**FR-1.4 — Suspicion is monotonic in the direction of "trigger more, not less."** If the user (Jade) tunes thresholds later, defaults err on the side of triggering Tier-2 — false positives cost ~$0.0045 each, false negatives cost a permanently-broken chain.

### FR-2 — LLM call wrapper

**FR-2.1** — New module `datasets/hadith-data/tier2_llm/client.py` exports:

```python
def call_llm_for_branches(
    text_ar: str,
    sanad_hint: list[str] | None,
    hadith_meta: dict,
) -> list[list[str]]:
    """Send `text_ar` to Claude Sonnet 4.6 with a few-shot prompt and
    structured JSON output, return list-of-lists matching the rule-based
    extractor's contract.

    On unrecoverable failure (3 retries exhausted), returns the canonical
    sentinel value `_LLM_FALLBACK_SENTINEL` and logs `llm_extraction_failed`
    to the per-row audit log so the caller falls back to Tier-1.
    """
```

**FR-2.2 — Structured JSON output via Anthropic SDK tool_use.** The LLM call MUST NOT free-text parse the response. Use the Anthropic SDK's `tool_use` mechanism with a tool whose `input_schema` is:

```json
{
  "type": "object",
  "properties": {
    "branches": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1
      },
      "minItems": 1
    },
    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    "notes": {"type": "string"}
  },
  "required": ["branches", "confidence"]
}
```

The wrapper parses `tool_use.input.branches` directly. If the model emits free-form text instead of calling the tool, that counts as a schema-validation failure.

**FR-2.3 — Few-shot prompt.** The prompt MUST include 3 hand-curated examples from `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl` (a 2-branch case, a 3-branch case, and a no-taḥwīl single-chain case). The prompt is versioned in `datasets/hadith-data/tier2_llm/prompts/extract_branches_v1.md` (markdown for ease of review; loaded at runtime). Bumping the prompt version REQUIRES bumping the version string (e.g., `_v2.md`) so the cache-key (NFR-1) invalidates.

**FR-2.4 — Retry policy.** Up to 3 attempts on schema-validation failure with progressively-more-explicit prompts:
1. **Attempt 1:** Base prompt + 3 few-shot examples.
2. **Attempt 2:** Base prompt + 3 few-shot examples + explicit reminder ("You MUST call the `extract_branches` tool with valid JSON. Do not respond with free text.").
3. **Attempt 3:** Base prompt + 3 few-shot examples + the failing response from attempt 2 quoted back ("Your previous response was rejected because: <validator error>. Please call the tool correctly now.").

After 3 retries, returns the sentinel and logs `llm_extraction_failed` with the per-attempt error trace.

**FR-2.5 — Model pin.** Claude Sonnet 4.6 only. Model ID pinned to a constant `_CLAUDE_MODEL_ID = "claude-sonnet-4-6-20260101"` (placeholder; actual ID confirmed at implementation time). Multi-vendor support is out of scope (see §6).

### FR-3 — Hallucination guard

**FR-3.1** — Every narrator surface emitted by Tier-2 MUST be validated against `all_rawis.csv` via the existing resolver. New module `datasets/hadith-data/tier2_llm/hallucination_guard.py` exports:

```python
def guard_branches(
    llm_branches: list[list[str]],
    exact_index: dict,
    blocked_index: dict,
) -> tuple[list[list[str | int]], dict]:
    """For each surface form in each branch:
       - if resolve_narrator(surface, exact_index, blocked_index) returns a
         scholar_indx → keep the int scholar_indx
       - else → tombstone as a NameMention placeholder (string of the form
         `"NM::<sha1(surface)[:8]>"`) and emit the surface to the per-row
         audit's `name_mentions` field for the existing er-staging.jsonl
         HITL pipeline to pick up.

    Returns (guarded_branches, stats) where stats contains per-row resolution
    rate and the NameMention surfaces.
    """
```

**FR-3.2 — Mixed-output branches are allowed.** A branch may contain a mix of resolved scholar_indxs (ints) and `NM::<hash>` placeholders (strings). The downstream serializer writes ints verbatim and writes `NM::*` markers into a sidecar column (`name_mention_indx`) for er-staging consumption — they are NOT inlined into `chain_indx` (which stays integer-only to preserve backwards-compat parsing in `src/scripts/lib/regen/io.ts`).

**FR-3.3 — HITL escalation threshold.** After the validation pass, count the resolution rate per row. If `total_resolved / total_surfaces < 0.5`, the row is escalated to the HITL queue (er-staging.jsonl entry of type `tier2_low_resolution`) **and** Tier-2's output for that row is discarded — the row falls back to Tier-1 in the final reconciled output. Rationale: a row where Tier-2 disagrees so heavily with the rawi lexicon is more likely hallucinating than discovering.

**FR-3.4 — NameMention emission format** matches the existing schema consumed by `src/scripts/ingest-er-approved.ts` and `datasets/hadith-data/er-staging.jsonl`. Each NameMention entry contains: `{type: "tier2_name_mention", hadith_id, dvId, surface_form, branch_index, position, llm_confidence, prompt_version, model_id, ts}`. Do not invent a new schema — extend the existing one if a field is missing.

### FR-4 — Reconciliation

**FR-4.1** — New module `datasets/hadith-data/tier2_llm/reconcile.py` exports:

```python
def reconcile_tier1_tier2(
    tier1_resolved: list[list[str]],
    tier2_guarded: list[list[str | int]],
    text_ar: str,
    row_meta: dict,
) -> tuple[list[list[str]], list[dict]]:
    """Reconcile Tier-1 and Tier-2 outputs into the final chain_indx branches.

    Returns (final_branches, audit_events) where audit_events is a list of
    structured log entries describing every disagreement and the resolution.
    """
```

**FR-4.2 — Disagreement policy:**

| Disagreement type | Policy |
|---|---|
| Tier-2 has MORE narrators in a branch than Tier-1 (expected case) | Prefer Tier-2 for that branch. Emit `tier2_extended_branch` event. |
| Tier-2 has FEWER narrators (hallucination guard removed some) | Prefer Tier-2's surviving narrators (already guard-validated). Emit `tier2_pruned_branch` event with the diff. |
| Tier-2 disagrees on branch COUNT | Prefer Tier-1's branch count. Use Tier-2's narrators only for branches Tier-1 also found (positionally). Emit `branch_count_disagreement` event with both counts. |
| Tier-1 empty + Tier-2 populated | Prefer Tier-2. Emit `tier1_empty_tier2_recovered` event. |
| Tier-1 populated + Tier-2 sentinel (FR-2.5) | Prefer Tier-1. Emit `tier2_extraction_failed_fallback`. |
| Tier-1 populated + Tier-2 discarded by FR-3.3 | Prefer Tier-1. Emit `tier2_low_resolution_fallback`. |

**FR-4.3 — Never silently overwrite Tier-1.** Every divergence between Tier-1 and Tier-2 produces an audit event. The set of event codes is the canonical contract; tests in FR-7 assert each is emitted on its trigger fixture.

**FR-4.4 — Audit log format.** Append each row's events to `logs/tier2-<dvId>.jsonl` as one JSON object per row:

```json
{
  "ts": "<ISO 8601>",
  "dvId": "<dataset-version-id>",
  "hadith_id": "<id>",
  "row_idx": <int>,
  "suspicion_reason": "<FR-1.2 code>",
  "tier1_branches": [...],
  "tier2_branches": [...],
  "final_branches": [...],
  "events": [{"code": "...", "details": {...}}, ...],
  "cost_usd": <float>,
  "prompt_version": "<v1>",
  "model_id": "<claude-sonnet-4-6-...>"
}
```

### FR-5 — Integration into the existing pipeline

**FR-5.1** — Extend `regen_unified_csvs.py` with `_compute_chain_indx_with_tier2(...)` that wraps the parent track's `_compute_chain_indx`:

```python
def _compute_chain_indx_with_tier2(
    text_ar: str,
    fallback_sanad_list: list[str] | None,
    exact_index, blocked_index,
    stats: dict,
    row_meta: dict,
) -> str:
    """Wrapper that calls Tier-1, checks is_suspicious, conditionally calls
    Tier-2 + hallucination guard + reconciliation, and emits the per-row
    audit log. Returns the final reconciled `|`-delimited chain_indx cell."""
```

Algorithm:
1. Call parent's `_compute_chain_indx(...)` and capture `tier1_branches`, `tier1_resolved`.
2. Call `is_suspicious(tier1_branches, tier1_resolved, text_ar)`. If False → return the Tier-1 string unchanged. Emit `{suspicion_reason: null, action: "tier1_passthrough"}` to audit log.
3. Else, check the cost ceiling (FR-6). If exceeded → return Tier-1 string unchanged + emit `cost_ceiling_hit`.
4. Else, call `call_llm_for_branches(text_ar, fallback_sanad_list, row_meta)`. If sentinel → return Tier-1 unchanged + emit `tier2_extraction_failed_fallback`.
5. Call `guard_branches(llm_branches, exact_index, blocked_index)`. If FR-3.3 triggers → return Tier-1 unchanged + emit `tier2_low_resolution_fallback`.
6. Call `reconcile_tier1_tier2(tier1_resolved, tier2_guarded, text_ar, row_meta)`. Use the returned `final_branches` to construct the `|`-delimited string.
7. Emit the full audit log entry.

**FR-5.2 — Call-site wiring.** Replace every call to `_compute_chain_indx` in `regen_unified_csvs.py` with `_compute_chain_indx_with_tier2` — same signature plus the new `row_meta` arg. Three call sites from the parent track's FR-3.1: `_enrich()` Sunni branch, `openiti_to_clean_row` / `openiti_to_shia_row`, `load_classical_sunni_rows`.

**FR-5.3 — Output format unchanged.** `_compute_chain_indx_with_tier2` returns the same `|`-delimited string format as the parent's `_compute_chain_indx`. The TS reader (`src/scripts/lib/regen/io.ts`) requires NO changes. NameMention sidecar column (`name_mention_indx`) is a NEW column appended at the end of the CSV; existing readers ignore unknown columns.

### FR-6 — Hard cost ceiling

**FR-6.1** — Module-level cumulative cost counter in `datasets/hadith-data/tier2_llm/cost_tracker.py`:

```python
_CUMULATIVE_COST_USD = 0.0
_COST_CEILING_USD = float(os.getenv("TIER2_COST_CEILING_USD", "50.0"))

def add_cost(input_tokens: int, output_tokens: int) -> float: ...
def check_ceiling() -> bool: ...  # True if ceiling exceeded
```

**FR-6.2 — Behavior on ceiling hit:** After each LLM call returns, `add_cost` is called with the actual token counts from the response. Before the NEXT LLM call, `check_ceiling()` is consulted. If True, the pass aborts Tier-2 for ALL remaining rows and falls back to Tier-1 results. An incident file is written at `logs/tier2-cost-ceiling-<dvId>-<ts>.json` with `{ceiling_usd, actual_usd, rows_processed_with_tier2, rows_remaining}`.

**FR-6.3 — Token accounting.** Token counts come from the Anthropic SDK response's `usage.input_tokens` and `usage.output_tokens`. Do NOT estimate from prompt length — use the SDK's reported numbers.

**FR-6.4 — Per-run reset.** `_CUMULATIVE_COST_USD` resets to 0 at the start of each pass (a new `regen_unified_csvs.py` invocation). The ceiling is per-run, not per-day or per-process-lifetime.

### FR-7 — Test coverage

**FR-7.1 — Suspicion detector unit tests.** ≥ 10 unit tests in `datasets/hadith-data/__tests__/test_tier2_suspicion.py` covering: each of the 5 trigger codes in FR-1.2 (5 tests), at least 2 non-triggering control cases (well-formed single chain, well-formed 2-branch taḥwīl), and ≥ 3 edge cases (empty text_ar, text_ar with only matn, text_ar with quoted-ح-in-matn that should not trigger). All tests run without network.

**FR-7.2 — Hallucination guard tests.** ≥ 6 tests in `test_tier2_hallucination_guard.py`: a fully-resolvable branch (no NameMention emission), a fully-hallucinated branch (all surfaces tombstoned), a mixed branch, the FR-3.3 threshold boundary (49% vs 51% resolution), the empty branch case, the duplicate-surface case.

**FR-7.3 — Reconciliation tests.** ≥ 8 tests in `test_tier2_reconcile.py`, one per disagreement type in FR-4.2 plus the no-disagreement passthrough.

**FR-7.4 — End-to-end fixture test.** A pytest in `test_tier2_e2e.py` that runs the full `_compute_chain_indx_with_tier2` against each of the 5 `tahweel-gold.jsonl` fixtures with a MOCKED LLM client (NFR-2). Asserts the final branches match the gold expectations OR fall back to Tier-1 cleanly.

## 4. Non-Functional Requirements

**NFR-1 — Idempotency via response caching.** Re-running with the same CSV + same prompt-version + same model-id produces identical output. Implementation: a JSONL response cache at `datasets/hadith-data/tier2_llm/.cache/<model_id>__<prompt_version>.jsonl` keyed by `sha256(text_ar + sanad_hint_json)`. On cache hit, skip the LLM call entirely (also skips the cost counter increment — cached calls are free). On cache miss, call the LLM, write the response to the cache. Temperature is set to 0 but caching is the authoritative idempotency mechanism since Claude responses at T=0 are still non-deterministic enough to break bit-equality.

**NFR-2 — No network on test paths.** All unit tests use a `MockLLMClient` interface in `datasets/hadith-data/tier2_llm/__tests__/_mocks.py` that returns canned responses keyed by input hash. The real `AnthropicClient` and `MockLLMClient` both implement a single `Protocol` named `LLMClient` so swap is a one-line constructor change. Tests that touch the network are tagged `@pytest.mark.network` and skipped by default in CI.

**NFR-3 — Dry-run mode.** `--dry-run-tier2` flag on `regen_unified_csvs.py` runs everything but stubs `call_llm_for_branches` to return the Tier-1 result unchanged. The cost tracker is bypassed. Used for CI and local iteration. Distinct from `--dry-run` on the parent track (which is a CSV-vs-Neo4j dry run, not an LLM dry run).

**NFR-4 — Backwards compatibility on Tier-2 disable.** If `DISABLE_TIER2=1` is set in the environment, `_compute_chain_indx_with_tier2` is a thin alias for `_compute_chain_indx` (no suspicion check, no LLM call, no audit log). The CSV output is bit-identical to a parent-track-only run. Tested via G-4 below.

**NFR-5 — Hadith scholar sign-off on prompt content.** The few-shot examples in `prompts/extract_branches_v1.md` MUST come from the hand-annotated `tahweel-gold.jsonl` and MUST be signed off by Jade (the project lead, an Islamic scholar with hadith expertise) before Phase 2 of the implementation plan ships. Sign-off recorded as a comment line in the prompt file: `<!-- signed-off-by: Jade Zaher, 2026-06-XX -->`.

**NFR-6 — Performance budget.** Average per-row Tier-2 call (including network round-trip): ≤ 3 sec. Total pass over the K6 multi-branch subset (1,768 rows at ~5% trigger rate = ~88 actual LLM calls): ≤ 5 min wall time. Cached re-runs: ≤ 30 sec.

**NFR-7 — Log volume.** Audit JSONL grows at ~2 KB per Tier-2 invocation. At 5% trigger over 99k rows = ~5000 entries = ~10 MB. Acceptable. Rotate by `dvId`; no archival policy needed at this scale.

**NFR-8 — Concurrent-write safety on cache.** If multiple Python processes ever write to the cache concurrently (rare; only if a future pipeline parallelizes the CSV builder), the cache MUST use an atomic append pattern (open mode `'a'` is atomic for small writes on Linux/macOS; on Windows use file locking via `portalocker`). Currently single-process; the lock is precautionary.

## 5. Acceptance Guardrails

Each is a test. Pattern matches the parent track's 7-guardrail style.

**G-1 — Suspicion detector correctness.** On the 5 fixtures in `tahweel-gold.jsonl`, the suspicion detector triggers on AT LEAST ONE fixture that Tier-1 mishandles (validates the trigger logic is wired to real signal, not noise). Test: run `is_suspicious` against each fixture's Tier-1 output, assert `sum(is_suspicious(...)[0] for f in fixtures) >= 1`.

**G-2 — Hallucination guard works.** Plant a fake row where Tier-2 (mocked) returns a made-up narrator name `"خليفة بن قرفقس"` (a non-existent name not in `all_rawis.csv`). Assert the guard tombstones it as a `NM::<hash>` placeholder AND emits the surface to the audit log's `name_mentions` field. Zero phantom scholar_indxs in the final `chain_indx`.

**G-3 — Cost ceiling enforces.** With `TIER2_COST_CEILING_USD=0.05`, run the pass against a 50-row test CSV where all rows trigger Tier-2. Assert: ~10 rows are processed with Tier-2 (depending on actual token usage), the remaining ~40 fall back to Tier-1, and the incident file at `logs/tier2-cost-ceiling-*.json` is written with the correct counts.

**G-4 — Tier-2 fallback is bit-identical when `DISABLE_TIER2=1`.** Run the CSV builder twice: once with the env var set, once with the parent track at the same commit. Assert the two output CSVs are byte-identical (after sorting by `dataset_row_id` to neutralize any ordering nondeterminism).

**G-5 — Reconciliation never silently overwrites.** For each of the 6 disagreement types in FR-4.2, a corresponding fixture exists in `tahweel-gold-disagreements.jsonl` (NEW file — to be hand-authored in Phase 0). After running the reconciler, assert that every fixture produces the expected event code in the audit log. Zero silent overwrites.

**G-6 — End-to-end coverage improvement on K6 multi-branch.** After running over the 1,768 K6 multi-branch hadiths with Tier-2 enabled, the `diagnose-chain-data.ts` script (parent track) shows a strictly higher `avg narrators per chain` than the Tier-1-only baseline from the parent track's Phase 6b. Numeric target: K6 average narrators per chain moves into [4.8, 6.8] vs the Tier-1-only [4.5, 6.5]. **Floor uplift, not ceiling change** — the bar is the p25 Jaccard improving from 0.625 toward 0.75 on a re-evaluated gold set.

**G-7 — Idempotent re-runs via cache.** Run the pass twice in succession without clearing the cache. Second run makes ZERO LLM calls (verified via cost counter == 0.0 at end of run 2). Audit log entries from run 2 are byte-identical to run 1 (after timestamp normalization).

## 6. Out of Scope

- **Switching extractor primary from rule-based to LLM-based.** Tier-1 (candidate C) remains primary. Tier-2 is the fallback for suspicious cases only. Even if Tier-2 outperforms Tier-1 on the gold set, the design intent is hybrid not LLM-first.
- **Fine-tuning a custom Arabic NER model.** Per Stage 2 of the research, requires 1,000–3,000 annotated sentences + 100–300 hrs of labor with worse worst-case than the LLM at $8/run. Defer.
- **Expanding the gold set beyond the existing 5 fixtures in this track.** If desired, file as a follow-up track (`tahweel_gold_expansion_<date>`).
- **Multi-vendor LLM support.** Claude Sonnet 4.6 only in scope. GPT-4 / Gemini as a follow-up if cost/accuracy tradeoffs shift.
- **Tier-3 HITL queue UI / workflow.** This track produces the NameMention entries; the existing `er-staging.jsonl` + `ingest-er-approved.ts` flow consumes them. No UI changes required by this track.
- **Re-prompting strategies beyond the 3-attempt retry.** Chain-of-thought, self-consistency, ensembling — out of scope. The simple retry is the floor; sophistication is a follow-up if accuracy data motivates it.
- **Auto-expanding the prompt's few-shot examples.** Few-shot count is fixed at 3 to keep input tokens predictable. If signal indicates more examples help, file as a follow-up.

## 7. Technical Considerations / Decisions Made

**TC-1 — Why caching beats temperature=0 for idempotency.** Claude responses at T=0 are still non-deterministic enough across model upgrades and infrastructure changes to break bit-equality on a 99k-row pass. Caching by `sha256(text_ar + sanad_hint_json) + prompt_version + model_id` is the only path to true idempotency. T=0 is set as a quality measure (reduces drift between cache misses), not the idempotency mechanism.

**TC-2 — Why structured tool_use beats free-text JSON parsing.** Free-text JSON has ~3% silent failure rates on Claude per Stage 4 (malformed brackets, trailing commas, code-fence wrapping). Anthropic SDK's `tool_use` enforces the schema server-side; the client never sees a malformed payload. The retry logic in FR-2.4 only fires on "model didn't call the tool at all," which is rare and recoverable.

**TC-3 — Why NameMention placeholders are sidecar, not inlined.** `chain_indx` is parsed by `src/scripts/lib/regen/io.ts`'s `parseIndices` as integer-only. Inlining `NM::<hash>` strings would require a TS-side parser change cascading into `load-chain.ts` and the loader-batch. The sidecar `name_mention_indx` column keeps the TS reader unchanged and lets the HITL ingest path consume it directly (matches the existing er-staging pattern).

**TC-4 — Why $50 hard ceiling, not a percentage.** Percentage-of-budget ceilings drift as the corpus grows. A flat dollar number is the unambiguous safety net — "this pass cannot cost more than dinner regardless of corpus size." For the realistic $15–25 expected spend, $50 is ~2x headroom for surprise retries.

**TC-5 — Why suspicion detector errs toward over-triggering.** A false positive costs $0.0045; a false negative locks in a broken chain in the live graph until the next pass. The asymmetry is huge. Defaults are conservative; thresholds are env-var-tunable for future calibration.

**TC-6 — Why the reconciliation never silently overwrites.** Auditability. The research report (Synthesis section) emphasizes the "honest architecture" framing: every divergence is a scholarly judgment call, and the audit log is the durable record of those calls. A future researcher (or Jade) inspecting the graph can reconstruct exactly why a given chain has its current shape.

**TC-7 — Why HITL threshold is 50% resolution, not lower.** Below 50% resolution rate, the LLM is more likely hallucinating than discovering — the resolved/unresolved split is roughly the noise floor of the rawi lexicon's surface-form coverage. Above 50%, the unresolved surfaces are plausibly kunyas or honorific variants worth HITL review. This is calibrated against Phase 0.5 Round-2's observed resolver rates on the gold set.

## 8. Dependency Edges

- **Depends on:** `uniform_isnad_extraction_20260609` Phase 1 (canonical `extract_isnad_unified.py` module exists, exporting `extract_isnad_branches` and `resolve_branches_to_indxs`) AND Phase 2 (`_compute_chain_indx` in `regen_unified_csvs.py` is wired in across all three source paths).
- **Blocks:** `uniform_isnad_extraction_20260609` Phase 6b (mode-repair) re-runs against the K6 multi-branch subset until Tier-2 lands. Otherwise the repair pass locks in the lower-coverage Tier-1-only state and a subsequent Tier-2-aware re-run would need to diff against an already-repaired DB (more expensive, more risky).
- **Parallel-safe with:**
  - `uniform_isnad_extraction_20260609` Phase 4 (resolver enrichment — kunya alias indexing) — does not touch the extractor pipeline; Tier-2 benefits from a better resolver but doesn't gate on it.
  - `uniform_isnad_extraction_20260609` Phase 5 (UI multi-chain rendering) — UI is unchanged by Tier-2; it reads the same `:Chain` topology.
  - `narrator_enrichment_20260425`, `gds_setup_analytics_20260425` — Tier-2 improves their inputs but does not gate.
- **Does not block / parallel with:** `grade_normalization_20260425`, `scholarly_metadata_layer_20260425`, `comparative_ingestion_20260322`, all data-acquisition waves.

## 9. Open Questions

**Q1 — Exact Claude Sonnet 4.6 model ID.** Pin at implementation time. `claude-sonnet-4-6-20260101` is a placeholder. Update the constant + the cache-key invalidation note in NFR-1 when confirmed.

**Q2 — Does the existing er-staging.jsonl schema have all fields needed for FR-3.4?** Inspect `src/scripts/ingest-er-approved.ts` at the start of Phase 0 to confirm. If a field is missing (e.g., `branch_index`), extend the schema in a backwards-compatible way (new optional fields) and document.

**Q3 — Does Anthropic's tool_use mechanism count rejected tool_use attempts toward billed input tokens?** Likely yes (the prompt was processed). Means the retry policy in FR-2.4 effectively triples the worst-case cost for failed rows. Empirically validate during Phase 2; if cost is higher than expected, tighten retry from 3 to 2.

**Q4 — Where exactly should the `name_mention_indx` sidecar column live in the CSV header?** End of header to preserve column-position stability for any existing consumers. Document in `parent track FR-2` if it lands first.

**Q5 — Should Tier-2 also fire on rows where Tier-1 produced output but the resolver_rate is HIGH but the branch count is OFF?** Example: 3-branch hadith where Tier-1 found 2 branches, both fully-resolved. The current FR-1.2 catches this via `branch_count_mismatch` only if ح-count != branch-count − 1. Confirm the ح-counter is robust to over-counted ح (e.g., ح inside a quoted matn).

## 10. Acceptance Gate Summary

| Gate | Criterion | Test |
|---|---|---|
| G-1 | Suspicion detector triggers on ≥1 mishandled gold fixture | `test_tier2_suspicion.py::test_g1` |
| G-2 | Hallucination guard tombstones planted phantom narrator | `test_tier2_hallucination_guard.py::test_g2` |
| G-3 | Cost ceiling aborts mid-pass at $0.05 cap | `test_tier2_cost_ceiling.py::test_g3` |
| G-4 | `DISABLE_TIER2=1` produces bit-identical Tier-1-only CSV | `test_tier2_disable_passthrough.py::test_g4` |
| G-5 | Every FR-4.2 disagreement type produces its event code | `test_tier2_reconcile.py::test_g5_*` |
| G-6 | K6 multi-branch coverage uplift (avg narrators per chain, p25 Jaccard) | Diagnose-script delta vs parent baseline |
| G-7 | Cached re-run makes zero LLM calls, byte-identical audit log | `test_tier2_cache_idempotency.py::test_g7` |

Pass all seven → ship to Phase 6b re-run on K6 multi-branch.
