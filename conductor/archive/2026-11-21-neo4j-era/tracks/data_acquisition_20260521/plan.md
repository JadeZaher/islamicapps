# Implementation Plan — Hadith Dataset Acquisition

**Track ID:** `data_acquisition_20260521`
**Spec:** `./spec.md` (binding)

Workflow: no formal TDD (per `conductor/workflow.md`); add presence tests after
each acquisition lands (record count, source-name match, tradition consistency).
Manual commits per acquisition wave.

---

## Wave 0 — Infrastructure (do once, before any wave)

- [ ] **0.1** Add `db:rebuild-unified-csv` script to `package.json` that runs
  `datasets/hadith-data/regen_unified_csvs.py`. This becomes the canonical
  "rebuild the unified CSV from all per-source JSONL files" entry point.
- [ ] **0.2** Refactor `regen_unified_csvs.py` to take a `--include-sources`
  flag (default: all). Lets future waves add a source without changing the
  builder code each time.
- [ ] **0.3** Add a `make-source-acquisition.sh` template that scaffolds a new
  per-source acquisition (creates a directory, drops a README with the OpenITI
  link, a fetch script template, a JSONL output stub). Reduces friction for
  Waves 1–4.
- [ ] **0.4** Document the OpenITI fetch pattern in a single
  `datasets/hadith-data/README_OPENITI.md` (URL convention, JSON schema, how to
  parse). All Imami/Sunni-classical/Zaydi/Ibadi waves reuse it.

**Gate Wave-0 exit:** `npm run db:rebuild-unified-csv` produces a byte-identical
CSV to the current one (proves no regression).

---

## Wave 1 — Sunni K6 grading (FR-1, highest impact)

The 34,441 K6 hadiths currently have zero scholar verdicts. This is the most
high-leverage acquisition because K6 is the most-queried corpus.

- [ ] **1.1** Bukhari + Muslim direct: write a tiny script that emits
  `grade_value='sahih', grade_source='consensus', grade_tradition='Sunni'`
  for all 14,966 rows. Idempotent join on `(source, hadith_no)`.
- [ ] **1.2** sunnah.com scraping for the 4 sunan (Abi Da'ud, Tirmidhi, Nasa'i,
  Ibn Majah = 19,475 rows):
  - Rate-limit to 1 req / 2 sec (respectful).
  - Cache responses to `datasets/hadith-data/sunnah_com_cache/`.
  - Parse out the per-hadith al-Albani grade from the "Reference" block.
  - For Tirmidhi: also capture Tirmidhi's own grading (Hasan / Sahih / Gharib /
    etc.) into `gradings_full` alongside al-Albani's.
- [ ] **1.3** Output: append `grade_value`, `grade_source`, `grade_tradition`,
  and (for Tirmidhi) `gradings_full` to the K6 rows in
  `regen_unified_csvs.py`'s K6 builder.
- [ ] **1.4** Rebuild unified CSV. Verify: K6 `grade_value` coverage ≥ 99%.
- [ ] **1.5** Test: presence assertion in
  `src/scripts/__tests__/regen-grading-coverage.test.ts` that 0 K6 rows have
  empty `grade_value`.

**Gate Wave-1 exit:** Every K6 hadith has a grade. Unified CSV passes a re-run
of the v2 perfect-regen pass without `--allow-known-gaps`.

---

## Wave 2 — Imami Four Books completion + Bihar al-Anwar (FR-2)

The Four Books are the canonical Imami hadith corpus. We have Al-Kafi (14,245
rows) and Man La Yahduruhu al-Faqih (6,382 rows). Missing: Tahdhib al-Ahkam +
al-Istibsar. Bihar al-Anwar is the largest single Imami compilation and
critical for any serious Imami isnad work.

- [ ] **2.1** Tahdhib al-Ahkam: fetch from OpenITI
  (`0460Tusi.TahdhibAlAhkam` → JSONL → unified CSV append).
  Add `tahdhib_ahkam` entry to `CANONICAL_SOURCES`.
  Run `extract_isnad_sunni.py`-style sanad extraction (the Imami isnad format
  is compatible; reuse the regex set).
- [ ] **2.2** al-Istibsar: same pattern. OpenITI key
  `0460Tusi.AlIstibsar`. Add `istibsar` to `CANONICAL_SOURCES`.
- [ ] **2.3** Bihar al-Anwar: BIG (50k+ rows). Stream the OpenITI files in
  volume-batched chunks. Treat each tradition (the encyclopedic units) as a
  hadith record. Add `bihar_anwar` to `CANONICAL_SOURCES`.
- [ ] **2.4** Wasa'il al-Shi'a: similar bulk pattern.
- [ ] **2.5** Mustadrak al-Wasa'il: similar.
- [ ] **2.6** Rebuild unified CSV. Verify total row count ≈ 99,283 +
  acquisitions; per-source counts match published volumes within 2%.

**Gate Wave-2 exit:** All 5 Imami collections present; unified CSV total
≈ 226,000 rows (99k + 127k); regen pipeline accepts the expanded corpus.

---

## Wave 3 — Major Sunni post-K6 collections (FR-3)

These are the encyclopedic Sunni compilations academics use for sanad
criticism. Many isnad reach the Prophet via these (not via K6 directly).

