---
type: standard
applies_to: every claim shown to a reader, every AI review, every human review, every discussion post that asserts a fact
checkable_form: src/lib/review/citation-standard.ts
validator: reviews/tools/validate-citations.ts
---

# The citation standard

One standard, the same everywhere. A claim a reader sees either carries a citation that passes this standard or is
labelled **not yet cited**. The standard is code (`src/lib/review/citation-standard.ts`); this page is its prose form.

## The citation record (`shura-citation/1`)

| Field | Required | What |
| --- | --- | --- |
| `work.author`, `work.title` | yes | The author and title of the work (for a dataset, its compiler and name) |
| `work.tradition` | yes | `Ibadi`, `Imami`, `Sunni`, `Zaydi` or `none`: the tradition the work belongs to, so its view sits in the right group |
| `edition` | yes | The edition or digital source **exactly as its header or metadata names it** (OpenITI: editor, publisher, place, year and the OpenITI version URI) |
| `locator` | yes | One of four kinds, below |
| `passage.text`, `passage.language` | yes | The verbatim passage relied on, in the original language. Never a paraphrase |
| `passage.span` | when the passage is part of a stored text | `field`, `start`, `end` in code points of that text; `end - start` equals the passage length |
| `source.code`, `source.licence` | yes | The short reference and licence from `src/lib/sources/registry.ts` (the licence must match the registry) |
| `checked_against_sha256` | yes | SHA-256 of the text the citation was checked against (the report's Arabic, the OpenITI file, the passage) |

Locators:

| Kind | Required fields |
| --- | --- |
| `print` | at least one of `page`, `entry`, `number` (a volume alone is not a locator); `volume` where the work has volumes |
| `web` | `url` (https) and `retrieved` (YYYY-MM-DD) |
| `dataset` | `dataset` name, `version` (revision, release or dataset version id) and `record_id` |
| `quran` | `sura` (1-114), `aya_from`, `aya_to` |

## What cites what

| Claim | Accepted locators | Also required |
| --- | --- | --- |
| Identity of a name in a chain | `print` (a rijal entry), `dataset` (a source's index record) | |
| Correspondence of two tellings | `dataset`, `print`, `web` | **two** citations, one per text |
| Translation | `dataset`, `print`, `web` (the Arabic source) | the translator or model is credited separately, never as the citation |
| Grading | `print` (the grader's work), `dataset` (the source that records it, as "as recorded by") | the grader named in `work.author` |
| Narrator verdict, biographical value, rijal link, event or era | `print` | a dataset record alone does **not** cite these |
| Qur'an citation | `quran` | `passage.span` in the report text |
| Numbering or edition reference | `dataset`, `web`, `print` | |
| Human review, discussion post | any | the post asserts a fact (`asserts_fact`); questions and opinions need no citation |
| AI specialist review | its evidence quotes are checked against the packet; the packet's passages carry these citations | |

## Not acceptable

- A bare book title, or a title and volume with no page, entry or number.
- "General reference works", "well known", "various sources", "common knowledge".
- A dataset with no version or no record id.
- An AI's own knowledge. A model may find a passage; the citation is the passage, never the model.
- A paraphrase instead of the verbatim passage.

## Not yet cited

A claim without an acceptable citation is shown only where the owner has decided so, and always under the label
**not yet cited** with its `shown_under` reference to that decision. Today: narrator-lexicon dates, places and
generations ("narrator lexicon, not yet cited", fourth-round decision), and the 21 hand-written narrator verdicts. A
claim with no such decision is not shown.

## How a reader verifies a claim

Every claim shows a short source reference (`SourceCredit`) linking to its record on `/sources`. A cited claim shows
the work, edition and locator, and the passage on request; the passage's span and hash let anyone find it in the
digital text and confirm it is unchanged. `/method#<kind>` says what was checked and how well.

## How a contributor adds a citation

In a review file (`reviews/README.md`), each citation is one object in the format above. Copy the passage exactly
from the edition you name; give the page or entry; set `source.code` to the registry code of the source you read it
in (`RIJ` for the OpenITI rijal texts, `OITI` for other OpenITI texts) and its licence. If your edition is not in the
registry, cite it fully anyway (`work`, `edition`, `print` locator, passage) under the nearest code and say so in the
note; the maintainers add the source record. Run `npx tsx reviews/tools/validate-reviews.ts`.

## What each data lane's output must contain to pass

Run `npx tsx reviews/tools/validate-citations.ts <claims.jsonl>` on a JSONL of
`{claim_kind, claim_key, citation_status, citations, label?, shown_under?}`. Per lane:

| Lane output | Claim kind | Each record must carry |
| --- | --- | --- |
| `datasets/hadith-data/rijal/` (`rijal_extract.py`) | `rijal_link`, `biography`, `narrator_verdict` | `work` (rijal author, title, the author's tradition), `edition` from the OpenITI header, `print` locator with entry number and volume/page, the entry's verbatim passage with its span in the OpenITI file, `source: RIJ / CC BY-NC-SA 4.0`, the file's SHA-256. A verdict also names the critic (`work.author`, or the critic quoted inside the passage) |
| `datasets/hadith-data/assessments/` (`assessment_logic.py`) | `grading`, `narrator_verdict` | Thaqalayn gradings: `dataset` locator (Thaqalayn, retrieval date, the hadith's URL id) with the grading text verbatim, `work.author` the grader, and the grader's own work and volume/page kept in the passage as recorded; Tirmidhi statements: `dataset` locator of the report with `passage.span` into `text_ar`. `ثابت` collection labels are not claims and emit nothing |
| `datasets/hadith-data/history/` | `history` | Already carries a complete citation block and runs its own `validate_citations.py`. Map: book and author to `work`, OpenITI edition to `edition`, volume/page to a `print` locator, the quoted span with its offsets and the file SHA-256 |
| `datasets/hadith-data/quran/` | `quran_citation` | `quran` locator (sura, ayas from Tanzil), `passage.span` into the report's `text_ar`, `checked_against_sha256` = the report's `arabic_sha256`, the verse text credited to Tanzil (CC BY 3.0; to be added to the source registry) |
| `datasets/hadith-data/reconciled/structure/` | `numbering` | `dataset` locator (provider, version or retrieval date, the provider's record id) or the provider's URL with retrieval date; the number cell verbatim |
| `datasets/hadith-data/reconciled/` external identity sidecars | `identity` | `dataset` locator: hadith-kg revision `8ae7e3d5` or Riwayat v1 (Zenodo 23630501), record id = external report, chain and position; passage = the external name as the dataset writes it; `source: HKG` (CC BY 4.0) or `RWY` (CC0); checked against our report's `arabic_sha256` |
| `datasets/hadith-data/diagnostics/report-correspondence-v2/` | `correspondence` | Two `dataset` citations (this archive's dataset version, record id = each hadith id), each passage the matched wording with its span, `source` = each text's own source code (`SUN`, `THQ`, `OITI`, `NMC`), checked against each `arabic_sha256` |
| `datasets/hadith-data/machine_translation_candidates/` | `translation` | One citation of the Arabic: the text source's `dataset` locator and record id, the Arabic as passage, `checked_against_sha256` = `arabic_sha256`. The model (`tencent/hy-mt2-30b-a3b`, prompt version) is the producer, credited by `SWI`, not the citation |
