# Track: Multi-Axis Timelines & Cultural-Contact Grid (`timelines-and-contact-grid_20261127`)

## Objective
Model hadith transmission (*isnad* + *matn*) as a **spatiotemporal and sociocultural grid** (narrator × place × era × political/technological/cultural context) so researchers can inspect:
- Place-specific timelines with time-sliced demographic, ethnographic, religious, and political profiles (e.g., Kufa in 40 AH vs. 150 AH).
- Dedicated world, political, intellectual, and technological timelines (writing media, paper adoption, *tadwin*, *fitnahs*, *mihnah*, pilgrimage/trade routes).
- Narrator mobility (`narrator_residences`) and social/scholarly roles (`narrator_affiliations`).
- Cited scholarly observations on *Isra'iliyyat*, cross-cultural parallels, and regional milieu — strictly attributed and review-gated.

## Epistemic Rules
1. **No machine-asserted influence**: Contextual overlap (a narrator living in a city during an event) is always visually separated from directly attested links (`narrator_events`, `narrator_residences`).
2. **Citations as links**: Every timeline entry, place snapshot, residence, and parallel carries a `citation_id` (linking to `bibliographic_works` / `editions` / external URLs where available).
3. **Public vs. review gate**: `candidate_only` rows stay hidden from public views until promoted by human review.

## Proposed Additive Schema (`0025_timelines_and_contact_grid`)
1. `timeline_tracks`: `id`, `slug`, `category` (`political`, `world_event`, `technological`, `intellectual_movement`, `demographic_shift`, `legal_theological`, `trade_pilgrimage`), `scope` (`global`, `regional`, `city`), `description`.
2. `place_snapshots`: `id`, `location_id`, `year_min`, `year_max`, `precision`, `polity_or_ruler`, `dominant_schools`, `religious_communities` (`jsonb`), `languages` (`text[]`), `ethnographic_notes`, `citation_id`, `review_state`.
3. `narrator_residences`: `id`, `narrator_id`, `location_id`, `year_min`, `year_max`, `precision`, `role` (`born`, `studied`, `taught`, `qadi`, `governor`, `rihla_visit`, `died`), `citation_id`, `review_state`.
4. `narrator_affiliations`: `id`, `narrator_id`, `kind` (`tribe`, `mawla_of`, `legal_school`, `theological_tendency`, `political_faction`, `convert_background`, `profession`), `label`, `note`, `citation_id`, `review_state`.
5. `external_tradition_parallels`: `id`, `hadith_id`, `tradition_source` (`biblical`, `midrash_talmud`, `syriac_christian`, `sasanian_andarz`, `pre_islamic_poetry`, `other`), `relation_type` (`direct_quote`, `structural_parallel`, `shared_motif`, `polemical_response`), `source_work`, `locator`, `note`, `citation_id`, `review_state`.
6. Optional `track_id` FK on `historical_events` + `GiST` / btree range indexes on `(year_min, year_max)` for fast spatiotemporal overlap queries.

## UI Requirements
- Default narrator and isnad timelines remain clean and scannable.
- Add toggleable **Context Layers** (`Political`, `Places & Demographics`, `Tech & Writing`, `Parallels & Isra'iliyyat`) with clear badges distinguishing attested vs. contextual items and clickable source links.
