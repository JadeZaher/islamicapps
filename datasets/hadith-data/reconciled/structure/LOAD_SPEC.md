# Load specification (for the schema owner; nothing here is implemented)

Inputs: the files in this directory, keyed by `record_id` (= `hadiths.record_id`). The loader refuses a row whose
`work_id` differs from the report's `collections.source_work_id`, whose `record_id` is not live, or a provenance record
that fails `structure_provenance.validate_record` (re-run it; it reads `src/lib/sources/registry.ts`). Rebuild the
sidecars if the corpus or projection changes.

## 1. Columns on `hadiths` (additive migration)

| Column | Type | Fed by | Notes |
| --- | --- | --- | --- |
| `report_number` | text | `report_structure.report_number_display` | The work's own number (`8.2`, `3604b`, `1b`). Null when the source gives none. `hadith_no` stays untouched (it holds the chapter number for Thaqalayn and is what the old addresses saw); stop displaying it |
| `report_number_int` | int generated | from `report_number` (`^[0-9]+$`) | for sorting only |
| `number_scheme` | text check in (`continuous_work`, `per_chapter`, `unit_in_book`, `per_section`) | `number_scheme` | Null when no number. `number_scope` (`work`, `book`, `chapter`, `section`) beside it |
| `hadith_in_chapter` | int | `hadith_in_chapter` | Thaqalayn URL last segment |
| `source_order` | int not null | `source_order` | 1..N per work, unique per work; reproduces the printed or source order (basis in `source_order_basis`, kept in provenance) |
| `section_ordinal`, `section_label` | int, text | `section_ordinal` (derived), `section_companion` | Musnad Ahmad only. Show "Section k", never as a heading the source gave |
| `volume` | text | `volume` (already loaded for Imami, Ibadi, Zaydi) | Fill nothing for Sunni: no source gives a volume |
| `edition_id`, `edition_volume`, `edition_page` | text FK to `editions`, text, text | `edition_text`, `edition_volume`, `edition_page` | `editions` is empty today: create one row per distinct `edition_text` per work (verbatim, `locator_scheme` = `openiti_page_marker` or `pure_canon_edition_header`). Ibadi pages are asserted to match the print, Zaydi/Rida are not (`edition_pagination_asserted_to_match_print`) |
| `reference_key`, `reference_text`, `reference_unique` | text, text, bool | same names | `reference_key` is unique in its work exactly when `reference_unique`; a report without a key is cited by its stable id |
| `loaded_chapter_*`, `loaded_edition_page` | text | same | do not load: they record what the earlier load had, for review |

Chapters and books (`books`, `chapters`): load `structure_nodes.jsonl.gz` (natural key = work, volume, book number,
chapter number, title; ids are the loader's hash of that key). Thaqalayn: book = `categoryId`, chapter =
`chapterInCategoryId`, as `chapters.provider_chapter_locator` already stores. Ibadi: books (kitab titles, no number) and
chapters (bab number restarts in every kitab, so the key includes the kitab title). Zaydi/Rida: titles only, no numbers.
**Sunni works get no chapter rows: no source on disk or in hadith-kg or Riwayat has a bab.** The six books keep their
kitab in `books`. Correct the 53 Ibadi reports whose `chapter_id` differs from `report_structure` (`loaded_chapter_*`).

## 2. Provenance table (new, pipeline-written)

`report_reference_provenance(hadith_id fk, field text, value text, claim_by text check in ('project_source_file','external_dataset'),
kind text check in ('source_value','derived'), derivation text, source_code text fk to the sources registry, licence text,
source_file text, source_sha256 char(64), source_version text, source_record_id text, source_field text, edition text,
review_state text, primary key (hadith_id, field))`. Checks: `source_sha256 ~ '^[0-9a-f]{64}$'`; `kind='derived'` implies
`derivation` not null; `claim_by='external_dataset'` implies `source_code in ('HKG','RWY')` and `source_version` not null;
`field like 'edition%'` implies `edition` not null. Feed: `reference_provenance.jsonl.gz` (the 450,542 project rows; use
`group` to map to a column group), external rows go to the same table with `field` in (`external_number`, `edition_page`)
and are the datasets' claims, never copied into `hadiths`. Optional: load `external_locator_claims` for "other editions
number this report ..." display, shown only with its source code and "unreviewed".

## 3. Citation block and browse pages

- Citation text: work, then `reference_text` when `reference_unique`, else the stable address only; add edition and page when
  `edition_page` is set (`edition as named by source`, "vol. v, p. n"); add "section k" for Ahmad. Never print `hadith_no`
  for Thaqalayn. Add the source short reference (code and name, from the provenance row's `source_code`).
  `src/lib/citation/reference.ts` can read `reference_text` instead of rebuilding it from the URL.
- Browse order: `order by collection_sort_key, source_order`; page by keyset `(source_order)`. Book/chapter headings come
  from `books`/`chapters`; Ahmad shows section ordinals.
- Works with no `reference_key` (Shafi'i, Zaydi, Rida, Ahmad openers) show "No printed number in this copy" and keep the id.

## 4. Index and constraints

```sql
create unique index hadiths_collection_source_order_key on hadiths (collection_id, source_order) where retired_at is null;
create index hadiths_browse_order_idx2 on hadiths (collection_sort_key, source_order);   -- replaces (collection_sort_key, hadith_no_int, id)
create unique index hadiths_collection_reference_key on hadiths (collection_id, reference_key) where reference_unique;
```

Drop `hadiths_browse_order_idx` after the browse query moves. `source_order` is dense per work at load time; a later load
that inserts reports renumbers inside one transaction (or use gap-allocating keys if that is too costly).
