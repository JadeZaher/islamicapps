# Research Task: Source Complete Musnad al-Shafi'i Dataset

## Problem

The Shafi'i data in `pure_canon.jsonl` (2,054 rows) has **zero chain/isnad data and zero hadith numbers**. Only the matn (body text), rulings, and topic tags are present. The text is fully vocalized (tashkeel), suggesting it was extracted from a specific digital edition that separated matn from isnad.

### What we have

| Field | Populated | Notes |
|---|---|---|
| `text_ar` | 100% | Full matn with diacritics |
| `ruling` | 100% | All marked `ثابت` (established) |
| `topics` | 100% | Comma-separated Arabic tags |
| `shelf_no` | 100% | Unique sequential (112,924–115,216), usable as sort key |
| `chain` | **0%** | Completely empty |
| `hadith_no` | **0%** | Completely empty |

No transmission verbs (`حدثنا`, `عن`, etc.) found in `text_ar` either — the isnad was fully stripped at source.

### What we need

1. **Hadith numbers** — canonical numbering from a known edition of Musnad al-Shafi'i
2. **Isnad/chain text** — Arabic chain of transmission for each hadith
3. **Narrator identification** — map chain narrators to `scholar_indx` IDs

## Research Approaches

### Option A: Find a complete digital dataset (Recommended)

Look for a digital edition of Musnad al-Shafi'i that includes both matn and isnad:

- **shamela.ws** (al-Maktaba al-Shamila) — the most comprehensive Arabic text library. Musnad al-Shafi'i is catalogued there. Export as structured text.
- **islamweb.net** — has hadith databases with full isnad
- **sunnah.com** — may have partial coverage
- **HadithSoftware / Jawami' al-Kalim** — commercial hadith software with complete isnads
- **dorar.net** (al-Durar al-Saniyya) — another hadith database

**Steps:**
1. Check shamela.ws for Musnad al-Shafi'i (الأم / مسند الشافعي)
2. Export or scrape the text with isnad preserved
3. Match to our existing matn text (fuzzy match on Arabic body)
4. Extract `hadith_no` and `chain` fields

### Option B: Cross-reference from other collections

Many hadiths in Musnad al-Shafi'i also appear in the kutub al-sittah. We could:
1. Normalize and fingerprint each Shafi'i matn
2. Search for matching matn in our existing 34k+ hadiths
3. Copy the chain data from the matching hadith

**Limitations:** Only works for hadiths that also appear in other collections. Musnad al-Shafi'i has unique narrations not found elsewhere.

### Option C: Manual hadith numbering only

Use `shelf_no` or sequential numbering as `hadith_no` and import without chains. The isnads can be added later as an enrichment pass.

**Current plan:** This is what the import track does for now — Shafi'i goes in as matn-only with `shelf_no`-based ordering.

## Recommended Next Steps

1. Check shamela.ws for availability of the full Musnad al-Shafi'i with isnads
2. If available, write a Python script to parse the Shamela export format and extract chain + hadith_no
3. Match to our existing `pure_canon.jsonl` rows by matn text similarity
4. Produce an enriched JSONL or CSV with `chain` and `hadith_no` populated
5. Re-import to Neo4j

## Notes

- The Musnad al-Shafi'i is relatively small (~2,054 hadiths) so manual verification is feasible
- The `ruling` field is 100% populated with `ثابت` — this may indicate the data came from a pre-filtered/authenticated subset
- The edition used appears to be from a legal compilation (al-Umm) rather than a standalone musnad, which would explain the missing isnads
