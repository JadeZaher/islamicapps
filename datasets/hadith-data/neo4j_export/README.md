# Deterministic Neo4j graph bundle

This package converts one exact schema-v2 (37-column) hadith CSV/CSV.GZ plus
the canonical rawi CSV into a sorted, hash-bound Neo4j bulk-import bundle. It
does not alter either input and does not connect to Neo4j.

```powershell
python datasets/hadith-data/neo4j_export/export_bundle.py `
  --input datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz `
  --rawis datasets/narrator-data/all_rawis.csv `
  --output <new-empty-bundle-directory> `
  --source-release-state development_nonrelease `
  --curation-manifest datasets/hadith-data/development/incomplete-curation/curation_manifest.incomplete.json
```

The exporter writes `manifest.json`, `validation_report.json`, dedicated node
and relationship CSVs, a registry snapshot, `neo4j-admin-import.ps1`, and
`post_import_schema.cypher`. A valid bundle may be structurally
`import_ready=true` while remaining `publication_ready=false`.

Validate again, optionally comparing a second independently generated bundle:

```powershell
python datasets/hadith-data/neo4j_export/validate_bundle.py `
  <bundle-directory> `
  --compare-bundle <second-bundle-directory>
```

The generated loader always runs `neo4j-admin database import full` in dry-run
mode first. It performs the import only with the explicit `-Execute` switch:

```powershell
powershell -File <bundle>\neo4j-admin-import.ps1 `
  -Database <new-database-name> -Execute
```

The loader requires Neo4j 2026.02 or newer, sets UTF-8 string IDs, zero bad
tolerance, strict duplicate/orphan handling, scoped multiline CSV v2, and
`overwrite_destination=false`. The contract was prepared against the 2026.06
operations manual. Apply `post_import_schema.cypher` only after a successful
import.

Machine candidate files are refused as inputs. Schema-v2 rows marked
`machine_unreviewed` are counted as `omitted_machine_candidate` and receive no
Translation node in this canonical graph surface. Blank or unprovenanced
translations are likewise omitted rather than invented; the Hadith row records
the exact disposition. Source-provided/source-status-unknown translations
remain explicit, provenance-bound, non-candidate nodes without acquiring
publication-ready status.

Both documented Thaqalayn source-quality exclusions remain flagged and never
become normal translations or attributions. The confirmed paratext has no
chain assertions; the long report retains source-surface chain evidence when
extractable.

The bundle preserves finite co-transmitter expansions up to 256 branches while
leaving the shared extractor's normal 64-branch guard unchanged. Retried
reports and omitted zero-occurrence branches are counted in the manifest.
