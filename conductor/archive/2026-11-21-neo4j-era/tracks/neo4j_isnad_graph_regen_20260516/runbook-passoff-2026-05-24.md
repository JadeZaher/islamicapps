# Runbook — Pass-off 2026-05-24

**Parent track:** `neo4j_isnad_graph_regen_20260516`
**Spans:** v2 regen pipeline, app v1→v2 read-path migration, narrator-enrichment Phase 0
**Predecessors:** [`spec.md`](./spec.md), [`plan.md`](./plan.md), [`verification.md`](./verification.md),
[`ultrapilot-passoff-v2.md`](./ultrapilot-passoff-v2.md)

> A single document an operator (or future agent) can read top-to-bottom and (a) know the live state,
> (b) verify it, and (c) pick up the next item without spelunking through chat history.

---

## 1. What's deployed (live on Railway)

| Layer | Commit | What landed |
|---|---|---|
| **Build fix** | `560886a` | tsconfig excludes `src/scripts/archive` + `src/scripts/__tests__` so `next build` succeeds. |
| **v2 regen + supernode lib + app foundation** | `e951c29` | batch-loaders, retry-with-split, supernode-detect, mode-fullregen v2.2, drain batch lowered 1k→250, app hadith-detail reads v2 fields with v1 aliases. |
| **Chain ordering** | `63abee0` | `getFullChainGraph` orders narrators by `:INCLUDES.position` so the isnad renders top-to-bottom in canonical order. |
| **Phase-0 narrator bios + UI** | `74e3d87` | 21 anchor narrators seeded with `is_prophet`, `is_companion`, `tabaqah`, `bio_summary`, `bio_tadil`, `bio_jarh`, `reliability_consensus`, `reliability_disagreement`, `critic_quote_count`, `bio_provenance`. Narrator detail page renders a "Classical Verdict — Jarḥ wa Taʿdīl" card. |

Origin: `https://github.com/JadeZaher/islamicapps.git` → branch `main` → Railway auto-deploys.

---

## 2. Current DB state (Neo4j on Railway proxy `switchyard.proxy.rlwy.net:52091`)

| Label / Relationship | Count | Notes |
|---|---|---|
| `:Hadith` | **99,283** | exact match to unified CSV |
| `:Narrator` | **24,326** | exact match to all_rawis.csv |
| `:Chain` | 99,283 | 1 per hadith; multi-isnad rows in the CSV come pre-split as separate hadith rows |
| `:Assessment` | 399,064 | 4 traditions × 99,283 = 397,132 + extras from gradings_full multi-scholar entries |
| `:NameMention` | 4,944 | Tier-2/3 unresolved narrators (mostly Ibadi/Zaydi/Imami-gap sanad text) |
| `:Source` | 32 | matches distinct sources in CSV |
| `:ReligiousTradition` | 4 | Sunni, Imami, Zaydi, Ibadi |
| `:DatasetVersion (active=true)` | 1 | id `fb465b8e-8a51-423d-8d36-e7ab7664a79a` |
| `INCLUDES` (Chain→Narrator) | 215,312 | |
| `NARRATED_FROM` (Narrator→Narrator) | 28,712 | all flagged with `temporal_plausibility` (14,721 plausible / 5,848 impossible / 8,143 unknown) |
| `FROM_TRADITION` | 99,283 | 1 per hadith |
| `HAS_CHAIN` | 99,283 | |

### Phase-0 narrator bios — the 21 seeded scholar_indx

```
1  Prophet Muhammad ﷺ           (is_prophet=true)
2  Abu Bakr al-Siddiq            (Companion)
3  Umar ibn al-Khattab           (Companion)
4  Uthman ibn Affan              (Companion)
5  Ali ibn Abi Talib             (Companion)
13 Abu Hurayra                   (Companion, contested)
17 Ibn Abbas                     (Companion)
18 Ibn Umar                      (Companion)
19 Anas ibn Malik                (Companion)
34 Jabir ibn Abdullah            (Companion)
53 Aisha bint Abi Bakr           (Companion, contested)

10511 Urwa ibn al-Zubayr         (Tabi'i)   → thiqa_thabt
11013 Ibn Shihab al-Zuhri        (Tabi'i)   → thiqa_thabt, contested
11019 Qatada ibn Di'ama          (Tabi'i)   → thiqa, contested (Qadari)
11060 Sulayman al-A'mash         (Tabi'i)   → thiqa, mudallis

20001 Imam Malik ibn Anas        (Atba')    → thiqa_thabt
20005 Sufyan ibn Uyayna          (Atba')    → thiqa
20012 Sufyan al-Thawri           (Atba')    → thiqa_thabt
20020 Shu'ba ibn al-Hajjaj       (Atba')    → thiqa_thabt
30201 Abu Bakr ibn Abi Shayba    (Atba_Atba) → thiqa
30367 Qutayba ibn Sa'id          (Atba_Atba) → thiqa_thabt
```

