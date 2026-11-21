---
type: review
role: adversary (refute)
date: 2026-11-21
branch: refactor/postgres-drizzle @ c2b9620
---

# Adversarial review: Shura wa Istehsan, Postgres + Drizzle move

**Role.** Adversary in a two-sided review. My job was to refute, so this report lists only what I found wrong, unverified or missing, ranked by how much damage each finding does if left alone.

**Method.** I did not trust the project's summaries. Every finding below rests on something I checked myself:

- I queried the development database (`islamicapps_dev`) read-only. Each session ran with `SET default_transaction_read_only=on`, and Arabic queries ran from UTF-8 `.sql` files because Windows argv mangles Arabic (see the error I made below).
- I ran read-only Cypher counts and small samples against production Neo4j through `neo4j-driver`, using a one-off script in the scratchpad.
- I read code and docs, and I read rows. The 40 narrator links I judged myself from the chain context.
- I made no writes, ran no loads and no migrations, and made no commits. Every process I started has exited.

**What I ran.**

| Command | Result |
| --- | --- |
| `npx tsc --noEmit` | exit 0 |
| `npm run db:verify` | OK, but it checks the catalog only: 41 tables, 6 views, 7 of 7 migrations |
| `npx tsx src/lib/glossary/__tests__/glossary.test.ts` | all passed |
| `npx tsx --conditions=react-server src/db/queries/__tests__/flows.test.ts` | 12 passed |
| Python suite in `datasets/hadith-data/__tests__` (7 modules) | `Ran 170 tests in 6.5s OK` |

The Python suite cannot be run with `unittest discover` (`Start directory is not importable`). I ran it module by module.

**An error I made and caught.** My first matn check passed every row. That was a false pass: Windows argv turned the Arabic character class into an empty match, so every comparison succeeded trivially. I re-ran it from a UTF-8 file, and the corrected numbers are the ones below.

---

## Ranked findings

### 1. The pages show another report's text as the matn

The 1,597 misattached matns were loaded into Postgres, and the hadith page prefers them over the report's own text.

- **What I measured** (letters-only containment of `matn_ar` in `text_ar`): Muslim 625, Tirmidhi 596, Ibn Majah 245, Nasa'i 80, Bukhari 47, Abu Da'ud 4. That totals 1,597, exactly the RUNBOOK's figure.
- **Why the page shows it.** `src/app/hadith/[id]/client-page.tsx:30-32` reads `const arabicText = hasArabicMatn ? hadith.matn_ar : hadith.text_ar …`. The wrong text then appears under the heading "Matn · report text".
- **Example.** In `hadith:k6:23658` (Tirmidhi), `text_ar` opens `وقد روي هذا الحديث، عن الزهري…`. The page instead shows `حدثنا قتيبة… عن أبي بكر الصديق…`, which is a different report.
- **A second problem.** For 13,502 more K6 rows, `matn_ar` is at least 97% of the whole text, chain included. On those pages the isnad appears twice: once in the Isnad section and again under "Matn".
- The RUNBOOK lists this as an "ETL defect to fix". It does not say that the interface actively prefers the corrupt field. The interim fix is one line: show the matn only when it is contained in its own text.

### 2. The public site shows zero hadiths right now, and the preview approval protects nothing

- `select count(*) from public_hadiths` returns 0, and so does `public_translations`.
- `collection_rights` has 0 rows. The `public_hadiths` view inner-joins it and requires `rights_status='cleared'` (it is defined in `drizzle/core/0003_views.sql` and redefined in 0006).
- The owner's `approve_preview` row (`curation_audit` id 1) targets dataset version `30cd1c84…`. That version is no longer current. The current version `87f89127…` has no `public_override_by`, so the override was silently dropped by the next load.
- The flows test passes only because its fixture inserts rights rows. Nothing has ever exercised the real data together with the real gate.

### 3. Under the proposed rights plan, the preview publishes only the traditions with no links and no English

- `docs/rights/rights-register.md:102` proposes 23 works that can be cleared: 20 Imami works from Thaqalayn plus Musnad Zayd, Musnad al-Rabi' and Sahifat al-Rida. That is 34,372 reports, 35% of the corpus.
- Every Sunni collection stays pending, so Bukhari and Muslim drop off the site.
- Verified narrator links by tradition, measured: Sunni 83,949; Imami, Ibadi and Zaydi 0.
- `chain_mention_candidates` has candidates only for Sunni reports (212,921 rows, all Sunni). Every Imami, Ibadi and Zaydi name therefore shows as unidentified.
- Imami `matn_ar` is empty for 33,190 of 33,225 rows, so no matn segmentation.
- English publishable today: 0 ("No provider English is cleared today", `rights-register.md:103`).
- **Net result:** the session's identity work, about 84k verified Sunni links, would be invisible in the preview.

