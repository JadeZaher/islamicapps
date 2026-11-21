---
type: implementation-plan
title: Vectors and semantic search plan
tags: [vectors-semantic-search_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Vectors and semantic search

Track: `vectors-semantic-search_20261121`. Spec: [./spec.md](./spec.md). Design steps: 11.

## Phase 0 — Decide

- [ ] Owner answers Q8.

Done when: model and width are recorded.

## Phase 1 — Benchmark

- [ ] Embed a sample offline; benchmark the filtered query (section 7.4).

Done when: benchmarks are recorded (section 12 step 11 done-when).

## Phase 2 — Ship

- [ ] Core migration for `hadith_embeddings`; full offline embedding; load.
- [ ] Similar-hadiths query and UI.

Done when: the feature serves only public rows in production.