All carry `bio_provenance = 'manual_phase_0'` — Phase 1 (Taqrīb ingest) MUST skip rows where this
field equals `'manual_phase_0'` to avoid overwriting curated bios.

---

## 3. Quick verification (operator commands)

```bash
# (a) Live DB has the expected counts
npx tsx src/scripts/verify-regen-acceptance.ts

# (b) Phase-0 bio is reachable end-to-end
node -e "
require('dotenv').config();
const neo4j = require('neo4j-driver');
const uri = process.env.NEO4J_URL.startsWith('bolt://') ? process.env.NEO4J_URL : 'bolt://' + process.env.NEO4J_URL;
const driver = neo4j.driver(uri, neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD));
(async () => {
  const s = driver.session({ defaultAccessMode: neo4j.session.READ });
  const r = await s.run('MATCH (n:Narrator { scholar_indx: 13 }) RETURN n.bio_summary AS s, n.reliability_consensus AS rc');
  console.log(r.records[0].get('rc'), '|', (r.records[0].get('s')||'').slice(0,100));
  await s.close(); await driver.close();
})();
"

# (c) Build is green locally
npx tsc --noEmit | grep -E "src/(app|scripts)" | grep -v "archive" | grep -v "__tests__"
# (empty output = clean)
```

In the browser, after Railway deploy, hit:
- `/hadith/a7041675-f4b0-49d1-9850-59df9d3dfebd` — Sahih Bukhari #1; should show **sanad** + **matn (Arabic + English)** in the "Hadith Text" card, and an **ordered isnad chain** (Qutayba → Sufyan → al-Zuhri → Abu Salama → Abu Hurayra) in the IsnadChain component.
- `/narrator/a02869eb-058a-4b90-83ca-a10b5e8336d5` — Abu Hurayra; should show the **Classical Verdict** card with `not_applicable` badge + `contested` flag, Sunni rijāl note, taʿdīl quote, and a jarḥ note about the Imami/Mu'tazili critique.

---

## 4. Open follow-ups, in priority order

### F1. App v1→v2 migration — finish the read paths (medium, 3-4 hours)

The hadith **detail** page reads v2 fields. The **list**, **search**, **export**, **comparative**, and
**admin** pages still query v1 column names (`h.title`, `h.primary_topic`, `h.text_english`,
`h.text_arabic`). They don't crash (they return null for those fields) but they're visibly broken.

Files needing the same alias/rewrite treatment as `getHadithById`:

```
src/app/actions/graph-actions.ts            (lines 800-1020: exportHadiths, searchHadiths, etc.)
src/app/actions/comparative-actions.ts      (lines 370, 442)
src/app/api/comparative/research/route.ts   (lines 67-93)
src/app/admin/hadith/client.tsx
src/app/admin/chain-builder/page.tsx
src/app/narrator/[id]/client-page.tsx       (renders hadith.primary_topic in other_hadiths section)
src/components/HistoricalTimeline.tsx
```

Pattern to apply (already done in `getHadithById`):
- `text_english` → `text_en`, with v1 alias for backward compat
- `text_arabic` → `text_ar`
- `title` → `chapter || category`
- `primary_topic` → `category`
- `(:Hadith)-[:HAS_VARIATION]->(:MatnVariation)` → `(:Hadith)-[:HAS_CHAIN]->(:Chain)` direct
- `:HEARD_FROM` → `:NARRATED_FROM`

### F2. Sanad gap repair (small, several options)

Per-source coverage breakdown (rows with empty `sanad`):

```
Nahj al-Balagha            100% missing   ← BY DESIGN (sermons/letters/sayings, no isnads)
Musnad al-Shafi'i          100% missing   ← UPSTREAM DATA LOSS (matn-only import)
Sahih Muslim               56% missing    ← ~80% of these are chapter markers (text_ar starts with بَاب)
Sahih Bukhari              31% missing    ← REAL gap; full isnad embedded in text_ar
Sunan an-Nasa'i            48% missing    ← same
Sunan Abi Da'ud            48% missing    ← same
Sunan Ibn Majah            40% missing    ← same
Jami' al-Tirmidhi          37% missing    ← same
```

Three independent moves:

