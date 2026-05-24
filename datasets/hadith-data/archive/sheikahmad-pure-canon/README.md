# Sheikh Ahmad Pure Canon Pipeline

Processing pipeline for the "Hadith Pure Canon Authentica" and "Green Book of Sahih Hadith"
datasets from SheikhAhmad / NabiMuhammad.com.

## Pipeline Steps

1. Excel source files → `extract_xlsx_to_jsonl.py` → `pure_canon.jsonl`, `green_book.jsonl`
2. Translation → `pure_canon_en.jsonl`
3. `import-pure-canon.ts` — Import into Neo4j database
4. `canon-normalize.ts` — Normalize source names
5. `rename-anthology-sources.ts` — Rename anthology sources to canonical names
6. `scholar-graph-actions.ts` — Scholar graph relationship actions

## Key Files

| File | Description | Size |
|------|-------------|------|
| `pure_canon.jsonl` | Full canon dataset as JSONL | 68 MB |
| `green_book.jsonl` | Green Book dataset as JSONL | 59 MB |
| `pure_canon_en.jsonl` | English translations | 2.9 MB |
| `prompt_hadith_ar_to_en.txt` | Translation prompt |  |
| `run_translations.sh` | Translation batch script |  |
| `sheikahmad.zip` | Backup zip of directory | 54 MB |

## Status

Completed. Source Excel files remain in `sheikahmad/` for reference.
Data imported into the application database.
