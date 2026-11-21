---
type: track-spec
title: Neo4j curation export and seed ports
tags: [neo4j-curation-export_20261121, planned]
resource: ./metadata.json
---

# Neo4j curation export

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 7 (the full export list); section 10.3
(tamper review); section 6.1 (legacy grade diff); section 13.3 (seed ports).

## Goal

Every curated row in production Neo4j is either loaded into Postgres with
actor `system:neo4j-migration` or listed with a reason.

## Scope

- Full JSONL dump with `backup-db.ts`, kept off-machine (Q12).
- `export-neo4j-curation.ts` for everything step 7 lists; re-key UUIDs to
  `record_id` and `scholar_indx`; record `bound_arabic_sha256`; report rows
  that cannot be re-keyed and rows that differ from their seeds.
- Port the three seed scripts to `src/scripts/db/seed-*.ts` writing curation
  tables with actor `system:seed`. The Phase-0 bios are irreplaceable.

## Out of scope

Any write to Neo4j; provisioning; the Railway load window (railway-cutover
replays this export in production).

## Acceptance checks

- Exported, loaded and rejected counts reconcile per entity type.
- Every rejected or differing row is listed with a reason.
- The seed ports reproduce their rows on an empty database.

## Open owner questions (section 14)

- Q9: which tradition the Phase-0 narrator verdicts belong to.
- Q10: existing commentaries migrate as `published`?
- Q6: existing parallels migrate as `published`?
- Q12: where the dump and curation archives are kept.
