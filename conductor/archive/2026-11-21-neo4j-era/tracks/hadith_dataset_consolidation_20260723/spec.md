---
type: specification
---

# Specification: Hadith Dataset Consolidation and Neo4j Import Bundle

**Track ID:** `hadith_dataset_consolidation_20260723`  
**Type:** Feature / data engineering  
**Priority:** P0  
**Created:** 2026-07-23  
**Depends on:** `uniform_isnad_extraction_20260609`,
`neo4j_isnad_graph_regen_20260516`  
**Production cutover:** Out of scope

## 1. Evidence boundary

The checked-in `all_hadiths_unified.csv.gz` is the preserved legacy 26-column
master. It has 99,283 records but lacks the stable identity, provenance, and
translation-state fields required by this track. The only current 37-column
input is the hash-bound incomplete-curation artifact under
`datasets/hadith-data/development/incomplete-curation/`.

The first bundle is therefore a deterministic `development_nonrelease` graph
bundle. Passing graph-integrity gates makes it safe for an offline Neo4j bulk
import rehearsal; it does not make the underlying corpus publication-ready.
The bundle manifest must preserve the failed curation gates and selected input
hash. It must never claim a canonical publication binding.

The represented traditions are exactly Sunni, Imami, Zaydi, and Ibadi. Shia is
an alias/family label for the represented Imami and Zaydi traditions, not a
fifth corpus tradition.

## 2. Stable identity contract

Every graph identity is derived from an immutable domain key:

- report: the existing namespaced `record_id`;
- narrator/person: `scholar_indx` from the controlled rawi vocabulary;
- collection: a versioned all-work registry, retaining Imami
  `source_work_id` and stable source slugs for other works;
- source asset: the source documentation registry slug;
- chain: report `record_id` plus zero-based branch number;
- name mention: report, branch, and source-order position;
- translation: report identity plus language and content/provenance binding;
- book and chapter: provider/source-supported keys. Thaqalayn uses its URL
  category/chapter locator. OpenITI uses the local heading ordinal plus the
  NFC-normalized source heading because its ordinal resets and no global
  chapter identifier survives in schema-v2.

Unbound display names, numeric dataset row order, live Neo4j IDs, and random
UUIDs are not identity inputs. The OpenITI heading exception above is a bound
source surface, not a display-label substitution.

## 3. Export model

The exporter writes one UTF-8, LF, RFC 4180 CSV per node entity and one per
relationship type. Every file has an inline Neo4j bulk-import header using
string `:ID` namespaces, typed properties, `:START_ID`, `:END_ID`, labels, and
relationship types.

Supported nodes include:

- `Hadith:Report`, `Narrator:Person`, `Source`, `Collection`, `Book`, `Chapter`,
  `Tradition:ReligiousTradition`;
- `Chain`, ordered `NameMention`, `Translation`, `Alias`, and per-report
  provenance `Evidence`;
- typed header-only `Citation`, `Biography`, `Place:Location`, and
  `Event:HistoricalEvent` files while the reviewed evidence bundle remains
  empty.

The graph preserves two isnad layers:

1. each Arabic source-surface branch is exported losslessly as ordered
   `NameMention` occurrences;
2. `RESOLVES_TO`, narrator `INCLUDES`, and occurrence-level
   `NARRATED_FROM` relationships are emitted only for complete
   registry-resolved branches.

No unresolved surface is silently promoted to a person. Branch adjacency is
chain-scoped and carries report, branch, position, source-record, extraction,
and confidence provenance.

Eligible source translations remain separate nodes with their source, model,
status, review state, Arabic binding, and candidate flag. Rows marked
`machine_unreviewed`, including the paused OpenRouter suffix artifact, are not
mixed into the canonical Translation surface; their omission is explicit and
counted. Narrator-alias candidates are also excluded. The two documented
Thaqalayn source-quality exclusions remain explicitly marked and filterable.

## 4. Integrity and release gates

`import_ready=true` requires:

- exact headers, unique namespaced IDs, collision audits, and zero orphan
  relationships;
- one source/collection/tradition membership per report;
- exact input/tradition/source counts;
- contiguous source-order positions for every branch and the expected
  adjacency count;
- exact Arabic UTF-8 round trip and SHA-256 binding;
- complete relationship provenance and explicit translation state;
- manifest-to-file row, byte, header, and SHA-256 agreement;
- byte-identical output from two independent regenerations;
- no machine-candidate or unreviewed identity-candidate inputs.

`publication_ready` is copied from the selected curation/evidence state and is
independent of graph integrity. Empty reviewed biography, place, and event
files are correct while the evidence gate is non-ready.

## 5. Import handoff

The bundle includes:

- `manifest.json` and `validation_report.json`;
- a strict `neo4j-admin database import full` PowerShell command that defaults
  to dry-run, requires Neo4j 2026.02 or newer, uses UTF-8 string IDs, zero bad
  tolerance, no skipped duplicates or relationships, and per-file multiline
  handling;
- `post_import_schema.cypher` for stable-key constraints and lookup indexes.

The normal command must not include destination overwrite. No command is
executed against Railway or any other external Neo4j in this track.
