# Tech Stack

## Runtime & Framework

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | 16.0.10 |
| Language | TypeScript | ^5 |
| Runtime | Node.js | LTS |
| React | React | 19.2.1 |

## Database

| Layer | Technology | Notes |
|---|---|---|
| Graph DB | Neo4j | neo4j-driver ^6.0.1 |
| ORM (auxiliary) | Prisma | ^7.1.0 (available but Neo4j is primary) |
| DB access pattern | Server Actions | All queries via `src/app/actions/*-actions.ts` |

### Neo4j Node Types
`Narrator`, `Hadith`, `MatnVariation`, `Chain`, `Scholar`, `ScholarVerdict`, `HistoricalEvent`, `Location`, `Commentary`, `Source`, `ReligiousTradition`, `SourceText`, `CrossCulturalParallel`, `MotifTag`

### Key Relationships
`HAS_VARIATION`, `TRANSMITTED_VIA`, `INCLUDES`, `HEARD_FROM`, `GRADES`, `ISSUED`, `CITES_DEFECT`, `INVOLVED_IN`, `BORN_IN`, `DIED_IN`, `RESIDED_IN`, `COMMENTS_ON`, `DISCUSSES`, `HAS_PARALLEL`, `PARALLELS`, `FROM_TRADITION`, `BELONGS_TO`, `TAGGED_WITH`, `TRANSMITTER_OF_TRADITION`, `HEARTLAND_OF`

## UI & Styling

| Layer | Technology |
|---|---|
| CSS | Tailwind CSS 4 |
| Component primitives | Radix UI (@radix-ui/*) |
| UI components | shadcn/ui pattern (src/components/ui/) |
| Icons | Lucide React |
| Graph visualization (structured) | @xyflow/react |
| Graph visualization (force) | react-force-graph-2d |
| Animation | tw-animate-css |

## Scripting & Data

| Tool | Purpose |
|---|---|
| tsx | Run TypeScript scripts directly |
| `npm run db:init` | Initialize Neo4j schema (constraints + indexes) |
| `npm run db:import` | Import hadith datasets from CSV/JSON |
| `npm run db:seed-history` | Seed historical event data |
| `npm run db:find-parallels` | Discover cross-cultural parallels via you.com Research API (batch) |
| `npm run db:ingest-parallels` | Ingest APPROVED candidates from staging JSON into Neo4j |
| Python (datasets/) | Data preprocessing scripts |

## Key Conventions

- **App Router only** — `src/app/` with `page.tsx` (server) + `client.tsx` or `client-page.tsx` (client components)
- **Server Actions** — all DB mutations and queries in `src/app/actions/` with `'use server'` directive
- **No API routes (general rule)** — mutations go through Server Actions, not `/api/` endpoints; exception: long-running AI research calls at `/api/comparative/research`
- **Schema file** — `src/lib/db/schema.ts` for Neo4j constraint/index initialization
- **Neo4j connection** — `src/lib/db/neo4j.ts` exports `runQuery`, `runWrite`, `runTransaction`
- **Component pattern** — reusable UI in `src/components/`, page-specific in `src/app/.../components/`

## Environment Variables

```
# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>

# Comparative parallel discovery pipeline
YOU_API_KEY=<you.com API key>          # Required — https://you.com/platform
OPENAI_API_KEY=sk-...                  # Optional — fallback LLM if you.com unavailable
BIBLE_API_KEY=...                      # Optional — Christian text verification (scripture.api.bible)
# Sefaria has a public read tier — no key needed
```
