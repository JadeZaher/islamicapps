---
type: specification
---

# Specification: Uniform Taḥwīl-Aware Isnad Extraction

**Track ID:** `uniform_isnad_extraction_20260609`
**Type:** Feature (data engineering — chain extraction quality)
**Priority:** P0 (correctness floor for the user-facing chain display + the GDS analytics track)
**Created:** 2026-06-09
**Depends on:** `neo4j_isnad_graph_regen_20260516` (regen pipeline + reified `:Chain` schema)
**Blocks:** `narrator_enrichment_20260425` (kunya gaps need closing here), `gds_setup_analytics_20260425` (multi-isnad mutawātir analytics need proper branch separation)

**Implementation decision (2026-07-20):** the canonical extractor promotes the
candidate-C suffix-alignment strategy, but keeps each earlier branch's fuller
convergence surface and appends only the unmatched final-branch tail. Arabic
vocalization is ignored for parsing; pronouns and collective surfaces are not
identity-expanded. The release evidence is now a 32-record, provenance-backed
gold set across Sunni, Imami, Ibadi, and Zaydi sources. Historical five-row
metrics below are design history only; acceptance requires an independent run
on all 32 records with branch-count accuracy and median branch Jaccard both at
least 0.90, median normalized ordered edit similarity at least 0.90, and each
tradition's branch-count accuracy and mean ordered similarity at least 0.80.
Co-transmitters are parallel alternatives, never sequential edges. Resolution
is atomic: one unresolved or invalid surface empties the whole row chain.

---

## 1. Overview

Replace the **three divergent chain_indx code paths** in `datasets/hadith-data/regen_unified_csvs.py` with **one uniform taḥwīl-aware extractor** that runs against every hadith's `text_ar` (or, where present, structured `sanad_detail` / `arabicText` from upstream parsers). Emit **one `:Chain` node per ح-branch**, each independently extended through the shared post-convergence segment back to the Companion / Imam / Prophet.

This is correctness work, not a feature add. It fixes a class of bug surfaced by the user on Jami' al-Tirmidhi #1: the chain display shows only the *pre-convergence prefix* of one branch, missing the shared post-convergence narrators (Muṣʿab b. Saʿd, Ibn ʿUmar) that connect the chain to the Prophet ﷺ. Same pathology affects every taḥwīl hadith across the Sunni Six and the Imami compilations.

### 1.1 Apply mode: differential repair, NOT drop-and-recreate

**Local-first override (2026-07-20):** the repair design below remains a
technical proposal, not an execution prescription. This track authorizes only
local staged regeneration and a disposable-local/no-write graph dry run.
Railway mutation requires a separately approved cutover after every extractor,
manifest, loader, UI, and rollback gate passes for the confirmed project.

**Decision (2026-06-10):** this track does **not** call `--mode=fullregen`. The existing fullregen pattern wipes all `:INCLUDES` and `:NARRATED_FROM` edges globally then re-CREATEs from scratch (`mode-fullregen.ts:391–443` after the 2026-06-08 wipe addition). That's appropriate when the source-of-truth is being rebuilt wholesale; it is **not appropriate** for an incremental correctness fix that touches the chain composition of a known subset of hadiths.

This track introduces a new mode: **`--mode=repair`**. Its contract:

1. For each hadith in the unified CSV, compute the **new** `chain_indx` (the multi-branch `|`-delimited form from FR-2).
2. Query the **live** `:Chain` topology for that hadith.
3. Diff the two. Three possible outcomes per hadith:
   - **Identical** — no DB write. Most rows by count, since the changes are concentrated in K6 taḥwīl hadiths + Imami sanad_detail rows.
   - **Changed** — surgically repair: add missing narrators, remove orphaned ones, update positions, split a single chain into multiple when the new data has more branches than the live state. Each repair is its own transaction, rolls back independently on failure.
   - **New** (hadith has no `:Chain` in live DB) — load it fresh, like fullregen would.
4. Never use a global `MATCH ()-[r:INCLUDES]->() DELETE r` or equivalent. The wipe step from `mode-fullregen.ts` line 391 onward is **explicitly forbidden** in repair mode.
5. Emit per-hadith repair logs to `logs/regen-repair-<dvId>.jsonl` for audit and reproducibility.

Remote duration and cost are intentionally not estimated until the local dry
run supplies current evidence and the user approves a bounded cutover.

The upside: any chain that was *already correct* (or already partially fixed by a prior pass) is left untouched. If a downstream track has been hand-curating specific narrator edges (e.g., a future HITL pass adding human-resolved kunyas to specific chains), repair mode preserves that work. Fullregen would erase it.

## 2. Background

### 2.1 What the prior track (`neo4j_isnad_graph_regen_20260516`) left in place