1. **Filter Muslim chapter markers** (~1 hour). Tag rows where `text_ar` starts with `بَاب` with
   `is_chapter_marker=true`; exclude from hadith lists. Recovers the "false gap" stat.
2. **LLM extraction for Bukhari/Sunan** (~$8, ~hours). The regex starter at
   [`src/scripts/extract-sanad-from-text.ts`](../../../src/scripts/extract-sanad-from-text.ts)
   only hit 60% precision — see § Gotchas. A Haiku call per row would extract the isnad cleanly. Idempotent (writes only where `sanad` is empty).
3. **Re-source Musnad al-Shafi'i** (research/days). Find an isnad-preserving original source for this
   collection and re-import. Likely the OpenITI corpus or a fresh dataset.

### F3. Narrator enrichment Phase 1 — Taqrīb al-Tahdhīb (large, ~day)

Per spec [§ Addendum 2026-05-24](../narrator_enrichment_20260425/spec.md):
1. Acquire Ibn Ḥajar's *Taqrīb al-Tahdhīb* text (OpenITI has it).
2. Parse entries (each is `narrator_name + one_word_verdict + brief_remarks`).
3. Fuzzy-match each entry against `:Narrator { scholar_indx, name }` (name_arabic_clean from Phase 0
   helps if Phase 0 covers the seed entries).
4. SET `reliability_consensus` + populate one-line `bio_tadil`/`bio_jarh`.
5. **MUST skip** any narrator where `bio_provenance = 'manual_phase_0'` — those are higher-quality.

Expected coverage: ~6,000 of the 24,326 narrators (only the Sunni ones in Taqrīb).

### F4. Narrator enrichment Phase 2 — Tahdhīb al-Kamāl (large, days-week)

Per spec: LLM-assisted extraction of `(critic, verdict, quote, page_ref)` tuples per narrator. HITL
review per book before aggregating into the `:Narrator` summary fields. Add the relational layer:

```cypher
(:Narrator)-[:HAS_VERDICT]->(:Tawthiq | :Tajrih)-[:CITES]->(:RijalBook)
```

### F5. Mode=test §9b false-negative (small)

`mode=test`'s "Live :Hadith count >= 50000" reports 0 even though 99,283 exist. The "live" filter in
`src/scripts/lib/regen/mode-test.ts` is wrong (likely a tombstone/INGESTED_IN check that's too
strict). Fix the query so the test passes, then add it to CI.

### F6. Counter inflation in mode-fullregen (cosmetic)

When retry-with-split fires, the in-memory `chainLoaded` / `mentionLoaded` counters get incremented
on each retry attempt even though the underlying MERGE is idempotent. The reported numbers
overstate by ~5-15% in heavy supernode zones. DB state is always correct (verified by direct count
queries). Either:
- Move counter increments to a post-flush single-source-of-truth count, or
- Document the inflation and ignore it.

---

## 5. Gotchas — things that bit us this pass

### G1. Railway proxy Bolt RTT is the dominant cost
Each `runWrite` is ~215 ms commit RTT. With v2.0's ~20 writes/row, the full load extrapolated to
**5.7 days**. Solution: **batched UNWIND** (one tx → 100 rows) at
[`src/scripts/lib/regen/batch-loaders.ts`](../../../src/scripts/lib/regen/batch-loaders.ts).
Reduced run to ~hours. Any future hot-path that issues per-row writes will hit this same wall —
always UNWIND-batch.

### G2. Supernode-driven MERGE contention
Top narrators (Abu Hurayra 4,672 chains; al-Zuhri 4,064; Yahya 3,193) cause MERGE INCLUDES to
slow down within a single UNWIND tx because each edge's MERGE has to scan the target narrator's
existing edges. At K=100 batches, this triggered the 30s per-tx timeout in mid-load. Solution:
**retry-with-split** at
[`mode-fullregen.ts:flushSlice`](../../../src/scripts/lib/regen/mode-fullregen.ts) (halve on
transient/timeout, recurse to single rows). On a fresh DB the issue was manageable. Watch list at
[`src/scripts/lib/regen/supernode-detect.ts`](../../../src/scripts/lib/regen/supernode-detect.ts).