### 4. "Verified" links include wrong people, and "confirmed by text" cannot detect homonyms

I drew a seeded random sample of 40 `resolution='source_index'` mentions (`order by md5(id||'adv1')`; full list in the appendix) and judged each one in its chain context.

| Result | Count | Cases |
| --- | ---: | --- |
| Plainly wrong person | 2 | #5, #33 |
| Doubtful | 1 | #3 |
| Correct or defensible | 37 | |

That is a 5% error rate on definite errors and 7.5% if the doubtful case counts. The 95% interval is roughly 1% to 17%.

- **#5, Ibn Majah, عمرو بن خالد (from Habib b. Abi Thabit).** This is Amr b. Khalid al-Wasiti, who is matruk. The link goes to `عمرو بن خالد بن فروخ`, al-Harrani, who is thiqa and died in 229. The error inverts the reliability judgment on that link.
- **#33, Bukhari, `يحيى > هشام > محمد > أبي هريرة`.** This is Hisham b. Hassan from Ibn Sirin. The link goes to Hisham b. 'Urwa.
- **#3, Muslim, Ishaq b. Ibrahim from 'Abd al-Razzaq.** Linked to `إسحاق بن إبراهيم بن محمد`, while Ibn Rahawayh is a separate lexicon row. This may be a duplicate-identity problem.
- **Wrong neighbours.** In the same 40 chains I also saw four wrong neighbouring links:
  - #24: `عبيد الله` linked to Ubayd Allah b. 'Umar instead of Ubayd Allah b. Musa.
  - #30: `أبي موسى` linked to Abu Burda, a position shift.
  - #33: `محمد` linked to Ghundar instead of Ibn Sirin.
  - #34: `سعيد` linked to al-Maqburi instead of Ibn Abi 'Aruba.
- **Cause.** These are the K6 source's own index errors. They pass "confirmed by text" because a bare `هشام` or `سعيد` is consistent with any Hisham or Sa'id. Neither the word "verified" in the public view nor the glossary carries a residual error rate.

### 5. Production Neo4j holds almost no hand-made curation, so the one-time export track is near-empty

- **Labels with nodes:** Assessment 399,064, Hadith 99,283, Chain 99,283, Narrator 24,326, NameMention 4,944, Source 32, ReligiousTradition 4, DatasetVersion 2.
- **Labels that exist in the catalog with zero nodes:** Commentary, CrossCulturalParallel, HistoricalEvent, Location, SourceText, MotifTag, Scholar, ScholarVerdict, MatnVariation, SchoolOfThought, Practice.
- **The only hand-shaped data** is the 21 `bio_provenance='manual_phase_0'` narrators. Their `bio_updated_at` values all fall within seconds of each other on 2026-05-24, which looks like a seed run. Their content lives in `src/scripts/seed-narrator-bios-phase0.ts`.
- **What the track plans for.** `conductor/tracks/neo4j-curation-export_20261121/spec.md` asks owner questions Q6 and Q10 about migrating existing parallels and commentaries, and the RUNBOOK's "Next" step 3 lists commentaries, events and parallels. None of these exist.
- **Seed ports.** None are ported: `src/scripts/db/` contains only `approve-preview.ts`. Twenty-four of the 41 Postgres tables are empty, including `narrator_bios`, `narrator_assessments`, `chain_absence_dispositions` (the Nahj al-Balagha seed was never run), `collection_rights`, `citations` and every history and comparative table.

### 6. A reader would see the cutover as a regression on every visible axis

| Axis | Live Neo4j today | New site |
| --- | --- | --- |
| English | 68,515 hadiths (Sunni 33,588, Imami 33,225, Ibadi 1,004, Zaydi 698) | 0 public. Postgres keeps 66,776 rows, all `source_provided`, none cleared |
| Narrator links on chain pages | 159,550 `INCLUDES` | 0 public; at most 83,949 Sunni once rights clear |
| Collections | all 34 | 23 under the rights proposal |
| Previous/next | (not checked) | none: no `/collection` route, no next or previous link in `src/app/hadith/[id]/*` |