The reified `:Chain` / `:INCLUDES` schema is correct. `loadChainForRow` in
`src/scripts/lib/regen/load-chain.ts` already iterates `resolutions: NarratorResolutionResult[]` — each `resolution` becomes one `:Chain` node with its own `chain_index`. The TS-side multi-isnad support **already exists**.

The Python CSV builder is the bug. It has three diverging paths:

| Path | Source data | What it produces | Failure mode |
|---|---|---|---|
| K6 Sunni `_enrich()` | `sunni_isnad.jsonl` sidecar's `sanad: [...]` | One flat chain, taḥwīl-stripped | Drops post-convergence narrators (Tirmidhi #1: shows 2/5 narrators) |
| Classical Sunni `load_classical_sunni_rows()` | `extract_classical_isnad(text_ar)` on `pure_canon.jsonl` | One flat chain, taḥwīl-stripped | Same. Plus only 22% resolve to scholar_indx. |
| Imami / Ibadi / Zaydi / Rida (Fix B + C from 2026-06-05 ultrapilot batch) | `thaqalaynSanad` English splitter / `sanad_detail[*].name_ar` / Arabic extractor on `text_ar` | One flat chain | No taḥwīl handling. Low resolution rate (13–28%). |

### 2.2 The taḥwīl problem, restated

Classical isnad grammar marks **transmission convergence** with ح (lone letter heh). Two example branches that share a common transmitter:

> حدثنا A، حدثنا B، عن C، **ح وحدثنا D، حدثنا E، عن F، عن C، عن G، عن H، عن النبي ﷺ**

Semantically:
- Branch 1: A → B → C → G → H → Prophet ﷺ
- Branch 2: D → E → F → C → G → H → Prophet ﷺ
- C is the **convergence narrator**. From C forward, the chain is shared between both branches and reaches the Prophet via G and H.

The existing `extract_classical_isnad` at `regen_unified_csvs.py:411` truncates at the first ح and discards Branch 2 entirely. The user-reported Tirmidhi #1 bug is exactly this: the live chain stops at سماك بن حرب (C) and never reaches Ibn ʿUmar (H) or the Prophet.

The correct semantics:

> Branch 1 full chain = [A, B, C, G, H, Prophet] = pre-ح prefix + post-convergence suffix from Branch 2
> Branch 2 full chain = [D, E, F, C, G, H, Prophet] = the full second clause

Both chains independently connect to the Prophet. They are **independent isnads** in the classical sense — counting how many independent paths exist is the basis of *mutawātir / mashhūr / āḥād* classification, so we MUST preserve them as separate `:Chain` nodes, not collapse into one.

### 2.3 Why this matters for downstream tracks

- **Narrator enrichment** (`narrator_enrichment_20260425`) builds biographical bios keyed off scholar_indx. Today's broken chains drop ~3 narrators per K6 hadith on average; enriching narrators who never appear in any chain is wasted effort. Fix the chains first.
- **GDS analytics** (`gds_setup_analytics_20260425`) counts isnad branches per matn to surface *mutawātir* candidates. A collapsed-or-truncated chain reports 1 isnad where there are 2 — false negatives on the most important grade class.
- **UI** (`/hadith/[id]`) currently shows truncated chains to users, which is read by Islamic-scholar users (per `[[user_islamic_scholar_developer]]`) as factually wrong. This is the loudest correctness floor.

## 3. Functional Requirements

### FR-0.5 — Empirical algorithm bake-off (PRECONDITION FOR FR-1)

**Phase 0 audit finding (2026-06-11):** A naive convergence detector (set-intersection on verb-split tokens, normalized via `_norm`) found token-overlap in only **30%** (15/50) of sampled Ṣaḥīḥ Muslim 1-ح rows — far below the > 95% the original FR-1.1 implicitly assumed. The token boundaries the cleaner produces are too small (single Arabic word tokens, not full name spans) and convergence narrators often appear with subtly different surface forms across branches (`عن سماك بن حرب` in one branch, `عن سماك` in the other).

This invalidates "implement FR-1.1's algorithm and ship" as a straight-line plan. Before any production code is written, we must **empirically evaluate** several candidate algorithms against a labeled set of hand-annotated taḥwīl hadiths to pick the right one. Findings recorded at [`.omc/research/uniform-isnad/algo-evaluation.md`](../../../.omc/research/uniform-isnad/algo-evaluation.md).

**FR-0.5.1 — Labeled gold set.** Maintain at least 30 manually annotated,
provenance-backed records across Sunni, Imami, Ibadi, and Zaydi assets. Full
records must match the declared local source byte-for-byte; excerpts require
exact start/end bounds. OpenITI identity composes parsed ID, hadith number, and
page reference. Expected branches preserve source order and represent
co-transmitters as parallel alternatives.

