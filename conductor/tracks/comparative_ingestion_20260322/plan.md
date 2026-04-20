# Implementation Plan: Automated Cross-Cultural Parallel Ingestion Pipeline

**Track ID:** `comparative_ingestion_20260322`
**Spec:** `conductor/tracks/comparative_ingestion_20260322/spec.md`

---

## Overview

Three phases. Phase 1 builds the shared type layer and the discovery script. Phase 2 builds the review UI. Phase 3 builds the ingestion script and wires everything together. Each phase is independently deployable — the next phase can begin as soon as the previous phase is verified.

No test suite is required per workflow conventions. Verification steps are manual CLI runs and browser checks at the end of each phase.

---

## Phase 1: Discovery Script and Staging Schema

**Goal:** A runnable `npm run db:find-parallels` command that reads hadiths from Neo4j, calls the OpenAI API, optionally verifies against Sefaria and Bible APIs, and writes structured candidates to `datasets/parallel-candidates.json`.

---

### Tasks

- [ ] Task: Create shared candidate type file

  Create `src/scripts/types/parallel-candidate.ts` with the full `ParallelCandidate` interface as specified in spec FR-2 and the Technical Considerations section. Export `ParallelType`, `IsraIliyyatStatus`, and `ConfidenceLevel` re-exports so scripts can import from one place. Include a `loadCandidates(filePath: string): ParallelCandidate[]` utility and a `saveCandidates(filePath: string, candidates: ParallelCandidate[]): void` utility that reads/writes the JSON file atomically (write to a temp file then rename). This is the contract used by all three scripts.

- [ ] Task: Add environment variable types and validation helper

  Create `src/scripts/lib/env.ts`. Export a `getRequiredEnv(key: string): string` function that throws a descriptive error if the variable is not set. Call this at script startup for `OPENAI_API_KEY`. Make `SEFARIA_API_KEY` and `BIBLE_API_KEY` optional — log a warning if absent but do not block execution (verification steps are skipped for the relevant tradition when the key is missing).

- [ ] Task: Implement the OpenAI structured-output prompt

  Create `src/scripts/lib/llm-client.ts`. Export `findParallelCandidates(hadith: HadithRecord): Promise<LLMCandidateResult[]>` where `HadithRecord` holds `{ id, title, text_english, primary_topic }` and `LLMCandidateResult` is the raw LLM response shape before verification. Use the `openai` npm package (`npm install openai`). Use `response_format: { type: "json_schema", json_schema: { ... } }` (structured outputs) so the model is constrained to return valid candidate JSON.

  **Prompt design (tradition-agnostic, monotheism-focused):** The system prompt instructs GPT-4o to consider parallels across *any* faith tradition where a supreme creator deity or monotheistic framework is documented by scholarship — including but not limited to Abrahamic traditions, African traditional religions (Akan, Yoruba, Igbo, Dinka, Zulu), Tengrism, Atenism, Sikhism, Mandaeism, Manichaeism, and indigenous traditions worldwide. The model is told to prioritize traditions geographically or culturally proximate to the hadith's probable transmission region when known. Each candidate must include `suggested_tradition` as a free-form string matching how the tradition would be named in a scholarly database.

  Use the `VERIFIABLE_TRADITIONS` constant `['JUDAISM', 'CHRISTIANITY']` to determine which candidates get API verification. For all other traditions, the confidence is set by a `DEFAULT_CONFIDENCE_BY_CLUSTER` map. Pin the model to `gpt-4o-2024-08-06`.

- [ ] Task: Implement Sefaria verification helper

  Create `src/scripts/lib/sefaria-client.ts`. Export `verifySefariaPasage(canonicalRef: string): Promise<{ found: boolean; text_en?: string }>`. Use the public Sefaria REST API: `GET https://www.sefaria.org/api/texts/<ref>`. Parse the `text` array from the response into a flat English string. Implement a simple file-based cache at `datasets/sefaria-cache.json` (read on startup, write after each new lookup, keyed by canonical reference). Handle 404 (not found) and network errors gracefully — return `{ found: false }` without throwing.

- [ ] Task: Implement Bible API verification helper

  Create `src/scripts/lib/bible-client.ts`. Export `verifyBiblePassage(canonicalRef: string): Promise<{ found: boolean; text_en?: string }>`. Use `scripture.api.bible` (API key from `BIBLE_API_KEY`). Parse the passage text from the response. Same file-based cache pattern at `datasets/bible-cache.json`. Handle missing key gracefully — return `{ found: false }` with a logged warning.

