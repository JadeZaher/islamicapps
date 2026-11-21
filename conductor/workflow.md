---
type: workflow
title: Workflow
---

# Workflow

## Development Methodology

**Iterative feature delivery.** Each track delivers a working, self-contained feature. No formal TDD requirement — write code that works correctly, add targeted tests only when logic is complex enough to warrant it.

## Track Structure

```
conductor/tracks/<track_id>/
├── spec.md        # Requirements and acceptance criteria
├── plan.md        # Phased implementation breakdown
└── metadata.json  # Track status and metadata
```

## Implementation Cycle

```
Plan → Implement → Verify → (Fix if needed) → Done
```

1. **Plan**: Read `spec.md` and `plan.md`. Understand scope before touching code.
2. **Implement**: Work through plan phases sequentially. Mark tasks complete as you go.
3. **Verify**: Check that acceptance criteria in `spec.md` are met.
4. **Fix**: If verification fails, address before marking phase complete.

## Code Quality Standards

- TypeScript strict mode — no `any`
- SQL lives only in `src/db/queries/` and `src/db/load/`; user input reaches it only as bound parameters (Drizzle builders or postgres.js tagged templates), never by string interpolation. Rules: `docs/architecture/data-architecture.md` section 3.2
- Server Actions must have `'use server'` directive; they validate input with zod and call one query function
- Client components must have `'use client'` directive
- Keep page components thin (fetch + pass data); put data logic in `src/db/queries/` and UI logic in shared components

## Git & Commits

- **Manual commits only** — developer controls when to commit
- Conductor will NOT auto-commit
- Suggested commit message format: `feat(<area>): <description>` or `fix(<area>): <description>`

## Test Coverage

- No formal coverage target at this stage
- Write tests for: complex graph algorithms, data transformation pipelines, and ingestion logic
- Skip tests for: UI components, simple CRUD actions, routing

## Data Scripts

- All data scripts live in `src/scripts/` (TypeScript, run via `tsx`); database operator entry points live in `src/scripts/db/`
- Dataset preprocessing lives in `datasets/` (Python)
- Run scripts via `npm run` commands defined in `package.json`

## Database Schema Changes

- Edit the Drizzle schema in `src/db/schema/core/`, then generate a migration into `drizzle/core` with `drizzle-kit`; check it in
- Migrations are expand-only: a rename or drop ships one release after no deployed code reads the old shape (design section 2.6)
- Large index builds are not migrations; they go in `src/db/ops/indexes-heavy.sql`
- Migrations are applied by the Railway pre-deploy command; record schema decisions in `docs/architecture/data-architecture.md`