**FR-0.5.2 — Candidate algorithms.** Implement at least four in `datasets/hadith-data/algo_candidates/`. Each candidate exports a single function `extract_branches(text_ar) → list[list[str]]` with the same contract. Candidates to evaluate:

| ID | Name | Strategy |
|---|---|---|
| `A` | `simple_set` | The original spec proposal: verb-split tokenizer + set intersection on `_norm`'d tokens. Baseline. |
| `B` | `name_span` | Run the existing `extract_classical_isnad` (which preserves full Arabic name tokens like "سماك بن حرب") on each ح-segment independently; then set-intersect those clean name lists. |
| `C` | `lcs_suffix` | Compute the longest common suffix (LCS) of the post-verb-split token sequences across branches; use the LCS span as the shared post-convergence segment regardless of explicit convergence-narrator detection. |
| `D` | `position_anchored` | Find the matn (everything after the last `قال`/`أن`/`عن النبي`/`عن رسول الله` or equivalent matn-attaching cue), then walk BACKWARD from the matn through the last branch identifying narrators; for earlier branches, walk backward through their text aligning to the last-branch suffix by name match. |
| `E` (optional) | `no_stitch_fallback` | Don't attempt stitching at all; just emit each ح-segment as an independent branch. The "do nothing" baseline — Phase 1 work must beat this. |

**FR-0.5.3 — Comparison harness.** Build `datasets/hadith-data/algo_evaluate.py` that, for each candidate × each labeled fixture, computes:
- **Branch-count accuracy:** % of fixtures where `len(actual) == len(expected)`.
- **Per-branch narrator-set Jaccard:** for matched branches by index, intersection-over-union of the surface-form sets. Reported as median + p25/p75.
- **Per-branch narrator-list edit distance:** Levenshtein on the position-ordered list (rewards correct order, not just membership).
- **Resolver-rate proxy:** % of the candidate's produced surface forms that resolve to a `scholar_indx` via the existing `resolve_narrator` (predicts downstream chain-data quality).
- **No-stitch-correct-anyway rate:** rows where candidate D's "do nothing" is actually within a Jaccard-0.9 ball of the gold — informs when stitching is necessary vs. cosmetic.

Output: a Markdown table per metric, signed off in `.omc/research/uniform-isnad/algo-evaluation.md`.

**FR-0.5.4 — Winner-pick policy.** The canonical candidate must:
- Achieve overall branch-count accuracy ≥ 0.90 across the gold set.
- Achieve median per-branch Jaccard ≥ 0.90.
- Achieve median normalized ordered edit similarity ≥ 0.90.
- Achieve per-tradition branch-count accuracy and mean ordered similarity ≥ 0.80.
- Tie-breakers: simpler implementation > better edge-case behavior > faster.

If no candidate clears the bar, **FR-1 is replanned**: the spec is amended to specify a hybrid (e.g., "use candidate B's name-span detection, but when set-intersect returns empty, fall back to candidate C's LCS"), and the bake-off is re-run on the hybrid before Phase 1 proceeds.

### FR-1 — Single taḥwīl-aware extractor

**FR-1.1** — New module `datasets/hadith-data/extract_isnad_unified.py` exports:

```python
def extract_isnad_branches(text_ar: str) -> list[list[str]]:
    """Parse a classical Arabic isnad text into one branch per ح-separated isnad.

    Each branch is the full ordered list of narrator surface forms from the
    initial transmitter through the shared post-convergence segment to the
    Companion / Imam / Prophet.

    Algorithm: **candidate C (lcs_suffix), hardened** — initially picked by
    the historical FR-0.5 bake-off on 2026-06-11. See
    `.omc/research/uniform-isnad/algo-evaluation.md` and the two bake-off
    findings files. The old five-row Round-2 results were:
      - branch-count accuracy: 1.000
      - Jaccard median: 0.845 (FR-0.5.4 bar: 0.80)
      - Jaccard p25: 0.625 (highest of all candidates)
      - Jaccard mean: 0.776

    C was chosen over B (which tied on median) because C correctly handled
    muslim-1, a case where the same compiler-narrator opens both ح-branches.
    B's set-intersection approach overwrote both branches with the same
    shared-suffix view; C's longest-common-suffix approach correctly kept
    them distinct. Both branches in muslim-1 emerge identical under B (a
    correctness regression); under C they are different chains as expected.

    Promotion path:
      - The canonical implementation lives in this module.
      - The historical `algo_candidates/` tree remains a comparison baseline.
      - Parsing helpers are canonical here because diacritics, co-transmitters,
        matn boundaries, weak-pronoun convergence, and branch-local fuller
        convergence surfaces required fixes beyond `_common.py`.
    """
```

The algorithm steps below are common to every candidate; the candidate-specific bits live in the chosen implementation under `algo_candidates/`:

1. **Detect ح-splitter positions.** Lone ح preceded by ، or whitespace, followed by و? + a transmission verb (حدثنا|حدثني|أخبرنا|أنبأنا|ثنا|نا) signals taḥwīl. Multiple ح in one isnad are allowed (3-branch and 4-branch hadiths exist — see Phase 0 stats). Detector regex shared with `audit_tahweel_stats.py`.
2. **Split into segments.** Pre-ح + each post-ح clause. Track segment ordering.
3. **Find the convergence narrator** OR **the shared post-convergence segment** depending on the chosen candidate's strategy (set-intersect, name-span intersect, LCS suffix, or matn-anchored backward walk).
4. **Construct full branches.** Keep the complete earlier branch, including its own convergence spelling, and append only the unmatched last-branch tail.
5. **No-stitch fallback.** When the chosen algorithm can't find a shared segment (Phase 0 estimates this at 10-15% of taḥwīl hadiths even with the best candidate), emit each branch as its own truncated chain. This is correct, just incomplete.
6. **Apply canonical source-surface cleaning.** Ignore vocalization/tatweel for parsing, remove honorific and narrative frames, retain lexical source wording and pronouns, and never resolve identity in the extractor.
7. **Expand co-transmitter levels.** A conjunction at one transmission level
   creates source-ordered alternative branches. Two such levels form the
   Cartesian set of valid routes; the paired names never become adjacent
   teacher/student nodes merely because they share a clause.

**FR-1.2** — New module exports a companion resolver:

```python
def resolve_branches_to_indxs(
    branches: list[list[str]],
    resolve_narrator: Callable[[str], int | None]
) -> list[list[int]]:
    """Resolve all branches atomically through the cited narrator index."""
```

Reuse the existing bilingual `resolve_narrator`. Any unresolved, ambiguous,
invalid, or non-positive value raises `UnresolvedNarratorError`; callers may
record telemetry and emit an empty whole-row cell, but never a partial branch.

**FR-1.3** — Unit-tested with the cases:
- (a) Tirmidhi #1 — 2-branch convergence at Smāk
- (b) Tirmidhi #3 — 3-branch convergence
- (c) A no-taḥwīl Bukhari row (single chain) — must produce one branch identical to current behavior
- (d) An Imami Al-Kāfī row with isnad in `arabicText` (no ح) — single branch
- (e) A pathological 4-branch hadith if one exists in the corpus
- (f) An empty `text_ar` — returns `[]`
- (g) Text with ح inside a quoted matn (not an isnad ح) — should not split

Acceptance first occurs in a disposable local graph: Tirmidhi #1 has Branch A
= [Qutayba, Abū ʿAwāna, Smāk, Muṣʿab b. Saʿd, Ibn ʿUmar] and Branch B =
[Hannād, Wakīʿ, Isrāʾīl, Smāk, Muṣʿab b. Saʿd, Ibn ʿUmar].

### FR-2 — Multi-branch `chain_indx` CSV format

**FR-2.1** — Extend the `chain_indx` column format to encode multiple branches.

Decision: **`|`-separated branches, `,`-separated within branch.** Example: `30367,20469,10770,10556,18|30480,20032,20311,10770,10556,18`.

Rationale:
- Backwards compatible — single-chain rows have no `|`, parse the same.
- The TS `parseIndices()` (`src/scripts/lib/regen/io.ts`) already strips `[` and `]` and splits on `,` after `.trim()` — only needs a `.split('|')` outer layer added.
- The Python writer just `'|'.join('|'.join(','.join(branch) for branch in resolved_branches))`.

**FR-2.2** — Update `src/scripts/lib/regen/io.ts`:

```ts
function parseIndices(s: string): number[][] {
    const stripped = s.trim().replace(/^\[|\]$/g, '');
    if (!stripped) return [];
    return stripped.split('|').map(branch =>
        branch.split(',').map(t => parseInt(t.trim(), 10)).filter(n => !isNaN(n))
    ).filter(b => b.length > 0);
}
```

Change `UnifiedRow.chain_indx` type from `number[]` to `number[][]`. Update `buildTier1Resolution` in `load-chain.ts` to iterate over branches and emit one `NarratorResolutionResult` per branch with distinct `chain_index` values (0, 1, 2, …).

**FR-2.3** — Migration shim. The existing CSV in production has single-chain `chain_indx` (no `|`). The new parser must read those as a single-branch list of one element. This is automatic given the `split('|')` semantics — a string without `|` splits to a single element. No CSV migration step required.

### FR-3 — Apply uniformly to all source paths

**FR-3.1** — In `regen_unified_csvs.py`, replace the three divergent `chain_indx` writers with a single call:

```python
def _compute_chain_indx(text_ar: str, fallback=None,
                       resolve_narrator=None) -> str:
    """Resolve canonical Arabic branches atomically into a CSV cell."""
```