- [ ] Task: Build the main discovery script

  Create `src/scripts/find-parallels.ts`. Follow the structure of `import-datasets.ts` as a reference. Logic:

  1. Parse CLI args: `--batch-size` (default 10), `--offset` (default 0), `--tradition` (optional), `--dry-run`, `--overwrite`, `--delay-ms` (default 500).
  2. Call `getRequiredEnv('OPENAI_API_KEY')`.
  3. Query Neo4j for Hadith nodes: `MATCH (h:Hadith) RETURN h.id, h.title, h.text_english, h.primary_topic ORDER BY h.created_at SKIP $offset LIMIT $batchSize`.
  4. For each hadith, call `findParallelCandidates(hadith)`. Catch errors per-hadith, log, and continue.
  5. For each LLM candidate result, optionally verify via `verifySefariaPasage` or `verifyBiblePassage` based on tradition. Adjust `suggested_confidence_level` down to `"LOW"` if verification fails.
  6. Build `ParallelCandidate` objects with `status: "PENDING"`, new UUID for `id`, current timestamp for `generated_at`.
  7. Unless `--dry-run`, load existing staging file (or empty array), append new candidates (skip if a candidate with same `hadith_id` + `suggested_tradition` + `suggested_source_text_canonical_reference` already exists), save.
  8. Sleep `--delay-ms` between API calls.
  9. Print summary.

- [ ] Task: Register npm script

  Add `"db:find-parallels": "tsx src/scripts/find-parallels.ts"` to `package.json` scripts.

- [ ] Verification: Run the discovery script on a 3-hadith batch [checkpoint]

  ```bash
  # Ensure OPENAI_API_KEY is set in .env.local (dotenv loaded via tsx)
  npm run db:find-parallels -- --batch-size 3 --dry-run
  # Verify: JSON candidates printed to stdout, no file written

  npm run db:find-parallels -- --batch-size 3
  # Verify: datasets/parallel-candidates.json created with 3+ candidate entries
  # Verify: each entry has id, status="PENDING", hadith_id, suggested_tradition, etc.
  # Verify: no Neo4j nodes were created (query: MATCH (p:CrossCulturalParallel) RETURN count(p))
  ```

---

## Phase 2: Human Review UI

**Goal:** A working `/admin/comparative/review` page that loads the staging JSON and allows accept / edit / reject operations persisted back to the file via Server Actions.

---

### Tasks

- [ ] Task: Add review Server Actions

  Create `src/app/actions/parallel-review-actions.ts` with `'use server'` directive. Implement:

  - `getPendingCandidates(): Promise<ParallelCandidate[]>` — reads `datasets/parallel-candidates.json`, returns all candidates sorted: PENDING first, APPROVED second, REJECTED last, COMMITTED excluded from display.
  - `approveCandidate(id: string, overrides?: CandidateOverrides): Promise<void>` — finds candidate by `id`, sets `status: "APPROVED"`, `reviewed_at: new Date().toISOString()`, applies any overrides to `override_*` fields, saves file.
  - `rejectCandidate(id: string, notes?: string): Promise<void>` — sets `status: "REJECTED"`, `reviewed_at`, `reviewer_notes`, saves file.
  - `batchApprove(ids: string[]): Promise<void>` — applies approve logic to each id.
  - `batchReject(ids: string[]): Promise<void>` — applies reject logic to each id.

  The file path for the JSON is resolved relative to `process.cwd()` as `path.join(process.cwd(), 'datasets', 'parallel-candidates.json')`. This works for local development. Include a guard that throws if the file does not exist, with a clear error message.

- [ ] Task: Build the review page server component

  Create `src/app/admin/comparative/review/page.tsx`. Import `getPendingCandidates` and pass the result to the client component. The server component is thin — fetch and pass.

- [ ] Task: Build the CandidateCard client component

  Create `src/app/admin/comparative/review/components/CandidateCard.tsx` with `'use client'`. Props: `candidate: ParallelCandidate`, `onApprove`, `onReject`, `onEdit`. Layout: two-column card. Left column: hadith title + full English text. Right column: tradition badge (colored by tradition — emerald for Judaism, blue for Christianity, orange for Zoroastrianism), source text title, canonical reference, English passage, parallel type badge, isra'iliyyat status badge, confidence badge, scholarly analysis, API source label. Actions row: Accept button, Reject button, Edit button. Edit triggers an inline form (not a modal) that shows editable fields with current suggested values pre-populated.

- [ ] Task: Build the inline edit form

  Create `src/app/admin/comparative/review/components/EditForm.tsx` with `'use client'`. Fields: parallel type (select from enum), isra'iliyyat status (select), confidence level (select), scholarly analysis (textarea), reviewer notes (textarea). On submit, calls `onApprove` with the override values. Cancel button restores the card to read-only view.

