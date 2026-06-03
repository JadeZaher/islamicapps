# Runbook Addendum — F1 partial 2026-05-25

**Parent track:** `neo4j_isnad_graph_regen_20260516`
**Predecessor:** [`runbook-passoff-2026-05-24.md`](./runbook-passoff-2026-05-24.md)
**Scope:** F1 (App v1→v2 migration) — what got done, what was discovered, what's deferred.

---

## TL;DR

F1 in the prior runbook described the remaining work as a 3–4h mechanical
rename across list/search/export/admin/comparative pages. After audit, only
one of those was a real user-visible bug; most of the named files were
already migrated. The bigger discovery: the **v2 Hadith schema dropped
`display_grade` and `transmission_type` entirely** — grading moved onto
`:Assessment` nodes (G-1). This makes the admin tooling for hadith
authoring/grading a redesign target, not a migration target.

What shipped this pass:
- Fixed the narrator teacher/student network tab (was empty).
- Dropped the obsolete v1 grade filter / column from admin/hadith.
- Removed dead v1 server actions and the orphaned admin/chain-builder route.

What's deferred to a fresh track:
- An admin grading-UX redesign that surfaces per-tradition `:Assessment.grade`.
- A decision on whether manual chain authoring is still a use case post-v2.

---

## 1. What shipped (commits land on `main` → Railway auto-deploys)

### Bug fix
- **`getNarratorNetwork`** (`src/app/actions/graph-actions.ts`): swapped
  `:HEARD_FROM` → `:NARRATED_FROM`. The v2 fullregen never writes
  `:HEARD_FROM`, so the narrator page's teacher/student tab was returning
  empty arrays for every narrator. Verified post-fix: Abu Hurayra now
  resolves 43 teachers / 361 students from the live DB.

### Dead-code removal in `src/app/actions/graph-actions.ts`
All of these were v1-only and silently no-ops or schema-violating writes on
the v2 graph. None were called by any live page:
- `calculateAutoGrade`, `calculateTransmissionType` — read `n.reliability`
  (gone in v2, moved to `:Assessment`), wrote `h.auto_calculated_grade` /
  `h.display_grade` / `h.transmission_type` (not in v2 schema).
- `createNarrator`, `createHadith` — wrote v1 property names.
- `createChain`, `validateChainOrder` — wrote `:TRANSMITTED_VIA` and
  `:HEARD_FROM` (neither exists in v2), depended on `:MatnVariation` (gone).
- `getNarratorDetails` — duplicate of `getEnhancedNarratorDetails` via v1
  edges. The narrator page already calls the enhanced variant.
- `getEnhancedHadithDetails` — used `:HAS_VARIATION`. The hadith page does
  not call it.

### Admin UI cleanup
- Removed the entire `/admin/chain-builder` route. It was orphaned (no nav
  link pointed to it post-v1) and depended on `:MatnVariation`. The page
  hard-coded `variationId: 'temp-variation-id'`, so the write path could
  never have worked end-to-end.
- Removed the "New Hadith" create form from `/admin/hadith`. v2 ingest is
  the only authoritative writer of `:Hadith` nodes; manual creation produced
  v1-shape rows that wouldn't show up in tradition-filtered queries.
- Removed the "Auto-Analysis" per-row button (called `calculateAutoGrade`,
  which was a no-op).
- Removed the v1 grade filter from the search bar and the v1 grade column
  from each list card. The dropdown options (`SAHIH`/`HASAN`/`DAIF`/`MAWDU`)
  do not exist as values anywhere in the v2 graph.
- Removed `grade` and `display_grade`/`transmission_type` from
  `exportHadiths` config (filter and ALLOWED_EXPORT_FIELDS). The v1 CSV
  column aliases `title`/`primary_topic`/`text_english`/`text_arabic` are
  preserved for downstream consumers.