Call sites that change:
- K6 assembly — overwrite legacy `chain_indx` from Arabic. Keep sidecar
  `sanad`/`matn_ar` enrichment for display only; never use it as an ID fallback
  when Arabic exists.
- `openiti_to_clean_row` / `openiti_to_shia_row` — call the canonical Arabic
  resolver and retain structured upstream sanad only for display/cross-checks.
- `load_classical_sunni_rows` (existing Musnad Ahmad path) — replace the inline `extract_classical_isnad` + flat `','.join(resolved_indxs)` with `_compute_chain_indx(text_ar=chain_text, fallback=None, ...)`.

**FR-3.2** — `datasets/hadith-data/shia-hadith/build_csv.py` (W2's Fix B output): the current `thaqalaynSanad` English-string path produces low resolution (~14%) because English ibn/bn variants don't match the rawi `name` field cleanly. **Replace** it with reading `arabicText` from the v2_books JSON and running the new uniform extractor on it. The v2_books data has `arabicText` populated on 100% of rows per the 2026-06-05 survey — that's a higher-quality input than the English `thaqalaynSanad`.

**FR-3.3** — Remove `datasets/hadith-data/shia-hadith/extract_thaqalayn_sanad.py` once FR-3.2 lands. The English splitter becomes dead code. Move it to `datasets/hadith-data/shia-hadith/archive/` per the project memory rule about never deleting data files (this is parser code, but the rule generalizes to anything we may want to reference later).

### FR-4 — Optional Prophet/Imam anchor

**FR-4.1** — When the post-convergence segment ends at an attribution to the Prophet ﷺ (regex: `عن النبي|عن رسول الله|قال رسول الله`) or to an Imam (regex includes `قال أبو عبد الله|قال الباقر|قال الصادق` etc.), emit the Prophet/Imam as the final narrator with `scholar_indx=1` (Prophet) or the canonical Imam scholar_indx. Make this **opt-in via a `--include-anchor` flag** on `regen_unified_csvs.py`; default off for this track to keep the schema change minimal. The graph-analytics track will turn it on once it has anchor-aware queries.

Rationale: with the anchor, every Sunni chain naturally terminates at scholar_indx=1, enabling shortest-path queries from any narrator to the Prophet. Without it, the chain ends at the Companion, which is the classical convention. Both are valid; expose the choice.

### FR-5 — Resolver-rate improvements (the kunya gap)

**FR-5.1** — Add kunya / nasab alias indexing to `build_narrator_index` in `regen_unified_csvs.py`.

Current behavior (verified 2026-06-06): the rawi `name` column has surface like `"Wadah bin 'Abdullah al-Yashkari وضاح بن عبد الله اليشكري  أبو عوانة"`. `_extract_arabic_name` pulls Arabic chars and joins them, producing `"وضاح بن عبد الله اليشكري ابو عوانة"`. The kunya `أبو عوانة` alone matches as a suffix via Tier-2 containment IF it's the unique entry in its block — but there are multiple `أبو عوانة` narrators (e.g., scholar_indx 36688), so the block has >1 candidate and Tier-2 returns None.

Fix: parse the `name` field into segments (English part, Arabic name part, kunya part, honorific tail), index each segment as an alias to the same scholar_indx, and **for ambiguous kunyas, use the rawi metadata fields (`death_date_hijri`, `area_of_interest`, `teachers`, `students`) to disambiguate at resolution time** — pick the kunya match whose `death_date_hijri` is closest to the chain's expected era (inferred from adjacent narrators' eras).

If FR-5 is too large for this track, scope it down to: just index the kunya as an alias when only one entry has that kunya (covers ~80% of kunya gaps). The ambiguous-kunya disambiguator becomes its own follow-up.

**Acceptance:** Tirmidhi #1's `أبو عوانة` resolves to 20469 cleanly.

### FR-6 — Differential repair against live Neo4j (NOT fullregen)

**FR-6.1 — New `--mode=repair` in `regen-isnad-graph.ts`.** Implements §1.1's contract. Creates `src/scripts/lib/regen/mode-repair.ts` parallel to `mode-fullregen.ts`. Reuses every loader, schema-init, narrator-merge, and stat-reporting helper. The ONLY new logic is the per-hadith diff + surgical repair pass that replaces the streaming flush-buffer loop.

Per-hadith repair algorithm:

```
For each row in unified CSV:
  (1) compute new branches = extract_isnad_branches(row.text_ar)
      resolved_branches    = resolve_each(branches)         (list[list[scholar_indx]])
  (2) fetch live state:
      MATCH (h:Hadith {dataset_row_id: $id})-[:HAS_CHAIN]->(c:Chain)
            -[i:INCLUDES]->(n:Narrator)
      RETURN c.id, c.chain_index, collect({pos: i.position, indx: n.scholar_indx})
      ORDER BY c.chain_index
  (3) compute diff(live, new) → set of granular actions:
      - chain_added       : new branch index has no live :Chain
      - chain_removed     : live :Chain has no corresponding new branch (rare)
      - narrator_added    : new branch has narrator not in live :Chain at same chain_index
      - narrator_removed  : live :Chain has narrator not in new branch
      - position_changed  : same narrator, new position
  (4) if diff is empty → log {action: 'unchanged', row: rowNum} and continue.
  (5) apply actions in a single transaction per hadith:
      - All adds/removes/position updates scoped to the affected :Chain nodes only.
      - Tombstone the affected :Chain's INCLUDES edges that match `narrator_removed`
        (DELETE r, write tombstone marker on the :Chain itself with timestamp + dvId
         for audit). NEVER touch :INCLUDES edges of other Hadith's chains.
      - CREATE the new :INCLUDES edges for `narrator_added`.
      - SET r.position = newPos for `position_changed` matches.
      - For `chain_added`, MERGE new :Chain + HAS_CHAIN, then add INCLUDES.
      - For `chain_removed`, soft-tombstone the :Chain (mark `chain.active = false,
        chain.tombstoned_at = datetime(), chain.tombstoned_by = $dvId`); do NOT
        DETACH DELETE it. The reified history is preserved for audit.
  (6) per-row :NARRATED_FROM: for each (n[i], n[i+1]) in new branch's resolved list,
      MERGE (student:Narrator)-[r:NARRATED_FROM]->(teacher:Narrator)
      ON CREATE SET r.confidence = ..., r.source = $dvId.
      Do NOT delete stale :NARRATED_FROM edges — they may be co-derived from other
      hadiths' chains. Edge cleanup is a downstream concern.
  (7) emit per-row JSON to logs/regen-repair-<dvId>.jsonl:
      {action, row, hadith_id, chains_added, chains_removed, narrators_added,
       narrators_removed, narrators_repositioned, errors}
```

**FR-6.2 — Forbidden patterns in `mode-repair.ts`.**
- ❌ `MATCH ()-[r:INCLUDES]->() DELETE r` (any global delete)
- ❌ `MATCH ()-[r:NARRATED_FROM]->() DELETE r` (any global delete)
- ❌ `loadChainsBatchFresh` (uses CREATE blind — assumes empty-edge precondition)
- ❌ `DETACH DELETE (c:Chain)` (use soft-tombstone instead)
- ✅ `loadChainsBatch` (MERGE-based, safe) — but per-hadith, not buffered
- ✅ Per-Cypher targeted edge `DELETE` scoped via `MATCH (h:Hadith {dataset_row_id: $id})-[:HAS_CHAIN]->(:Chain)-[r:INCLUDES]->(:Narrator {scholar_indx: $sid}) DELETE r`

**FR-6.3 — Backup-first.** Before mode-repair starts the per-row loop, snapshot the affected `:Chain` and `:INCLUDES` topology to a JSONL backup file at `logs/regen-repair-<dvId>-pre-snapshot.jsonl`. Format: one line per `:Hadith`, containing `{id, chains: [{chain_id, narrators: [{position, scholar_indx}]}]}`. Sized at ~50-100 MB. Enables a rebuild-from-backup if a bug in mode-repair corrupts state mid-pass.

**FR-6.4 — Resume.** Mode-repair must support `--resume-from-row N` and emit a checkpoint to `logs/regen-repair-<dvId>-checkpoint.json` every 500 rows containing `{last_row_processed, last_hadith_id, counts}`. A killed-and-restarted run picks up from the last checkpoint, not from row 0.

**FR-6.5 — Dry-run mode.** `--mode=repair --dry-run` performs the diff for every row, emits the per-row JSON to a `dry-run` log, but writes nothing to Neo4j. Used during track development to validate the diff logic before any live writes.

**FR-6.6 — Acceptance check on live Neo4j (via `src/scripts/diagnose-chain-data.ts`):**
- Tirmidhi #1: exactly 2 `:Chain` nodes attached, each with ≥5 narrators ending at Ibn ʿUmar.
- K6 average narrators per chain: in [4.5, 6.5] (vs current 3.2–4.1 — taḥwīl-aware should be longer because we now include the shared post-convergence segment).
- K6 average chains-per-hadith: in [1.3, 2.0] (most hadiths are single-chain; taḥwīl is a sizable minority).
- Al-Kāfī: rows with non-empty chain ≥ 80% (vs current 61%).
- Musnad Zayd: rows with non-empty chain ≥ 70% (vs current 0%).
- Zero K6 chains with > 12 narrators (a sanity ceiling — anything longer is parse error).
- **Zero `:Hadith` nodes that lost all `:HAS_CHAIN` edges during repair** (every hadith that had a chain before still has at least one chain after, even if its narrators changed). This is the non-destructive guardrail's measurable contract.

