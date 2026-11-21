# Graph evidence contract

## Current compatibility layer

Narrator and historical-event scalar properties are compatibility projections, not publication evidence. No loader may treat a provenance tag, raw date string, or unverified seed marker as a citation. Historical seed nodes remain `publication_ready=false` and `verification_status=unverified_seed` until separately curated.

The interim historical read gate requires `publication_ready=true`, `verification_status` equal to `human_verified` or `source_verified`, a nonblank `citation_source`, and either a nonblank `citation_locator` or `citation_url`. This is fail-closed scaffolding; it does not replace the target citation graph.

`seed-historical-data.ts` may refresh deterministic content only while an event remains both `unverified_seed` and unpublished. Once an event is reviewed or published, rerunning the seed must preserve its claim text, interval, category, significance, and citation state; a changed seed definition requires a new review rather than inheriting stale approval.

## Target biography and history model

The future source-authenticated model should add these stable-keyed nodes and relationships without overwriting competing evidence:

```text
(Person:Narrator)-[:HAS_BIO_ASSERTION]->(BiographicalAssertion)
(Person:Author)-[:HAS_BIO_ASSERTION]->(BiographicalAssertion)
(BiographicalAssertion)-[:SUPPORTED_BY]->(Citation)
(Citation)-[:IN_EDITION]->(Edition)-[:EDITION_OF]->(BibliographicWork)
(Source)-[:COMPILED_BY]->(Person)
(HistoricalEvent)-[:HAS_DATE_ASSERTION]->(TemporalAssertion)
(Epoch)-[:HAS_DATE_ASSERTION]->(TemporalAssertion)
(TemporalAssertion)-[:SUPPORTED_BY]->(Citation)
(HistoricalEvent)-[:WITHIN_EPOCH]->(Epoch)
(Person)-[:INVOLVED_IN {role}]->(HistoricalEvent)
```

A biographical date assertion carries calendar, minimum/maximum year, precision, uncertainty, review state, and supersession lineage. Published people require cited birth and death assertions, but a cited unknown or open range is valid; an exact year must never be invented. All conflicts remain queryable. Only reviewed preferred assertions may materialize compact lifetime bounds on `Person` for interval queries.

Use unique stable keys for people, works, editions, citations, assertions, events, and epochs. Index materialized lifetime bounds and historical start/end years. Normalize work/edition/citation data instead of duplicating bibliographic strings on every person. Do not create narrator-by-event contextual overlap edges; compute indexed interval overlap at read time and persist only direct involvement.

DatasetVersion promotion must eventually require cited reviewed lifespan claims, author links, cited event/epoch ranges and overviews, valid intervals, and explicit preservation of disagreements. The schema reserves stable IDs and lookup indexes for these nodes; no curation importer writes them until the citation bundle and review workflow are implemented.