- [ ] Task: Build the review page client shell

  Create `src/app/admin/comparative/review/client.tsx` with `'use client'`. Renders:

  - Header with title and count badges per status.
  - Filter bar: tradition selector (all / Judaism / Christianity / Zoroastrianism), status filter (all / pending / approved / rejected), confidence filter.
  - Batch action bar: appears when one or more candidates are selected via checkboxes (Approve Selected, Reject Selected buttons).
  - List of `CandidateCard` components for filtered candidates.
  - Uses `useTransition` and `startTransition` around server action calls to show loading state.
  - After each action, calls `router.refresh()` to reload data from the server component.

- [ ] Task: Add "Parallel Review" link to admin layout

  Edit `src/app/admin/layout.tsx` to add a nav item `{ href: '/admin/comparative/review', label: 'Parallel Review', icon: Search }` to the `navItems` array. Add `Search` to the Lucide imports.

- [ ] Verification: Manual review flow [checkpoint]

  ```
  1. Navigate to /admin/comparative/review
  2. Verify: PENDING candidates appear with side-by-side layout
  3. Click Accept on one candidate — verify status badge changes to APPROVED
  4. Click Reject on one candidate — verify it moves to REJECTED section
  5. Click Edit on a third candidate, change parallel type, click Accept
     — verify override_parallel_type is set in the JSON file
  6. Select 2 candidates via checkboxes, click "Approve Selected"
     — verify both are now APPROVED
  7. Check datasets/parallel-candidates.json on disk to confirm mutations persisted
  ```

---

## Phase 3: Ingestion Script

**Goal:** A runnable `npm run db:ingest-parallels` command that reads APPROVED candidates from the staging JSON and commits them to Neo4j idempotently.

---

### Tasks

- [ ] Task: Implement SourceText MERGE helper

  In `src/scripts/ingest-approved-parallels.ts` (or a shared lib file), implement `mergeSourceText(candidate: ParallelCandidate): Promise<string>` that runs:

  ```cypher
  MERGE (s:SourceText {canonical_reference: $canonical_reference})
  ON CREATE SET
    s.id = $id,
    s.title = $title,
    s.tradition_name = $tradition_name,
    s.created_at = datetime()
  ON MATCH SET
    s.title = $title
  RETURN s.id
  ```

  Uses `canonical_reference` as the merge key. Returns the `id` of the created or matched node.

- [ ] Task: Implement ReligiousTradition MERGE helper

  Implement `mergeTradition(traditionName: string): Promise<string>` that MERGEs on `name`. Returns the tradition `id`.

- [ ] Task: Implement MotifTag MERGE helper

  Implement `mergeMotifTag(tagName: string): Promise<string>` that MERGEs on `name`. Maps tag names to categories using a static lookup object derived from the `MotifCategory` enum. Returns the tag `id`.

- [ ] Task: Implement CrossCulturalParallel MERGE and link

  Implement `commitParallel(candidate: ParallelCandidate, sourceTextId: string, traditionId: string, motifTagIds: string[]): Promise<void>` that:

  1. Determines effective field values (override > suggested).
  2. Runs a MERGE on `(CrossCulturalParallel {hadith_id_ref: $hadith_id, canonical_reference_ref: $canonical_reference})` — a composite uniqueness key stored as properties to enable idempotency without a Neo4j constraint. Alternatively, store the staging `id` on the node: `MERGE (p:CrossCulturalParallel {staging_id: $staging_id})`.
  3. Creates relationships using MERGE: `(Hadith)-[:HAS_PARALLEL]->(p)`, `(p)-[:PARALLELS]->(s)`, `(p)-[:FROM_TRADITION]->(t)`.
  4. For each motif tag, MERGE `(p)-[:TAGGED_WITH]->(m)`.

- [ ] Task: Build the main ingestion script

  Create `src/scripts/ingest-approved-parallels.ts`. Logic:

  1. Parse CLI args: `--dry-run`, `--limit` (process at most N approved candidates in this run).
  2. Load staging file. Filter for `status: "APPROVED"`.
  3. For each approved candidate: call merge helpers, commit parallel, update candidate `status: "COMMITTED"` and `committed_at` in memory.
  4. Unless `--dry-run`, call `saveCandidates` to persist updated statuses.
  5. Print summary: total approved, committed this run, skipped (already committed), errors.

- [ ] Task: Register npm script

  Add `"db:ingest-parallels": "tsx src/scripts/ingest-approved-parallels.ts"` to `package.json` scripts.