## 4. Non-Functional Requirements

**NFR-1** — Idempotency. Re-running `regen_unified_csvs.py` produces byte-identical CSV. Re-running `--mode=repair` against an already-repaired Neo4j produces ZERO writes — every row's diff comes back empty, every row logged as `unchanged`.

**NFR-1a — Non-destructive operation (HARD INVARIANT).** Mode-repair MUST NOT use any global graph mutation. Specifically:
- No query that matches edges without a `:Hadith {dataset_row_id: $id}` anchor.
- No `DETACH DELETE` against `:Chain`, `:Hadith`, `:Narrator`, or `:Assessment`.
- No drop of an entire relationship type via APOC or otherwise.
- Hand-curated edges (any `:INCLUDES` or `:NARRATED_FROM` whose `source` property does not start with `dv-` — i.e., not from a regen dataset version) are NEVER touched. Mode-repair MUST `WHERE r.source STARTS WITH 'dv-'` filter every deletion. Manual / HITL edges are preserved by definition.

Test: run mode-repair against a Neo4j that has been hand-augmented with an extra `:INCLUDES` edge of `r.source = 'human:hitl-2026-06-15'`. After repair, the human edge MUST still exist.

**NFR-2** — Backwards compatibility on the read path. Existing `getFullChainGraph` server action in `src/app/actions/graph-actions.ts` queries `(h)-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator)` and orders by `i.position`. Multi-chain hadiths will now return narrators from multiple chains, and the UI's `IsnadChain` / `IsnadGraph` components need to either:
- (a) Group narrators by `(c.id)` and render one chain per `:Chain`, OR
- (b) Continue collapsing them all into one flat view (which would *re-introduce* the visual bug the user reported).

This track owns (a). Add a chain-grouped variant of `getFullChainGraph` and update the UI to render N chain-rows when N > 1.

**NFR-3** — Test coverage uses Python standard-library `unittest` and covers
single/multi-chain extraction, co-transmitter alternatives, no-convergence,
embedded ح, honorific stripping, atomic resolution, exact provenance, ordered
quality, and per-tradition floors.

**NFR-4** — Performance. The extractor runs on 99,283 hadiths during CSV rebuild. Per-hadith budget: ≤ 50ms. Total: ≤ 90 min for full CSV rebuild on the user's machine (current rebuild is ~10 min — taḥwīl handling adds parse cost but resolution rate goes up, so net should be comparable).

## 5. Seven Enforceable Guardrails

Each is an acceptance criterion with a test.

**G-1 — Independent branches preserved.** A 2-branch taḥwīl hadith produces 2 distinct `:Chain` nodes attached to the same `:Hadith` via `:HAS_CHAIN`, not one merged chain. Test: query Tirmidhi #1, assert `count(c:Chain) == 2`.

**G-2 — Convergence narrators in both chains.** A narrator at the convergence point appears in both chains. Test: query Tirmidhi #1, assert Smāk b. Ḥarb (scholar_indx=10770) appears in INCLUDES edges of both Chain nodes.

**G-3 — Shared post-convergence segment.** The narrators after the convergence point appear in BOTH chains. Test: query Tirmidhi #1, assert Muṣʿab b. Saʿd (scholar_indx=10556) and Ibn ʿUmar (scholar_indx=18) appear in both Chain nodes' INCLUDES edges.

**G-4 — No information loss vs. taḥwīl-naive baseline.** Every narrator that the old buggy `chain_indx` referenced is still present in at least one of the new chains. Test: union the new branches' narrator sets per hadith, compare against the old `chain_indx` flat set, assert superset.

**G-5 — UI honors chain separation.** The `/hadith/[id]` page renders N visual chains for a hadith with N `:Chain` nodes, not one flat union. Manual visual test on Tirmidhi #1 post-rebuild.

**G-7 — Non-destructive repair.** Mode-repair never performs a global edge wipe. Tested by: (a) hand-augmenting a test Neo4j with a `:INCLUDES` edge of `r.source = 'human:hitl-test'`, (b) running mode-repair on Tirmidhi #1, (c) asserting the human edge survives. Plus: no `:Hadith` that had ≥1 `:Chain` before repair has 0 `:Chain` after (counted across all 99,283 rows; assert via Cypher delta query).

**G-6 — Per-tradition coverage floor.** The local candidate manifest emits
present/missing/invalid/unknown-reference counts by tradition, and the local
graph dry run meets approved coverage floors before any cutover request.

## 6. Out of Scope

