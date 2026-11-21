---
type: track-spec
title: UI polish: five disjoint lanes
tags: [ui-polish_20261121, in_progress]
resource: ./metadata.json
---

# UI polish

Research: [../../../.omc/research/pg-refactor/06-ui-audit.md](../../../.omc/research/pg-refactor/06-ui-audit.md) section 8 (lanes, owned
files, tasks), sections 0 to 7 (findings), section 9 (data dependencies).
Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 (closing paragraph), section 9.4 (contracts the
data-dependent fixes code against), section 2.6 (`error.tsx` wording when the
database is unavailable). Apply `C:/Users/atooz/.gemini/UI-UX-guidance.md`.

## Goal

Ship the five lanes of 06-ui-audit section 8. Lane A lands its shared
component API first; lanes B to E then run in parallel.

## Scope

| Lane | Area |
| --- | --- |
| A | Shell, tokens, shared primitives, public hadith and narrator index pages |
| B | Hadith detail |
| C | Narrator detail and timelines |
| D | Admin lists and list controls, `src/lib/pagination.ts` finite-number guard (design 13.3) |
| E | Comparative, public and admin |

Data-dependent fixes (no "Ungraded" badge, no false "Unknown" verdict,
nullable `chainHealthScore`, mention-keyed chain nodes) code against the
section 9.4 contracts and hide what the current data cannot support.

Some lane A components (`ArabicText`, `ConsensusBadge`, `EmptyState`,
`SiteHeader`) already exist in the working tree; re-verify before building.

## Out of scope

Any change to server actions or queries; the section 9.4 contract switch
itself (query-port phase 6).

## Acceptance checks

- Every task in 06-ui-audit section 8 is done or explicitly deferred here.
- No native `confirm()` or `alert()` remains under `src/`.
- `error.tsx`, `loading.tsx` and `not-found.tsx` exist where 06-ui-audit
  section 7 places them.
- Keyboard and aria checks from 06-ui-audit section 4 pass by hand.

## Open owner questions (section 14)

- Q4: lexicon dates hidden on public pages (lane C display).
