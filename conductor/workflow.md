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

- TypeScript strict mode — no `any` unless interfacing with Neo4j driver results
- All Neo4j queries must use parameterized inputs (never string interpolation with user data)
- Server Actions must have `'use server'` directive
- Client components must have `'use client'` directive
- Reuse existing patterns: see `graph-actions.ts` and `comparative-actions.ts` as reference implementations
- Keep page components thin (fetch + pass data); put logic in action files or shared components

## Git & Commits

- **Manual commits only** — developer controls when to commit
- Conductor will NOT auto-commit
- Suggested commit message format: `feat(<area>): <description>` or `fix(<area>): <description>`

## Test Coverage

- No formal coverage target at this stage
- Write tests for: complex graph algorithms, data transformation pipelines, and ingestion logic
- Skip tests for: UI components, simple CRUD actions, routing

## Data Scripts

- All data scripts live in `src/scripts/` (TypeScript, run via `tsx`)
- Dataset preprocessing lives in `datasets/` (Python)
- Run scripts via `npm run` commands defined in `package.json`
- New scripts should follow the pattern in `import-datasets.ts`

## Neo4j Schema Changes

- All schema changes go in `src/lib/db/schema.ts`
- Run `npm run db:init` to apply — safe to re-run (uses `IF NOT EXISTS`)
- Document new node types and relationships in `conductor/tech-stack.md`