- English-isnad parsing for the Imami collections (deferred to a future track if `thaqalaynSanad` English path is ever needed again).
- Cross-tradition narrator unification (a Sunni "Muḥammad b. Ismāʿīl" and an Imami "Muḥammad b. Ismāʿīl" may or may not be the same person — that's `narrator_enrichment_20260425`).
- Probabilistic isnad authentication (different track).
- Multi-isnad scoring / *mutawātir* candidate surfacing (gds_setup_analytics_20260425).
- Wiping the existing live INCLUDES edges (already handled by mode-fullregen.ts's global wipe step added 2026-06-08).
- Fix the `loadChainsBatchFresh` NARRATED_FROM duplication issue (documented in batch-loaders-fresh.ts header; acceptable for this track's scope).

## 7. Technical Considerations / Decisions Made

**TC-1 — Why one Python extractor not three.** The classical Sunni extractor at `extract_classical_isnad` already handles 80% of the parsing surface (the verb splits, honorific stripping, punctuation). Adding taḥwīl-awareness is a 50-line wrapper around it, not a rewrite. Keeping three diverging extractors (sidecar-array, English-narration, OpenITI-sanad_detail) is the source of the bug — collapsing to one is the fix.

**TC-2 — Why `|` delimiter not new column.** The CSV is already 170 MB. Adding a column means rewriting every row; using a delimiter inside an existing column means only the affected rows change. Diff-friendly.

**TC-3 — Why not also do multi-chain in `:NARRATED_FROM`.** Each `:Chain` already emits its own `:NARRATED_FROM` chain via `load-chain.ts`. With two chains converging at C and extending to H, the edge C→G is emitted twice (once per chain). The fresh-loader uses CREATE-not-MERGE, so this produces a duplicate edge. Documented in `batch-loaders-fresh.ts` header; will be deduplicated by the narrator-enrichment track's `:SAME_AS` reconciliation pass. Not blocking.

**TC-4 — Why Prophet/Imam anchor is opt-in.** Anchoring every chain at scholar_indx=1 inflates the Prophet's :INCLUDES adjacency list by ~99k edges. That's fine for graph queries but makes the node a supernode that slows down narrator-degree computations. The GDS track owns the decision on when to flip it.

**TC-5 — Python extractor language choice.** Stays Python. The CSV builder is Python; reusing existing regexes (`_CHAIN_VERB_SPLIT`, `_AAN_SPLIT`, `_CLASSICAL_HONORIFIC`) is cheaper than re-implementing in TS. The TS side only needs the `|`-aware parser update.

## 8. Dependency Edges

- **Depends on:** `neo4j_isnad_graph_regen_20260516` (the reified `:Chain` schema, the multi-isnad-aware `loadChainForRow`, the wipe-before-fullregen pattern added 2026-06-08).
- **Blocks:**
  - `narrator_enrichment_20260425` — kunya gaps from FR-5 must close before narrator bios are useful.
  - `gds_setup_analytics_20260425` — *mutawātir* candidate surfacing depends on multi-branch separation from FR-1.
  - `vector_embedding_pipeline_20260425` — per-chain embeddings need stable chain boundaries.
- **Does not block / parallel with:** `grade_normalization_20260425`, `scholarly_metadata_layer_20260425`, `comparative_ingestion_20260322`.

## 9. Open Questions

**Q1 — `arabicText` vs `text_ar` for Imami.** The Thaqalayn v2_books JSON has both `arabicText` (richly diacriticized) and the OpenITI fallback. The 2026-06-05 survey showed 100% coverage on `arabicText`. Confirm the diacritics don't break `_norm`; if they do, strip them.

**Q2 — How deep does taḥwīl nesting go?** Most are 2-branch. Tirmidhi #3 was 3-branch. Are there 4+ branch hadiths in the corpus? Quick grep on `text_ar` for occurrences of `ح وحدثنا` per row will tell us — file a small audit as the first task.

**Q3 — Prophet anchor scholar_indx.** Confirm `scholar_indx=1` is the Prophet in `all_rawis.csv` (the runbook addendum claims so). Imami scholar indices for Imams need confirmation against `all_rawis.csv`'s Imami coverage.

## 10. Acceptance Gate Summary

| Gate | Criterion | Test |
|---|---|---|
| G-1 | Tirmidhi #1 has 2 `:Chain` nodes | Cypher count |
| G-2 | Convergence narrators in both chains | Cypher intersect |
| G-3 | Post-convergence segment in both | Cypher membership |
| G-4 | Superset of old chain_indx narrators | Set comparison |
| G-5 | UI renders N separate chains | Manual test |
| G-6 | Per-tradition coverage floors | Diagnose script |
| G-7 | Non-destructive repair (human edges preserved, zero hadiths lose all chains) | Cypher delta + injected-human-edge fixture |

Pass all seven plus the independent evaluator and local dry run → request a
separately approved production cutover. No gate automatically authorizes a
remote write.
