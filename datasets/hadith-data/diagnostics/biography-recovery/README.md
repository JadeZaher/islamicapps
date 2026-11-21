# biography-recovery

Candidate narrator biography and assessment data recovered from assets already on disk. Every row carries the verbatim source cell, its file and row locator, `review_state: unreviewed_*` and `citation_id: null`. Nothing is a verified claim, no identity is asserted, competing values stay as separate rows, and no narrator gets a single reliability value. Standard library only; no database, no network.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/narrator-data/all_rawis.csv` | `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11` |
| `datasets/hadith-data/diagnostics/biography/lexicon_defects.jsonl` | `1eaedb1a6534210c6fdc8c060159f39762562498f59db79f91e55a1dd641f906` |
| `src/scripts/seed-narrator-bios-phase0.ts` | `77e7495a0cbddfd295342bfa422f973b0ee90adb3fd14433ec7d37b0ae71cab2` |
| `datasets/archive/loose-files-20260610/musnad_rawis.csv` | `e2a8f406915a1a6c2bb95ec6dcfff827d79b9fa45c7b29135e716b467b5712da` |
| `datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon.jsonl` | `0cb5ec01959b326c895a6063574955997067e8646c103863285403c3ba6550ac` |
| `datasets/hadith-data/{ibadi,zaydi,rida}-hadith/parsed_hadiths.json` | `c8dc2feb...`, `2dc24d9c...`, `89c15505...` (full values in `local_asset_inventory.json`) |
| OpenITI headers under `datasets/hadith-data/openiti-sources/` | full values in `local_asset_inventory.json` |

## Commands (each about 1 to 3 s, run from the repository root)

```
python -B datasets/hadith-data/diagnostics/biography-recovery/recover_biography_from_lexicon.py   # part A
python -B datasets/hadith-data/diagnostics/biography-recovery/inventory_other_local_biography.py  # part B
python -B datasets/hadith-data/diagnostics/biography-recovery/propose_defect_repairs.py           # part C
cd datasets/hadith-data/diagnostics/biography-recovery && python -B -m unittest test_lexicon_raw_parsing
```

`lexicon_raw_parsing.py` is the pure parser (years in the BH era are stored negative; ranges, "or" alternatives, `~`, `after`, `before`, `(est.)` are kept as qualifiers; an inferred era is flagged).

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `biographical_assertion_candidates.jsonl` | 60,725 | A. One row per narrator, predicate (`birth_year`, `death_year`, `birth_place`, `death_place`, `residence`, `tabaqah`) and calendar; shaped for `biographical_assertions`. `relation_to_parsed_column` says whether the parsed CSV column agrees, is new, or loses information |
| `narrator_assessment_candidates.jsonl` | 17,045 | A. The lexicon's verdict-like label from `area_of_interest` (`Narrator[Grade:Thiqah] [ ع - ثقة ]`): English label, Arabic term, book symbols, verbatim cell. `critic` is null, `tradition_id` is null |
| `raw_vs_parsed_discrepancies.jsonl` | 1,421 | A. Rows where the parsed column lost a qualifier or range, lost the BH sign, or disagrees with the raw cell |
| `marker_vs_death_year_tensions.jsonl` | 30 | A. Generation marker incompatible with the death year in the same row |
| `phase0_seed_candidates.jsonl` | 21 | B. Hand-written Phase-0 seed fields with `file:line`, joined on `scholar_indx`, with the lexicon death cell beside them |
| `ibadi_musnad_rawis_candidates.jsonl` | 19 | B. Ibadi narrator rows (ids 60001 to 60020) that are not in `all_rawis.csv`; name-join result recorded |
| `provider_sanad_detail_narrators.jsonl` | 25 | B. Distinct (name, tabaqah, school) triples from parsed Ibadi, Zaydi and Rida chains |
| `openiti_header_author_edition_claims.jsonl` | 15 | B. Author and publisher lines from OpenITI headers |
| `pure_canon_compiler_edition_header_claims.jsonl` | 8 | B. Compiler birth/death and printed edition from Pure Canon header rows |
| `local_asset_inventory.json` | | B. Every asset examined and what joins |
| `defect_repair_proposals.jsonl` | 236 | C. One proposal per existing J8 flag (classification, disposition, evidence) |
| `death_reason_natural_default_proposals.jsonl.gz` | 20,325 | C. One proposal per `Natural` death reason that has no death date |
| `recovery_summary.json`, `defect_repair_summary.json` | | Counts quoted in the report |

## Reading the numbers

- Years: the parsed columns already hold almost every year the raw cells contain (4 narrators gain a death year). The loss is in precision: 1,141 death and 187 birth values kept one number of a range, alternative or qualified date; 90 BH values lost their sign in the CSV.
- Generation markers: the lexicon `grade` column is a generation/class marker (`Follower(Tabi') [6th generation]`, `3rd Century AH`), not a verdict. Every row has one; 8,312 have a number.
- `narrator_assessment_candidates.jsonl` labels have no named critic. The layout resembles the Taqrib convention; that resemblance is recorded as a note, not as an attribution.
- Part C: all 38 inverted pairs, 48 of 50 birth and 8 of 27 death Gregorian disagreements come from BH dates; `src/scripts/lib/regen/io.ts:351-361` already restores that sign at load, so those 94 J8 flags are false positives of an unsigned comparison. The 121 zero death years and the 20,325 defaulted `Natural` values are not corrected by the loader.
- Name joins in part B are exact normalized-Arabic equality and are review candidates only.
