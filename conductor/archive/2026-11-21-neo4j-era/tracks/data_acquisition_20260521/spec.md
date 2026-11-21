# Specification: Hadith Dataset Acquisition

**Track ID:** `data_acquisition_20260521`
**Type:** Feature (data engineering)
**Created:** 2026-05-21
**Status:** Planned
**Priority:** P1
**Depends on:** —
**Blocks:** `neo4j_isnad_graph_regen_20260516` (re-runs after each acquisition wave),
            `gds_setup_analytics_20260425` (richer corpus → better community detection)

---

## 0. Why this track exists

The current unified hadith CSV (99,283 rows / 32 sources) has **two classes of
gaps** that block end-to-end usefulness:

1. **Missing grading data on 70% of rows** (notably **all 34,441 Sunni K6
   hadiths** have 0% scholar-verdict data).
2. **Missing whole collections** that any serious hadith research workflow
   needs (the deep Imami corpus, Sunni encyclopedic works, additional Zaydi /
   Ibadi works).

The pipeline (`neo4j_isnad_graph_regen_20260516`) is correctly architected to
*consume* whatever ends up in `all_hadiths_unified.csv` and `all_rawis.csv` — it
won't fail on a richer corpus. The bottleneck is data acquisition. This track
focuses on the gaps **NOT already covered** by:

- `translate_classical_collections_20260418` (Sunni-classical English)
- `grade_normalization_20260425` (canonicalizing grades that already exist)
- `narrator_enrichment_20260425` (filling in 16k narrator name_arabic / death_year_hijri / etc.)

---

## 1. Coverage audit (2026-05-21 baseline)

| Tradition | Rows | Sources | text_en gap | chain_indx gap | grading gap |
|---|---|---|---|---|---|
| Sunni K6 | 34,441 | 6 | ~5% (small) | <1% (small) | **100%** (no scholar verdicts) |
| Sunni classical | 29,915 | 4 | **100%** (handled by `translate_classical_collections_20260418`) | Shafi'i 100% (allowed) | 0% (grades present) |
| Imami | 33,225 | 20 | 0% | variable (Al-Kafi 97% / Nahj 0%) | major works only have `gradings_full` for Al-Kafi (98%); others 0-6% |
| Ibadi | 1,004 | 1 | 0% | **100%** (no chain_indx, has sanad — pipeline-side fix in `neo4j_isnad_graph_regen` Tier-2) | 100% |
| Zaydi | 698 | 2 | 0% | **100%** (same — pipeline-side fix) | 100% |

The **30% of rows that DO have `grade_value`** are entirely Sunni-classical
(Ahmad/Darimi/Shafi'i/Muwatta = 29,915 rows, all 100% scalar grade from the
source ingestion).

---

## 2. Functional requirements

### FR-1 — Sunni K6 al-Albani grading ingestion

Source: **sunnah.com** (public domain English + grade per hadith for the 5 sunan
that have al-Albani assessments). Bukhari + Muslim are *sahih by consensus* by
inclusion in their respective collections — encode as `grade_value='sahih',
grade_source='consensus'`.

Targets:
- Sahih Bukhari (7,370 rows) → `grade_value='sahih'`, `grade_source='consensus'`
- Sahih Muslim (7,596 rows) → `grade_value='sahih'`, `grade_source='consensus'`
- Sunan Abi Da'ud (5,260 rows) → al-Albani grade scrape
- Jami' al-Tirmidhi (4,214 rows) → al-Albani grade + Tirmidhi's own grade
- Sunan an-Nasa'i (5,774 rows) → al-Albani grade
- Sunan Ibn Majah (4,227 rows) → al-Albani grade

Total: **34,441 rows** acquire grading.

Tooling: HTTP scrape with rate-limiting (sunnah.com Terms accept respectful
scraping; cache to local JSONL). Map each row to its `dataset_row_id` via
`source + hadith_no` join.

Output: `datasets/hadith-data/k6_grades.jsonl` with schema:
```json
{"dataset_row_id": 123, "source": "Sahih Bukhari", "hadith_no": "1",
 "grade_value": "sahih", "grade_source": "consensus", "grade_tradition": "Sunni"}
```

### FR-2 — Major Imami collection additions

The current Imami corpus has 20 works but is missing the other two of the
canonical Four Books and the major encyclopedic compilations:

| Collection | Compiler | Est. rows | Source |
|---|---|---|---|
| Tahdhib al-Ahkam | al-Shaykh al-Tusi | ~13,500 | OpenITI |
| al-Istibsar | al-Shaykh al-Tusi | ~5,500 | OpenITI |
| Bihar al-Anwar | al-Allama al-Majlisi | ~50,000 (a *huge* compilation) | OpenITI |
| Wasa'il al-Shi'a | al-Hurr al-Amili | ~35,000 | OpenITI |
| Mustadrak al-Wasa'il | Mirza al-Nuri | ~23,000 | OpenITI |

Per [`arabic_ocr_research.md`](../../memory/) memory: OpenITI has clean text for
these — no OCR needed.

Total potential acquisition: **~127,000 rows** (could more than double the
unified corpus).

### FR-3 — Major Sunni collection additions

The current Sunni corpus has 10 works but is missing the post-K6 encyclopedic
compilations widely cited in academic isnad criticism:

| Collection | Compiler | Est. rows | Notes |
|---|---|---|---|
| al-Sunan al-Kubra | al-Bayhaqi | ~21,000 | major isnad source |
| Sahih Ibn Hibban | Ibn Hibban | ~7,500 | structured by topic |
| Sahih Ibn Khuzayma | Ibn Khuzayma | ~3,000 | |
| al-Mu'jam al-Kabir | al-Tabarani | ~30,000 | sahabi-organized; vast |
| al-Mu'jam al-Awsat | al-Tabarani | ~9,000 | |
| al-Mu'jam al-Saghir | al-Tabarani | ~1,200 | |
| al-Mustadrak | al-Hakim | ~9,000 | |
| Musannaf | Abd al-Razzaq al-San'ani | ~21,000 | early; key for sanad criticism |
| Musannaf | Ibn Abi Shayba | ~38,000 | early; key for sanad criticism |

Total potential acquisition: **~140,000 rows**.

### FR-4 — Extended Zaydi & Ibadi works

| Collection | Tradition | Est. rows |
|---|---|---|
| al-Amali al-Khamisiyya (al-Shajari) | Zaydi | ~2,500 |
| Amali Ahmad ibn Isa | Zaydi | ~1,200 |
| Majmu' al-Imam Zayd | Zaydi | ~1,000 |
| Tartib al-Jami al-Sahih (Ibn Barakah, Ibadi reorg) | Ibadi | ~1,200 |
| Sharh al-Jami al-Sahih (Salimi commentary chains) | Ibadi | derivative |

Total: **~6,000 rows** across both traditions.

### FR-5 — Per-source acquisition isolation

Each collection acquisition is an INDEPENDENT subtrack with its own:
- Source URL / pipeline (OpenITI XML/JSON → JSONL → unified CSV append)
- Quality verification (record count matches published volume counts)
- Per-source translation status (most are Arabic-only; English is FR-6)
- Updates to `src/lib/constants/sources.ts` (new entry per collection)
- Update to `datasets/hadith-data/regen_unified_csvs.py` to include the new
  source in the unified CSV builder

This means each collection is independently committable. The regen track can
re-run cleanly after each acquisition wave.

### FR-6 — English translation expansion (out of scope; references)

English translation for the new Imami / additional Sunni / Zaydi / Ibadi works
is **deferred to `translate_classical_collections_20260418`** (extend its
scope) or a future track. This acquisition track produces Arabic + sanad +
chain_indx where possible; translation is a separate concern.

### FR-7 — Rijal data extension

`all_rawis.csv` covers ~24,326 narrators but the `classical_narrator_gap.csv`
shows 13,413 unresolved surface forms in the classical Sunni corpus (i.e.,
narrators referenced in chains that aren't in the rijal dataset). Per spec
NFR-3, those resolutions are quarantined.

This track DOES NOT extend the rijal dataset — that's
`narrator_enrichment_20260425`'s job. But this track must ensure that any new
collection it adds is run through entity resolution against the EXISTING
`all_rawis.csv` and unresolved names get added to `classical_narrator_gap.csv`
(handoff to the enrichment track).

---

## 3. Non-functional requirements

- **NFR-1 — Idempotent acquisition.** Each subtrack must be re-runnable. Re-run
  produces no diff if the source upstream is unchanged.
- **NFR-2 — No-delete policy.** Existing CSV rows are never removed by an
  acquisition. The unified CSV builder always re-emits everything that was in
  before + the new source.
- **NFR-3 — Tradition-source consistency.** Every new source MUST be added to
  `src/lib/constants/sources.ts` with the correct `tradition` field. The regen
  pipeline rejects unregistered sources with a warning (per `passoff-v2.md`
  H3-H).
- **NFR-4 — Bibliographic provenance.** Each source entry in
  `CANONICAL_SOURCES` MUST include `compiler` and (where known) `school` for
  proper academic citation.
- **NFR-5 — Pre-acquisition gap reporting.** Before each acquisition, run a
  one-shot coverage report on the target source's metadata (page count, hadith
  count if known, language) so the operator can sanity-check the result.

---

## 4. Acceptance gates

Each subtrack independently satisfies:

1. **Gate A0 (per-source)**: Source registry entry exists in
   `src/lib/constants/sources.ts` BEFORE any data lands.
2. **Gate A1 (per-source)**: New rows appear in `all_hadiths_unified.csv` at
   expected counts (±2% of published volume).
3. **Gate A2 (per-source)**: `tradition` field matches the registry; no rows
   with unknown source name.
4. **Gate A3 (per-source)**: `dataset_row_id` (CSV column `id`) is uniquely
   assigned and not reused.
5. **Gate A4 (per-source)**: `text_ar` populated for every row. (English may
   be empty — handed off to translation track.)
6. **Gate A5 (per-source)**: `sanad` extracted where the source has explicit
   isnad chains; `chain_indx` left empty until Tier-1/2/3 resolution runs.
7. **Gate A6 (whole track)**: After all subtracks complete, the unified CSV
   passes spec §9b assertions (run `npm run db:regen -- --mode=test` on a
   throwaway DB).

---

## 5. Cross-references

- Pipeline that consumes the output: `neo4j_isnad_graph_regen_20260516/ultrapilot-passoff-v2.md`
- Translation handoff: `translate_classical_collections_20260418`
- Grade canonicalization: `grade_normalization_20260425`
- Narrator enrichment: `narrator_enrichment_20260425`
- Memory: `arabic_ocr_research.md` (OpenITI has clean text for Zaydi/Ibadi)
- Memory: `feedback_no_delete_backup.md` (acquisition never deletes existing data)
