---
type: implementation-plan
---

# Implementation Plan: Hadith Dataset Consolidation

**Track ID:** `hadith_dataset_consolidation_20260723`  
**Spec:** `./spec.md`

## Phase 0 — Inventory and contract

- [x] Inspect the canonical and incomplete-curation artifacts, generators,
  source registries, quality reports, isnad extraction, conductor tracks, and
  Neo4j loaders.
- [x] Confirm the 99,283-record, four-tradition input profile and the
  legacy-versus-schema-v2 mismatch.
- [x] Define immutable ID namespaces, the source/collection split, the
  surface-first isnad model, candidate isolation, and release-state semantics.
- [x] Confirm that production cutover and canonical dataset replacement are
  outside this track.

## Phase 1 — Deterministic exporter

- [ ] Add a versioned all-work source registry covering every observed
  collection.
- [ ] Export dedicated typed node and relationship CSVs in deterministic order.
- [ ] Preserve every Arabic report byte-for-byte with a SHA-256 binding.
- [ ] Export ordered branch/mention evidence and only complete narrator
  resolutions.
- [ ] Export translations with provenance/review state and explicit
  source-quality exclusions.
- [ ] Keep evidence-gated canonical entities header-only when no reviewed
  claims exist.

## Phase 2 — Validation and manifest

- [ ] Validate headers, IDs, domain-key collisions, endpoints, branch order,
  adjacency, source/tradition normalization, Arabic hashes, translation state,
  and candidate separation.
- [ ] Write a content-addressed manifest with per-file counts, byte sizes,
  headers, hashes, aggregate counts, input bindings, and curation gate state.
- [ ] Generate a machine-readable validation report that distinguishes
  `import_ready` from `publication_ready`.
- [ ] Regenerate twice and require byte-identical bundle contents.

## Phase 3 — Offline import handoff

- [ ] Generate a strict dry-run-first `neo4j-admin` command without overwrite.
- [ ] Generate post-import constraints and indexes.
- [ ] Document the exact local import and validation workflow.
- [ ] Record a real `neo4j-admin` dry run as deferred when the CLI is not
  installed; do not substitute an external database push.

## Phase 4 — Integrated verification

- [ ] Run the full Python hadith suite once.
- [ ] Run the annotation-fixture tests and isnad evaluator.
- [ ] Run the relevant TypeScript regeneration contracts once.
- [ ] Run TypeScript and lint once.
- [ ] Have an independent verifier audit the produced bundle and final diffs.

