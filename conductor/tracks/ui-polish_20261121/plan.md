---
type: implementation-plan
title: UI polish: five disjoint lanes plan
tags: [ui-polish_20261121, in_progress]
resource: ./spec.md
---

# Implementation plan: UI polish: five disjoint lanes

Track: `ui-polish_20261121`. Spec: [./spec.md](./spec.md). Design steps: alongside 4 to 6.

## Phase 1 — Lane A (shared API first)

- [ ] Shared components with the agreed signatures (06-ui-audit section 8).
- [ ] Tokens, `className="dark"`, metadata, home page as search plus browse.
- [ ] Public `hadith/page.tsx` and `narrator/page.tsx` index pages.

Done when: lanes B to E can import every shared component.

## Phase 2 — Lanes B to E in parallel

- [ ] Lane B: hadith detail tasks.
- [ ] Lane C: narrator detail and timeline tasks.
- [ ] Lane D: admin list tasks, pagination guard, confirm replacement.
- [ ] Lane E: comparative tasks.

Done when: each lane's task list in 06-ui-audit section 8 is checked off.

## Phase 3 — Join

- [ ] Apply the `package.json` removal of `react-force-graph-2d` at the join.
- [ ] One build, lint and type-check sweep across all lanes.
- [ ] Hand-check keyboard, loading, empty and error states on each lane's pages.

Done when: the spec's acceptance checks pass.

## Log

- 2026-11-21, browser review (interface lane). Walked home, indexes, hadith and narrator detail,
  comparative, 404 and route states at 1440 and 390 px against live Neo4j, then again after the data lane
  switched the indexes to the (empty) Postgres development database. Fixed: Tailwind source scan crashing
  dev on the OS-locked dataset file; one page background; Arabic joining and justification rules; hadith
  page rebuilt as one reading column; isnad rail with unidentified mentions unlinked; computed score and
  inferred marfūʿ no longer rendered; per-tradition assessments rendered; narrator page de-carded, verdict
  attributed, empty tabaqah pill removed; shared `RouteError` / `RouteMessage`; neutral Islamic tradition
  badges; comparative phone layout and page-size "total". Rationale: `src/components/AGENTS.md`.
  Not checked live: admin lists (now behind curator sign-in). Phase 3 hand-check stays open for admin.
