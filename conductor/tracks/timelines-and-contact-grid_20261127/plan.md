# Plan: Multi-Axis Timelines & Cultural-Contact Grid

## Phase 1 — Schema & Migration (`0025`)
- [ ] Add `src/db/schema/timelines.ts` defining `timeline_tracks`, `place_snapshots`, `narrator_residences`, `narrator_affiliations`, and `external_tradition_parallels` (with `pipelineBookkeeping()` / `review_state` and `ON DELETE RESTRICT` FKs).
- [ ] Generate additive migration `drizzle/core/0025_timelines_and_contact_grid.sql`, update `src/db/verify.ts` (`EXPECTED_TABLE_COUNT`), verify with `npx drizzle-kit check` and `glossary.test.ts`.
- [ ] Apply `0025` to production and verify `npm run db:verify` + `npm run db:verify-data`.

## Phase 2 — Seed & Staged Loaders
- [ ] Seed core `timeline_tracks` (`political`, `world_event`, `technological`, `demographic_shift`, `intellectual_movement`, `trade_pilgrimage`) and classify existing 105 `historical_events`.
- [ ] Build idempotent `src/scripts/db/load-timelines-grid.ts` (with `--dry-run`, `BATCH_SIZE = 500`, citation FK checks) for staged place snapshots, technological milestones, narrator residences/affiliations, and cited external-tradition parallels.
- [ ] Extend `src/scripts/db/bench-completeness.ts` to track coverage of all new timeline & contact-grid tables.

## Phase 3 — Queries & Toggleable UI
- [ ] Extend `src/db/queries/timeline.ts` with track-filtered spatiotemporal overlap queries (narrator residences × place snapshots × tech/world tracks + cited parallels).
- [ ] Add toggleable **Context Layers** to `NarratorTimeline.tsx` and `ChainTimeline.tsx` (following `C:/Users/atooz/.gemini/UI-UX-guidance.md`), keeping default view clean and rendering every citation as a clickable link via `CitationLink.tsx`.
- [x] Add flow tests covering public vs. review gating, layer filtering, and citation links.

## Phase 4 — Deep Pre-Hijri Cultural, Material & Social Axes (`0026`)
- [ ] Extend `timeline_tracks.category` (additive `0026` check/enum update) with `social_gender_norms`, `myths_literature_art`, `food_agriculture_ecology`, and `economic_tensions`, plus optional `social_norms` / `material_culture` (`jsonb`) on `place_snapshots`.
- [ ] Extend `external_tradition_parallels.tradition_source` for `ancient_near_eastern_myth`, `arabian_folklore`, `greco_roman`, and `poetry_adab`.
- [ ] Seed the 4 new tracks + initial cited pre-Hijri/classical milestones and add matching toggleable Context Layers to `ContextLayers.tsx`.
