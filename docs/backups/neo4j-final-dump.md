# Neo4j final dump (2026-11-21)

Complete, read-only export of the old Neo4j store (service `neo4j-hadith-graph-alltraditions`), taken before retirement. Nothing reads that store any more; the production data lives in Postgres.

Exporter: `src/scripts/ops/export-neo4j-final.cjs` (MATCH / RETURN / SHOW only; keyset pagination on `id()`, batches of 10,000). Run: `NODE_PATH=node_modules node src/scripts/ops/export-neo4j-final.cjs <output dir>` with `NEO4J_URL`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in the environment. The older `src/scripts/backup-db.ts` was not used: it paginates with `SKIP`, which is quadratic over 1.5 M relationships, writes into the repository and records the connection URL in its manifest.

## Where it is

Bucket `dataset-backups`, prefix `neo4j-final/2026-11-21/`:

| Object | Bytes | SHA-256 |
|---|---|---|
| `nodes.jsonl.gz` | 57,089,478 | `e3328ad48d3cbe1a7c565aeba9138543c611ba7ee345c2793dbb3e300273230c` |
| `relationships.jsonl.gz` | 13,494,697 | `bf9a1bd36e17c87e93e774b0d7c0c182681b9a7e0dd3b875db01e1f090addb5e` |
| `manifest.json` | 35,848 | `003618b7dd0d779577045f0fe928b9e080e38d36400fc96398158bb78034e985` |

All three were re-downloaded from the bucket and re-hashed (match), and the two data files were decompressed and recounted from the downloaded copies. Local manifest: [`neo4j-final-2026-11-21.manifest.jsonl`](neo4j-final-2026-11-21.manifest.jsonl).

## Counts (exported equals `MATCH` counts, per label and per type)

626,938 nodes and 1,539,277 relationships; reconciled `true` in `manifest.json`.

| Label (a node counts once per label) | Nodes | | Relationship type | Count |
|---|---|---|---|---|
| Assessment | 399,064 | | HAS_ASSESSMENT | 399,064 |
| Hadith | 99,283 | | UNDER_SCHEME | 399,064 |
| Chain | 99,283 | | INGESTED_IN | 198,566 |
| Narrator | 24,326 | | INCLUDES | 159,550 |
| NameMention | 4,944 | | FROM_SOURCE | 99,283 |
| Source | 32 | | FROM_TRADITION | 99,283 |
| ReligiousTradition | 4 | | HAS_CHAIN | 99,283 |
| DatasetVersion | 2 | | NARRATED_FROM | 80,240 |
| | | | INCLUDES_MENTION | 4,944 |

The store holds no commentary, event or parallel nodes: only the 21 hand-written biographies (properties on `Narrator` nodes) are curation content.

## Format

Gzipped JSON lines, UTF-8.

- `nodes.jsonl.gz`: `{"id": <internal id>, "labels": [...], "props": {...}}`
- `relationships.jsonl.gz`: `{"id", "type", "start", "end", "props"}` where `start` / `end` are node `id`s.
- Values: integers and strings as JSON; Neo4j integers outside the 2^53 range as `{"$int": "<digits>"}`; temporal values as `{"$temporal": <type>, "value": "<iso>"}`; points as `{"$point": {...}}`.
- `manifest.json`: server components, `SHOW INDEXES` and `SHOW CONSTRAINTS`, expected and exported counts, `reconciled`.

Read it: `gzip -dc nodes.jsonl.gz | head`, or in Python `for line in gzip.open(path, "rt", encoding="utf-8"): json.loads(line)`. Internal ids are only stable within this export; use `props` keys (such as `scholar_indx`) to identify entities.

## Hand-written biographies versus the seed script

The 21 narrators in `src/scripts/seed-narrator-bios-phase0.ts` were compared field by field with the dump. All 21 carry `bio_provenance = manual_phase_0`. Biography text (`bio_summary`, `bio_tadil`, `bio_jarh`), names, kunya, nasab, nisba, `reliability_consensus`, `reliability_disagreement` and `critic_quote_count` are identical to the script for every narrator: no hand edits to the text. The only differences:

- `tabaqah` and `geographic_region` are the empty string in Neo4j for all 21 (the script sets values such as `SAHABA`, `Madīna`). The script's values are the intended ones; the blanks look like a later bulk load overwriting them, not a manual change.
- `death_date_gregorian` is null in Neo4j for 7 narrators (the script sets it; its Cypher uses `coalesce`, so an existing value would win, and none existed).

The script is therefore the authoritative copy of the biographies.
