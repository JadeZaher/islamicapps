# Narrator Biographical Enrichment

## Problem

The data readiness audit (2026-04-25) found critical gaps in Narrator node properties:

| Field | Populated | Missing | Coverage |
|---|---|---|---|
| name_arabic | 7,733 | 16,614 | 31.8% |
| death_year_hijri | 3,845 | 20,502 | 15.8% |
| geographic_region | 14 | 24,333 | 0.1% |
| birth_year_hijri | 386 | 23,961 | 1.6% |
| tradition | 19 | 24,328 | 0.08% |

Additionally, 16,614 narrators have empty Arabic names and ~200 narrators appear as duplicates ("no identity", "no Identity").

These gaps block:
- **GDS community detection**: geographic_region is needed for contextual interpretation
- **Temporal chain validation**: death_year_hijri required to check if student could have met teacher
- **Arabic fuzzy matching**: name_arabic needed for cross-referencing with external rijal databases
- **Cross-tradition analysis**: tradition assignment required to partition graph by madhab

## Goal

Enrich Narrator nodes from the existing `scholar_indx` foreign key (which maps to external rijal databases) and from chain context (tradition of source hadiths). Target coverage:
- name_arabic: >80%
- death_year_hijri: >50%
- geographic_region: >40%
- tradition: >95%

## Constraints

- Read-only on existing narrator data; only SET new properties, never overwrite existing non-null values
- Back up current narrator state before any writes
- All enrichment scripts must be idempotent and resumable
- Log all changes for audit trail

## Success Criteria

- Re-run data-readiness-audit.ts and see all narrator fields pass (>50% coverage)
- No new orphan nodes created
- Tradition assigned to >95% of narrators based on which Source/Hadith they connect to

---

## Addendum (2026-05-24): Reasoned `jarḥ wa taʿdīl` bios

### Scope extension

Beyond the structural fields above, every non-prophet narrator with `scholar_indx`
must carry a reasoned biography drawn from classical narrator-criticism sources.
Each narrator gets two distinct quote collections plus a synthesised verdict:

- **`bio_taʿdīl`** — quoted statements of trust (e.g. *"al-Bukhārī said: thiqa
  thabt"*, *"Yaḥyā b. Maʿīn said: ṣadūq"*) explaining **why** scholars accepted him.
- **`bio_jarḥ`** — quoted statements of criticism (e.g. *"Abū Ḥātim said:
  matrūk al-ḥadīth"*, *"al-Nasāʾī said: ḍaʿīf"*) explaining **why** scholars
  impugned him.
- **`bio_summary`** — a one-paragraph synthesis (English) for the UI.
- **`reliability_consensus`** — single label drawn from the classical
  taxonomy: `thiqa | thiqa_thabt | ṣadūq | lā_baʾsa_bihi | majhūl | ḍaʿīf |
  matrūk | kadhāb | mukhtalaf_fīhi | not_applicable`. `not_applicable` is
  reserved for Prophets and angels.
- **`reliability_disagreement`** — boolean, true when critics conflict
  significantly (drives a "contested" UI badge).
- **`critic_quote_count`** — int, distinct critics contributing.
- **`is_prophet`** — boolean; if true, all bio_* fields above are omitted by
  design (Prophets are the source, not transmitters subject to jarḥ wa
  taʿdīl).

### Source priority

Per-tradition sourcing, with OpenITI providing most:

**Sunni:**
1. **Ibn Ḥajar, *Taqrīb al-Tahdhīb*** — one-word verdict per narrator, ~8000
   entries. Fast to ingest, gives baseline coverage immediately.
2. **al-Mizzī, *Tahdhīb al-Kamāl fī Asmāʾ al-Rijāl*** — gold standard, ~5500
   entries with full critic-quote chains. Richer bio_taʿdīl / bio_jarḥ.
3. **Ibn Ḥajar, *Tahdhīb al-Tahdhīb*** — abridgement of Mizzī + later additions.
4. **al-Dhahabī, *Mīzān al-Iʿtidāl*** — ~7000 impugned narrators specifically;
   fills bio_jarḥ for narrators absent from the Tahdhīb tradition.

**Shia (Imami):**
5. **al-Najāshī, *Rijāl***
6. **al-Ṭūsī, *Rijāl* + *Fihrist***
7. **al-Khūʾī, *Muʿjam Rijāl al-Ḥadīth*** (modern, comprehensive ~16k entries)

**Zaydi / Ibadi:** TBD — initial pass uses Sunni sources for shared narrators;
tradition-specific sources gathered in a follow-up.

### Pipeline (phased)

- **Phase 0 (manual seed, 20 narrators)** — hand-craft bios for the top
  supernode narrators (Abu Hurayrah, Anas, al-Zuhrī, Sufyān b. ʿUyaynah, etc.)
  to validate the schema and UI rendering. Drives initial UX.
- **Phase 1 (Taqrīb baseline)** — ingest Ibn Ḥajar's Taqrīb. Each entry maps
  to one short Arabic verdict + one canonical reliability label. Quick win:
  ~6000 Sunni narrators get `reliability_consensus` + a one-line bio_taʿdīl
  or bio_jarḥ.
- **Phase 2 (Tahdhīb rich quotes)** — parse Tahdhīb al-Kamāl entries.
  LLM-assisted extraction of (critic, verdict, quote_arabic, citation_page).
  Output stored as structured JSONL per narrator before being aggregated into
  the Narrator node properties.
- **Phase 3 (Mīzān + Ibn Ḥajar's Tahdhīb)** — second-pass enrichment of
  impugned narrators.
- **Phase 4 (Shia)** — al-Khūʾī Muʿjam as primary; al-Najāshī + al-Ṭūsī as
  secondary.

### HITL / safety rails

- All extracted (critic, verdict) tuples written to a staging JSONL first,
  with `source_book`, `page_ref`, `arabic_quote`, `extraction_confidence`.
- Aggregation into Narrator only after a sample is HITL-approved per book.
- Per scholar_indx: keep raw quote provenance accessible via
  `(:Narrator)-[:HAS_VERDICT]->(:Tawthīq | :Tajrīḥ)-[:CITES]->(:RijalBook)`
  pattern; the on-Narrator bio_* fields are denormalised summaries for UI speed.
- Prophets and angels (identified by `is_prophet=true` after seeding) skipped
  entirely.