### 7. The Neo4j copy is not trustworthy, so do not treat it as a fallback

- **Imami:** 13,964 links. The top targets are Ali b. Abi Talib (6,867), Abu Umayya Muhammad b. Ibrahim al-Tarsusi (2,805, a Sunni narrator inside Imami chains) and 'Abdullah b. Abi Shayba (2,086).
- **Sunni:** the top four targets are placeholders or the truncated-name bug: `Yahya` 4,211, `'Abdullah ('Abd Rabb) bin Haq` 4,049, `Sh'bh Shykh` 3,567, `Hmad Shykh` 2,179.
- `name_arabic` is empty on every linked narrator. All 145,510 Sunni links have it empty.
- **Assessments:** 352,315 placeholder nodes plus 29,915 Sunni nodes whose grade and grade_source are both `ثابت`. The scheme is cross-wired: every Sunni hadith carries Zaydi, Ibadi and Imami scheme nodes.
- **English:** at least 100 of the 1,702 Ibadi and Zaydi texts contain Arabic or model chatter. Ibadi #39 reads: "I will proceed by translating this specific, provided Arabic text block according to all rules."

### 8. The load never consulted the release gate

- `dataset_versions.curation_manifest_sha256` is NULL for all three versions, and every version is `source_release_state=unreviewed_local_snapshot`.
- The input was `development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`, dated 2026-07-21.
- **The access-denied files.** The three files the pipeline treats as gates are access-denied even to `icacls` ("Access is denied"). Two are the active release commit and the candidate manifest (16,459 bytes each); the third is the 16 MB backlog. All are dated Jul 21 19:50.
- These three files are also excluded from the backup. They are untracked but not git-ignored, so a stray `git add .` would trip on them.
- **Consequence.** The preview override is the mechanism by which an ungated snapshot is published.

### 9. The load inputs and the database are not backed up, and no restore has been run

- `docs/backups/README.md` excludes `datasets/hadith-data/development/` (9.04 GB). That folder holds the incomplete CSV and the `pg-load-2026-11-21` projection that Postgres was actually built from; the manifest has 0 `development/` paths.
- The bucket is in the same Railway project as both databases, so it is not an independent copy.
- No Postgres dump exists. `verify` checks only bucket object hashes. I found no record of a restore.

### 10. Cutover traps that have never been exercised

- **The loader blocks itself.** It refuses to run if any live `narrator_surface_decisions` exist (`src/db/load/AGENTS.md`, step 6: "replay is not implemented"). After the first curator identity decision, no reload is possible.
- **Production loading is untested.** "No curation dump before the load … no `pg_dump` 18 on the operator machine", yet a dump is required before any load into a database that holds curation. Production has been migrated but never loaded.
- **Missing operational pieces.** `ops/roles.sql` does not exist and the app connects as superuser. `apply_decision` is unimplemented, so identity decisions can be recorded but not applied. `refresh_network` grants are deferred (`src/db/AGENTS.md` §Deferred).
- **The merge is barely tested.** `load-flow.test.ts` exercises a 12-row slice and covers insert, a no-op reload, and one omission. It never tests a changed row (update path, derived columns, a candidate whose narrator changes). It also skips silently when the projection is missing (`{ skip: !projectionExists }`).

---

## Other verified defects (smaller)

- **Citation numbers are unusable.**
  - Al-Kafi: 14,245 rows but 597 distinct `hadith_no` values. Of the 11,033 rows that carry an in-text number (`4ـ…`), 10,888 disagree with `hadith_no`. Even (volume, chapter_no, hadith_no) repeats in 1,932 groups.
  - Musnad Ahmad: 23,529 rows, 3,616 distinct numbers, 463 rows numbered `1]` and other non-numeric numbers.
  - Musnad al-Shafi'i: no hadith numbers at all.
  - The page heading is `source + hadith_no` (`client-page.tsx:42`), so a heading like "Al-Kāfi 1" repeats across 255 rows.
  - The claim that every Al-Amālī row is number 1 is false as stated: Saduq has 97 distinct numbers and Mufid 47. The real problem is that numbering restarts per majlis without a majlis field.