- [ ] Verification: End-to-end ingestion test [checkpoint]

  ```bash
  # Ensure at least one candidate has status="APPROVED" in the staging file
  npm run db:ingest-parallels -- --dry-run
  # Verify: prints what would be committed, no Neo4j writes

  npm run db:ingest-parallels
  # Verify: CrossCulturalParallel nodes created in Neo4j:
  #   MATCH (p:CrossCulturalParallel) RETURN count(p)
  # Verify: relationships exist:
  #   MATCH (h:Hadith)-[:HAS_PARALLEL]->(p:CrossCulturalParallel)-[:PARALLELS]->(s:SourceText)
  #   RETURN h.title, p.parallel_type, s.title LIMIT 5
  # Verify: committed candidates have status="COMMITTED" in datasets/parallel-candidates.json

  # Re-run to test idempotency
  npm run db:ingest-parallels
  # Verify: "skipped (already committed)" count equals previous run's committed count
  # Verify: no duplicate CrossCulturalParallel nodes in Neo4j
  ```

---

## Phase 4: Documentation and Environment Setup (Lightweight)

**Goal:** Ensure a new developer can run the pipeline end-to-end using only the README or inline instructions.

---

### Tasks

- [ ] Task: Add environment variable entries to `.env.example` (or document in `conductor/tech-stack.md`)

  Add the following keys with placeholder values and comments:

  ```
  # Parallel discovery pipeline
  OPENAI_API_KEY=sk-...          # Required for find-parallels script
  BIBLE_API_KEY=...              # Optional — Christian text verification (scripture.api.bible)
  # SEFARIA_API_KEY not required — Sefaria has a public read tier
  ```

  Update `conductor/tech-stack.md` Environment Variables table with these three keys.

- [ ] Task: Update `conductor/tech-stack.md` with new node type

  If `PendingParallel` or `staging_id` property is used on `CrossCulturalParallel`, document the schema change. Document the new npm scripts in the scripting table.

- [ ] Verification: Fresh-clone simulation [checkpoint]

  ```
  1. Copy .env.example to .env.local, fill in OPENAI_API_KEY
  2. Run: npm run db:find-parallels -- --batch-size 2 --dry-run
     Verify: script runs, prints candidates, exits cleanly
  3. Confirm no undocumented env var is required
  ```

---

## Dependency Map

```
Phase 1 (Discovery Script)
  └── Provides: datasets/parallel-candidates.json
        └── Phase 2 (Review UI) consumes staging JSON
              └── Phase 3 (Ingestion Script) consumes APPROVED entries
                    └── Phase 4 (Docs) wraps up
```

Phases 1, 2, and 3 can be implemented in sequence. Phase 4 is independent and can be done at any point after Phase 1.

---

## File Creation Summary

| File | Phase | Type |
|---|---|---|
| `src/scripts/types/parallel-candidate.ts` | 1 | Shared types |
| `src/scripts/lib/env.ts` | 1 | Utility |
| `src/scripts/lib/llm-client.ts` | 1 | API client |
| `src/scripts/lib/sefaria-client.ts` | 1 | API client |
| `src/scripts/lib/bible-client.ts` | 1 | API client |
| `src/scripts/find-parallels.ts` | 1 | Script |
| `src/app/actions/parallel-review-actions.ts` | 2 | Server Actions |
| `src/app/admin/comparative/review/page.tsx` | 2 | Server component |
| `src/app/admin/comparative/review/client.tsx` | 2 | Client component |
| `src/app/admin/comparative/review/components/CandidateCard.tsx` | 2 | Client component |
| `src/app/admin/comparative/review/components/EditForm.tsx` | 2 | Client component |
| `src/scripts/ingest-approved-parallels.ts` | 3 | Script |
| `datasets/parallel-candidates.json` | 1 (generated) | Data |
| `datasets/sefaria-cache.json` | 1 (generated) | Cache |
| `datasets/bible-cache.json` | 1 (generated) | Cache |

---

## Key Decisions Recorded

- **Staging layer:** Flat JSON file (not SQLite/Prisma) to keep the pipeline simple and avoid schema migrations. Revisit if concurrent reviewers or Vercel deployment becomes a requirement.
- **API strategy:** Option D (hybrid LLM + verification APIs) per spec recommendation.
- **Idempotency key for CrossCulturalParallel:** Use `staging_id` property (the UUID from the staging file) as the MERGE key. This is simpler than a composite key and ensures one Neo4j node per staging candidate.
- **Override precedence:** Reviewer override fields always win over suggested fields at ingestion time. If no override is set, the suggested field value is used.
- **MotifTag category mapping:** Defined as a static constant in the ingestion script to avoid a runtime DB lookup per tag. Must be kept in sync with the `MotifCategory` enum in `comparative-actions.ts`.