- [ ] **3.1** al-Sunan al-Kubra (Bayhaqi) — 21,000 rows.
- [ ] **3.2** Sahih Ibn Hibban — 7,500 rows.
- [ ] **3.3** Sahih Ibn Khuzayma — 3,000 rows.
- [ ] **3.4** al-Mu'jam al-Kabir (Tabarani) — 30,000 rows.
- [ ] **3.5** al-Mu'jam al-Awsat (Tabarani) — 9,000 rows.
- [ ] **3.6** al-Mu'jam al-Saghir (Tabarani) — 1,200 rows.
- [ ] **3.7** al-Mustadrak (al-Hakim) — 9,000 rows.
- [ ] **3.8** Musannaf Abd al-Razzaq — 21,000 rows.
- [ ] **3.9** Musannaf Ibn Abi Shayba — 38,000 rows.
- [ ] **3.10** Rebuild + verify per-source counts.

**Gate Wave-3 exit:** 9 new Sunni sources present (~140k new rows). Unified CSV
total ≈ 366,000 rows. Regen pipeline still completes within tolerance.

**WARNING — operational impact:** at 366k rows, the regen execution time grows
roughly 3.7x (linear in row count). Plan for ~36-48 hour fullregen vs the v2
baseline. Tier-1 entity resolution coverage on these will be low (rijal dataset
predates them), so `classical_narrator_gap.csv` will grow significantly —
handoff to `narrator_enrichment_20260425` becomes essential.

---

## Wave 4 — Zaydi + Ibadi extension (FR-4)

Smaller in volume but important for tradition coverage.

- [ ] **4.1** al-Amali al-Khamisiyya (al-Shajari) — 2,500 rows.
- [ ] **4.2** Amali Ahmad ibn Isa — 1,200 rows.
- [ ] **4.3** Majmu' al-Imam Zayd — 1,000 rows.
- [ ] **4.4** Tartib al-Jami al-Sahih (Ibn Barakah Ibadi reorg) — 1,200 rows.
- [ ] **4.5** Sharh al-Jami al-Sahih (Salimi) — derivative; assess scope.
- [ ] **4.6** Rebuild + verify.

**Gate Wave-4 exit:** Zaydi total ≈ 5,400 rows (vs current 698); Ibadi total
≈ 2,200 rows (vs current 1,004). Both traditions now have meaningful corpus
size.

---

## Wave 5 — Rijal handoff + regen re-run (FR-7)

- [ ] **5.1** Run `entity-resolution.ts`'s Tier-1/2/3 against the EXPANDED
  unified CSV. Most new Imami collections will Tier-1-resolve well (chain_indx
  populated); Sunni post-K6 will have low Tier-1 coverage (rijal predates them)
  and large unresolved-name sets land in `classical_narrator_gap.csv`.
- [ ] **5.2** File a handoff to `narrator_enrichment_20260425` with the new
  gap CSV.
- [ ] **5.3** Re-run the v2 perfect-regen pass against the expanded corpus.
- [ ] **5.4** Update `verification.md` in
  `neo4j_isnad_graph_regen_20260516/` with the new acceptance numbers.

**Gate Wave-5 exit:** Neo4j graph reflects the full expanded corpus.

---

## Wave 6 — Documentation + future-proofing

- [ ] **6.1** Update `conductor/tech-stack.md` with the OpenITI fetch pattern
  and the new collection inventory.
- [ ] **6.2** Update `MEMORY.md` (auto-memory index) with a pointer to this
  track's outcomes.
- [ ] **6.3** Audit: any collection mentioned in academic papers but not yet
  in our corpus? File as follow-up acquisition for a future track.

**Gate Wave-6 exit:** Track documentation complete; tracks.md entry checked.

---

## Sequencing rationale

| Wave | Why this order |
|---|---|
| 1 (K6 grades) | Lowest cost, highest leverage. Unblocks any grade-based query. |
| 2 (Imami extension) | Imami corpus is the most "deep" already; finishing the Four Books + Bihar is the highest research value per row. |
| 3 (Sunni post-K6) | Largest acquisition (~140k rows). Wait until grade infra is proven in W1, so we don't waste time on a giant ungraded corpus. |
| 4 (Zaydi/Ibadi) | Small, low-risk. Could parallelize with W3 if needed. |
| 5 (Rijal handoff + regen) | After everything is in CSV — single re-run vs many. |
| 6 (Docs) | Last. |

---

## Out-of-scope (explicit)

- English translation of acquired Arabic-only rows → `translate_classical_collections_20260418`
- Grade canonicalization (broad-category mapping like `صحيح → sahih`) → `grade_normalization_20260425`
- Narrator biographical enrichment → `narrator_enrichment_20260425`
- Vector embeddings → `vector_embedding_pipeline_20260425`
- GDS analytics → `gds_setup_analytics_20260425`
- Schema/pipeline changes → `neo4j_isnad_graph_regen_20260516` is the authority

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenITI source schema changes | Low | Med | Cache fetched JSONL; pin a known-good snapshot date |
| sunnah.com rate-limit / ToS | Med | Low | Respectful scrape (1 req / 2s); cache locally; check ToS pre-launch |
| Bihar al-Anwar size blows memory | Med | High | Stream per-volume; never load whole CSV into memory in `regen_unified_csvs.py` |
| New collection isnad format breaks `extract_isnad_sunni.py` | Med | Med | Tier-1 resolution gracefully falls back to Tier-2; gap CSV captures the difference |
| Regen runtime balloons past 48h | High | Med | Add `--source-filter` to fullregen for incremental loads; profile before W3 |