### G3. Drain batch size needs to match graph density
Original 1,000-node `DETACH DELETE` exceeded Neo4j's 716 MiB per-tx memory cap on the v2 graph
(denser than v1 — Narrators + INCLUDES + NARRATED_FROM didn't exist before). Lowered to 250 in
[`src/scripts/drain-db.ts`](../../../src/scripts/drain-db.ts). If the graph grows further
(narrator-enrichment will add edges), may need to drop again.

### G4. Cypher `collect()` and `RETURN DISTINCT` do NOT preserve order
First reported by the user as "odd lineage on isnad". `getFullChainGraph` returned narrators in
whatever order Neo4j happened to emit them. Fixed with explicit `ORDER BY i.position` on the
`:INCLUDES` edge in commit `63abee0`. **Lesson:** any Cypher returning ordered things via
`collect` or `DISTINCT` needs explicit ordering.

### G5. Process survives VSCode crash via `nohup`
The 2h 38min v2.2 regen run survived a mid-run VSCode crash because it was launched with `nohup
npm run db:regen … &`. The Monitor task died with VSCode but the regen kept writing. Lesson: any
long-running script should be wrapped in `nohup` so the editor or session lifecycle doesn't kill
the work.

### G6. App schema migration is non-trivial — three independent renames + a path change
The v1→v2 changes were not just renames:
- `text_english` → `text_en` (rename)
- `text_arabic` → `text_ar` (rename)
- `title`, `primary_topic` → **deleted** (no direct equivalent; alias to `chapter`/`category`)
- `(:Hadith)-[:HAS_VARIATION]->(:MatnVariation)` → **deleted** (direct `:HAS_CHAIN` instead)
- `:HEARD_FROM` → `:NARRATED_FROM` (different edge type)
- Narrator `.reliability` field → **moved to** `:Assessment` nodes (G-1 invariant)

The hadith detail page handles all six via aliasing in `getHadithById`. The list/search/export/admin
pages do not (yet — see F1).

### G7. Regex isnad extraction has ~60% precision
[`src/scripts/extract-sanad-from-text.ts`](../../../src/scripts/extract-sanad-from-text.ts) was
written but **not run against production**. The matn boundary detection slips into matn body for
~40% of cases (Companion-source patterns like Ibn Abbas dispute narratives, where the matn lacks
an explicit Prophet mention). For production-quality recovery, use LLM extraction (~$8 for all
20k empty-sanad rows at Haiku rates).

### G8. Phase-0 bio MUST be respected by Phase 1+
The 21 hand-curated bios carry `bio_provenance = 'manual_phase_0'`. Any subsequent enrichment pass
(Taqrīb in Phase 1, Tahdhīb al-Kamāl in Phase 2, etc.) MUST filter by `WHERE bio_provenance IS
NULL OR bio_provenance <> 'manual_phase_0'` to avoid overwriting curated content with bulk-extracted
content.

---

## 6. Reference — useful one-liners

```bash
# Show top 20 supernode narrators (by chain appearances)
node -e "
require('dotenv').config();
const neo4j = require('neo4j-driver');
const uri = process.env.NEO4J_URL.startsWith('bolt://') ? process.env.NEO4J_URL : 'bolt://' + process.env.NEO4J_URL;
const driver = neo4j.driver(uri, neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD));
(async () => {
  const s = driver.session({ defaultAccessMode: neo4j.session.READ });
  const r = await s.run('MATCH (n:Narrator)<-[:INCLUDES]-(c:Chain) WITH n, count(c) AS x ORDER BY x DESC LIMIT 20 RETURN n.scholar_indx AS i, n.name AS name, x');
  for (const rec of r.records) console.log(String(rec.get('i').toNumber()).padStart(6), '|', rec.get('x').toNumber(), '|', (rec.get('name')||'').slice(0,60));
  await s.close(); await driver.close();
})();
"

# Per-source sanad coverage
# (see § 4 F2 above — same as the diagnostic query used in this pass)

# Re-run Phase-0 seed idempotently (refreshes any bio edits in src/scripts/seed-narrator-bios-phase0.ts)
npx tsx src/scripts/seed-narrator-bios-phase0.ts

# Dry-run sanad regex extractor on a source
npx tsx src/scripts/extract-sanad-from-text.ts --dry-run --limit=100 --source="Sahih Bukhari"

# Drain DB (250-node batches, idempotent across multiple runs)
npm run db:drain

# Full clean-slate regen (uses batched UNWIND + retry-with-split; ~hour fresh, much slower over existing data)
npm run db:regen -- --mode=fullregen
```

---

## 7. Commit log (this pass)

```
74e3d87  feat(narrator): Phase-0 jarḥ wa taʿdīl bios for top-20 supernodes + UI
63abee0  fix(hadith): order isnad narrators by chain position
560886a  fix(build): exclude src/scripts/archive from tsc
e951c29  v2 isnad graph regen + app schema migration
9eff4b1  export                                            ← last commit before this pass
```

Path forward: pick one of F1–F6, file a follow-up runbook addendum, repeat.
