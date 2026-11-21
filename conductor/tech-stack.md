---
type: tech-stack
title: Tech stack
---

# Tech Stack

The data layer is defined by
[`docs/architecture/data-architecture.md`](../docs/architecture/data-architecture.md)
(section 1 for the decision, section 3 for layout and rules). This file is the
summary; the design doc wins on any difference.

## Runtime & Framework

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router, standalone output) | 16.0.10 |
| Language | TypeScript | ^5 |
| Runtime | Node.js | LTS |
| React | React | 19.2.1 |
| Input validation | zod | ^4 |

## Database

| Layer | Technology | Notes |
|---|---|---|
| Store | PostgreSQL 18 on Railway | Railway template image `ghcr.io/railwayapp-templates/postgres-ssl:18`, one small always-on instance tuned for low memory (design 2.4). Lives in Railway project `hadith-ontology`; extensions `vector`, `pg_trgm`, `unaccent` enabled |
| ORM | Drizzle ORM `drizzle-orm` 0.45.4 | The stable line, not the 1.0 release candidate |
| Migrations | `drizzle-kit` 0.31.11 (dev dependency only) | Generated into `drizzle/core`, checked in, applied by a Railway pre-deploy command (design 2.6). Expand-only |
| Driver | postgres.js (`postgres`) | One lazy client per process, `max: 5` (design 3.3) |
| Vectors | pgvector | Own table `hadith_embeddings`, added at step 11; exact scan with a bit pre-filter, no approximate index at launch (design 7.4) |
| Text search | `pg_trgm` + `unaccent`; `tsvector` | Arabic: trigram on text normalized by the project's Arabic `norm()`. English: full-text. Names and titles: trigram (design 7) |
| Roles | `schema_owner`, `app_rw` | `src/db/ops/roles.sql`; the app has no `DELETE` anywhere (design 2.9) |

**Removed:** Neo4j and `neo4j-driver` (until the step 10 sweep, the old code
still exists under `src/lib/db/` and `src/scripts/`), and Prisma, which this
file used to list but which was never installed.

## Where SQL lives

| Path | Holds |
|---|---|
| `src/db/schema/core/*.ts` | Drizzle table, enum and view declarations |
| `drizzle/core/` | Generated migrations plus hand-written SQL (extensions, views, functions) |
| `src/db/queries/*.ts` | Every app query. Server actions, pages and components never contain SQL |
| `src/db/load/*.ts` | Bundle loader: COPY into staging, merge, verify |
| `src/db/ops/*.sql` | Roles, Railway tuning, heavy index builds (run by an operator) |
| `src/db/client.ts` | The single server-only client |

## UI & Styling

| Layer | Technology |
|---|---|
| CSS | Tailwind CSS 4 |
| Component primitives | Radix UI (@radix-ui/*) |
| UI components | shadcn/ui pattern (src/components/ui/) |
| Icons | Lucide React |
| Graph visualization (structured) | @xyflow/react |
| Animation | tw-animate-css |

`react-force-graph-2d` is being removed with the dead `IsnadGraph` UI (design 13.1).

## Scripting & Data

| Tool | Purpose |
|---|---|
| tsx | Run TypeScript operator scripts; type-checked by `tsconfig.scripts.json`, not by `next build` |
| `src/scripts/db/` | Operator entry points: load, verify, audit, seeds, curation export (design 3.1) |
| Python (`datasets/`) | Dataset pipeline and the bundle exporter; `export_postgres.py` projects a validated bundle to COPY CSVs (design 4.4) |

## Key Conventions

- **App Router only** — `src/app/` with `page.tsx` (server) + `client.tsx` or `client-page.tsx` (client components)
- **Layering** — files under `src/app/**` may not import `drizzle-orm`, `postgres`, `@/db/client` or `@/db/schema` (ESLint rule, design 3.2 rule 1). Server components call `src/db/queries` directly; client components call thin actions in `src/app/actions/read/` or `src/app/actions/curation/`
- **Writes need a named curator** — `requireCurator()` is the first line of every curation action, and every write records a `curation_audit` row (design 10)
- **Public pages read `public_*` views** (design 11.3)
- **Pages that read the database** declare `export const dynamic = 'force-dynamic'`, so `next build` never needs a database
- **Component pattern** — reusable UI in `src/components/`, page-specific in `src/app/.../components/`

## Environment Variables

Names only; values live in Railway and the local `.env.local` (design 2.2).

```
DATABASE_URL=            # app: app_rw role on the private Railway host, never the superuser URL
MIGRATOR_DATABASE_URL=   # schema_owner role; read only by migrate.mjs in the pre-deploy command
TEST_DATABASE_URL=       # disposable test database (name ends in _test)
DATABASE_PUBLIC_URL=     # Postgres service; exists only while Public Access is on for a load
CURATOR_PASSPHRASES=     # {name: scrypt hash}
ADMIN_SESSION_SECRET=    # HMAC key for the curator cookie

# Comparative parallel discovery pipeline
YOU_API_KEY=             # research route; curator-only
OPENAI_API_KEY=          # optional fallback LLM
BIBLE_API_KEY=           # optional (scripture.api.bible); Sefaria needs no key
```

The nine Neo4j variables stay on the app until the owner approves their
removal at step 9.
