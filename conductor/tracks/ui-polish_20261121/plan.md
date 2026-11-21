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