### What was checked but didn't need migration
The prior runbook's F1 list was based on a partial audit; this pass checked
each named file end-to-end:
- `src/app/actions/comparative-actions.ts` — `s.title` / `t.title` references
  are on `:SourceText` / `:Translation` nodes (a separate cross-cultural
  parallels subsystem), not `:Hadith`. Already v2-compliant.
- `src/app/api/comparative/research/route.ts` — already reads `h.text_en`
  and `h.category`; aliases on output only.
- `src/app/narrator/[id]/client-page.tsx` — receives `other_hadiths` from
  `getEnhancedNarratorDetails`, which aliases `chapter`→`title` and
  `category`→`primary_topic` server-side. Already correct.
- `src/components/HistoricalTimeline.tsx` — `event.title` is
  `:HistoricalEvent.title`, not `:Hadith.title`. Not a v1 vestige.
- `searchHadiths`, `exportHadiths`, `getEnhancedNarratorDetails` in
  `graph-actions.ts` — already applied the alias pattern.

---

## 2. Schema discovery — why admin grading is deferred

Probing the live Railway DB showed the v2 `:Hadith` and `:Narrator`
node shapes are leaner than the v1 application code assumed:

```
:Hadith keys
  attributed_to, category, chain_type, chapter, chapter_no, created_at,
  dataset_row_id, hadith_id, hadith_no, id, matn_ar, matn_en,
  narration_level, page_ref, pipeline_key, sanad, sanad_confidence,
  school, source, text_ar, text_en, tradition, updated_at, url, volume

  NOT PRESENT: display_grade, transmission_type, auto_calculated_grade,
               title, primary_topic, text_english, text_arabic

:Narrator keys
  bio*, created_at, death_date_*, geographic_region, id, is_companion,
  is_prophet, kunya, name, name_arabic, name_arabic_clean,
  name_english, name_english_clean, nasab, nisba, reliability_consensus,
  reliability_disagreement, scholar_indx, source, tabaqah

  NOT PRESENT: reliability, bio_summary populated only for 21 Phase-0
               narrators (per parent runbook)
```

Grading lives on `:Assessment` — 4 per Hadith (one per tradition):

```
:Assessment keys
  created_at, grade, grade_scheme, grade_source, id, pipeline_key,
  tradition, updated_at

distinct grade_scheme:
  imami_4tier (101,215), sunni_7tier (99,283), zaydi_3tier (99,283),
  ibadi_2tier (99,283)

distinct Sunni grades:
  no_extant_evaluation (69,368), ثابت (29,915)

distinct Imami grades (top):
  no_extant_evaluation (84,381), مجهول, صحيح, ضعيف, ضعيف على المشهور,
  لم يخرجه, حسن, موثق, مرسل, معتبر, حسن كالصحيح, مرفوع
```

So:
- Each Hadith has 4 grades, not 1.
- Grades are tradition-specific Arabic terms, not a single global v1 enum.
- The Sunni `7tier` scheme, Imami `4tier` scheme, Zaydi `3tier` scheme, and
  Ibadi `2tier` scheme each need their own badge palette and ordering.

That is a UX redesign, not a code migration. See § 4 below.

---

## 3. Quick verification

```bash
# (a) tsc is clean on src/ (stale .next/types entries for the removed
#     chain-builder route will resolve on the next `next build`)
npx tsc --noEmit 2>&1 | grep -E "^src/" | grep -v archive | grep -v __tests__
# (empty)

# (b) Abu Hurayra teacher/student network resolves with :NARRATED_FROM
node -e "
require('dotenv').config();
const neo4j = require('neo4j-driver');
const uri = process.env.NEO4J_URL.startsWith('bolt://') ? process.env.NEO4J_URL : 'bolt://' + process.env.NEO4J_URL;
const d = neo4j.driver(uri, neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD));
(async () => {
  const s = d.session({ defaultAccessMode: neo4j.session.READ });
  const t = await s.run('MATCH (n:Narrator {id: \"a02869eb-058a-4b90-83ca-a10b5e8336d5\"})-[:NARRATED_FROM]->(t:Narrator) RETURN count(DISTINCT t) AS c');
  const st = await s.run('MATCH (st:Narrator)-[:NARRATED_FROM]->(n:Narrator {id: \"a02869eb-058a-4b90-83ca-a10b5e8336d5\"}) RETURN count(DISTINCT st) AS c');
  console.log('teachers:', t.records[0].get('c').toNumber());   // expect 43
  console.log('students:', st.records[0].get('c').toNumber());  // expect 361
  await s.close(); await d.close();
})();
"
```