- **Extractor artefacts in chain mentions** (live and retired rows): bare `و` 766, a trailing `و` 164, a trailing `انه` 127, formulas such as `بإسناده`, `مثله` and `قراءة عليه` 2,809, Latin, digits or markup 998, `عنه` 825, `قال` 119.
  - From a 20-row Pure Canon check:
    - pc_7819: the chain is just `أبي هريرة و`.
    - pc_95445, branch 0: `… سالم ابن أبي الجعد > أبي ذر > زيد ابن وهب > أبي ذر`, a mis-flattened branch.
    - pc_6534: the chain stops at Humayd and Anas is missing.
    - pc_22780: a mention reads `عمن حدثه`.
    - pc_43859: a mention ends in `انه`.
  - Chain-to-report attachment was correct in 20 of 20, and order runs compiler to companion.
- **Wrong chain status.** Nahj al-Balagha and Shafi'i (4,314 rows) have `chain_status='extraction_failed'` although the design says these works have no chain. The status is not rendered today.
- **Behbudi's exclusions shown as rulings.** 1,734 entries of `لم يخرجه` are stored as `cited_ruling` with `grade_canonical='ungraded'` and are publicly displayable. "Not included in Sahih al-Kafi" is a judgment, not an absence of one. There is also a `صحيح3` artefact.
- **No real Sunni grades.** Only the 29,915 `collection_label` rows exist, and these are hidden. Tirmidhi's own verdicts are extracted only in diagnostics.
- **Qur'an inside reports is unmodelled.** The design doc contains 0 mentions of Qur'an. At least 2,108 reports carry ﴿﴾ or {} quotation marks, and about 2,939 match quotation formulas.
- **Basic interface gaps.** The interface is English only (`<html lang="en">`). There is no transliteration search. English search covers only `public_translations`, which is empty, so Latin queries match only chapter and category titles. `CrossCulturalParallelCard.tsx:174` and `admin/hadith/client.tsx:275` build `/hadith/${id}` without encoding, although OpenITI ids contain `|`.
- **Arabic search works.** `الله` over `hadiths` took 593 ms with the trigram index. Vocalized input is folded by `norm()`. Partial-word `ilike` works.
- **Near-duplicates are few.** Exact `arabic_sha256` duplicates within a collection: Musnad Ahmad 33, Nahj al-Balagha 16, Muslim 10, and small numbers elsewhere. Short fragments under 20 characters: 768 in Ahmad.
- **Translation binding holds.** The Arabic hash matches its hadith on all 66,776 translations (0 stale), and 14 of 14 sampled translations belong to their Arabic. However, 10,650 Sunni translations are flagged `arabic_leakage`, a third of the Sunni English.
- **The dev database has leftover test schemas.** `query_fixture`, `query_fixture_cc`, `query_fixture_http` and `query_fixture_http_cc` each hold 42 relations.

## Stale or false claims in project documents

- **RUNBOOK contradicts itself.** Line 23 says "local only, not pushed"; line 153 says "pushed to GitHub". `gh` reports the repository as **PUBLIC**.
- **Table and view counts.** RUNBOOK line 26 says "40 tables, 5 views". `db:verify` reports 41 and 6.
- **Track index.** `conductor/tracks.md` shows the loader, query-port and containment tracks as `[ ]` (planned), and no track as `[x]`. The RUNBOOK calls them done.
- **External sources README.** `datasets/sources/external/README.md` omits hadith-kg (1.6 GB) and Riwayat (5.0 GB), which are now on disk. It still says the larger datasets were "not downloaded".
- **"Thaqalayn ships no narrator ids"** (`diagnostics/chain-reconciliation/README.md:164,169`) is contradicted by Riwayat itself. Its Shi'i chains carry `id_method='source_annotation_thaqalayn'` on 100,843 mentions and `thaqalayn_id_on_reparsed_span` on 33,771.
- **Design doc drift.** The `hadiths` and `translations` column lists omit `arabic_sha256`, and `narrators` omits `placeholder_reason`. The counts do match the live rows. At 2,359 lines, the doc is too long to keep current, and it is already drifting.
- **Secrets.** No credentials were found in the pushed history; the `NEO4J_PASSWORD=` lines are placeholders. However, the production Neo4j host and port (`switchyard.proxy.rlwy.net:52091`) are in public history (`2bedb29`, `657cf51`, `a3a1022`).

## Question 2: build from local sources or from the Neo4j copy?