In the browser after deploy:
- `/narrator/a02869eb-058a-4b90-83ca-a10b5e8336d5` → "Teacher-Student
  Network" tab should now populate (was empty before).
- `/admin/hadith` → no grade column, no grade filter, no New Hadith button,
  no per-row Auto-Analysis button. List + tradition badge + view-details
  + Export CSV only.
- `/admin/chain-builder` → 404 (route removed).

---

## 4. Deferred — new track candidates

### F1.a — Admin grading-UX redesign (medium-large)

**Problem.** Admin/hadith and the public hadith detail page both want to
show "this hadith's grade." In v2 there is no single grade — there are 4
per-tradition assessments using 4 different scheme vocabularies in Arabic.

**Decisions required before implementation:**
1. **Default-tradition selection.** When viewing a hadith in
   `admin/hadith` list (which is tradition-mixed), do we show:
   - (a) the Hadith's own `tradition` (`h.tradition`) assessment, or
   - (b) all 4 side-by-side (4 chips per row), or
   - (c) the Sunni assessment as a global default?
2. **Vocabulary surfacing.** Show the raw Arabic term (`ثابت`, `صحيح`,
   `ضعيف`) — fidelity preserved, but unreadable for English-only users — or
   add a transliteration + English gloss map per scheme?
3. **Color palette per scheme.** Sunni `7tier` and Imami `4tier` have
   different orderings; one color ramp does not work for both.
4. **Filter semantics.** If the user filters by grade=`صحيح`, are we
   filtering on assessment-grade-in-the-Hadith-own-tradition, or
   any-assessment-anywhere, or only-when-h.tradition-matches?

### F1.b — Manual chain authoring: keep, redesign, or remove?

The deleted `admin/chain-builder` was a v1-era tool with a broken write
path. Decide:
- Is hand-authoring a chain ever a use case post-v2? (v2 ingest reads
  `all_rawis.csv` and `gradings_full.csv`; chains derive from `sanad` text.)
- If yes, the v2 shape would be: pick a `:Hadith`, then write a single
  `:Chain` node + `:HAS_CHAIN` edge + `:INCLUDES` edges (with `position`) +
  `:NARRATED_FROM` edges (with `temporal_plausibility`).
- If no, the route stays deleted and the dataset is the only authority.

### F1.c — Per-hadith chain-health score

`src/app/hadith/[id]/page.tsx:57-66` calculates a "chain health"
percentage as "fraction of narrators with `n.reliability === 'THIQA'`" —
which is always 0% on v2 (the field is gone). A v2 equivalent would derive
from `:Assessment` on narrators (once Phase 1 Taqrīb ingest populates
`reliability_consensus` for the ~6k Sunni narrators per the parent track).
Block this until Phase 1 lands.

---

## 5. Commit log (this addendum)

To be filled at commit time.

---

## 6. What did NOT change

For posterity: the following remained intact and verified working:
- v2 fullregen pipeline (`src/scripts/lib/regen/*`).
- Hadith detail page (`/hadith/[id]`) — already reads v2 fields via aliases
  in `getHadithById`.
- Phase-0 narrator bios — 21 seeded `scholar_indx` rows, `bio_provenance =
  'manual_phase_0'`, still present and rendering on `/narrator/[id]`.
- Cross-cultural parallels subsystem (`comparative-actions.ts`,
  `api/comparative/research/route.ts`).
- Acceptance gauntlet still passes 30/31 (the one minor :NameMention noise
  noted in the parent runbook is unchanged: 4,944 actual vs ≥5,000 expected).