**Answer: build from local sources. The choice is right, but the export plan is mostly empty.**

| Kind of data | Authoritative source | Lost if you rely on Neo4j | Lost if you rely on local sources |
| --- | --- | --- | --- |
| Arabic text, structure, numbers | Local sources (re-ETL), then fix numbering | Nothing new; Neo4j has the same 99,283 reports | Nothing |
| Chains and narrator links | Local K6 index plus text corroboration, with external candidates labelled | Inherits garbage links (placeholders, Imami links to Sunni rijal) | Nothing of value. Neo4j's links are mostly wrong |
| English | Local provider files with rights state | Contaminated Ibadi and Zaydi English | Nothing; Postgres holds the same Sunni and Imami English |
| Grades | Local Thaqalayn gradings | Nothing usable; Neo4j's Sunni "ثابت" pseudo-grades and placeholders are noise | Nothing |
| Phase-0 bios | `seed-narrator-bios-phase0.ts`, after diffing against Neo4j | Nothing | Nothing, after the diff |
| Commentaries, parallels, events, locations, source texts, motif tags | None exist anywhere | Nothing | Nothing |
| Legacy Neo4j snapshot | A one-time full JSONL dump (`backup-db.ts`) before retirement | — | Forensics only |

**What would be lost irrecoverably.**

- **Relying on Neo4j:** the corrected Pure Canon chains, the identity candidates, and the provenance and version tracking.
- **Relying on local sources:** potentially nothing. The only unknowns are the 4,944 NameMention nodes and any field-level edits that differ from the seed. Run the dump and the diff to settle them.

## Question 5: busywork versus importing open datasets

**Low-yield effort compared with importing.**

- Name-invariant resolver diagnostics: several jobs ending in 84k Sunni links and 0 Imami links.
- MinHash and LSH report-correspondence work: 135,825 pairs, with no table and no loader.
- Home-built rijal parsing for biography verification.
- Machine translation candidates through hy-mt2, while no English is publishable at all.

**What already exists on disk.**

- Riwayat (CC0 for its own layer) matches 64.6% of the Imami reports and 93.1% of Al-Kafi. It carries Thaqalayn-annotated narrator ids on 100,843 Shi'i mentions and states a precision of 0.98 against MIDS.
- hadith-kg (CC BY 4.0) has 577,024 chains with narrator ids, 49,844 narrators with tabaqa and dates, and 127,863 critic statements.
- Riwayat's own `kg` crosswalk agreed with the project's name-and-year join on 632 of 632 narrators.

**Importing honestly.** Import these as labelled external candidates with their source as the basis, for example `external:riwayat/source_annotation_thaqalayn`, and carry the CC BY attribution for hadith-kg.

**Importing dishonestly would mean:**

- promoting them to "verified";
- importing Riwayat's `claude_label_mention` rows (38,265 LLM labels) or its ranker guesses as identifications;
- presenting hadith-kg's `aqwal` as the project's own verdicts, including the 11,660 rows attributed to the editor's `تعليق` (commentary);
- leaving Musnad Zayd and Musnad al-Rabi' labelled `sunni` as Riwayat and hadith-kg ship them.

## What I could not verify

- The live site's UI: whether Neo4j's "ثابت" grades or placeholders actually render. I did not browse it.
- The production Postgres database (`railway`). I did not query it, per the brief.
- Why the three files are access-denied. Even `icacls` is refused, so this needs an administrator.
- That the backup bucket objects exist or restore correctly. That needs bucket credentials.
- The contents of the 4,944 Neo4j NameMention nodes.
- Whether the 21 Phase-0 bios in Neo4j differ from the seed script.
- The contribution plan against the schema: on paper, the planned tables cover roles, endorsements, submissions, reviews and comments. Votes, notifications and reputation, which the plan lists, have no table. Mapping existing `curation_audit.actor` text to future contributors is undefined. None of this is built, so none of it is testable.
- The search latency on the live site (the "2 s" figure).

## Appendix: the 40-mention sample

Query: `order by md5(m.id||'adv1') limit 40` over `chain_mentions` with `resolution='source_index'`, joined to narrators, with the full chain for each.

The output, with linked names, is saved at `C:\Users\atooz\AppData\Local\Temp\claude\8b9ecadf913d98e6\95b7dde3-527e-49ce-8f56-83c964db48b2\scratchpad\sample40.txt`. Judgments are given in finding 4.
