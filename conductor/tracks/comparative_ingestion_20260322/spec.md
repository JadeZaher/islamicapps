# Spec: Automated Cross-Cultural Parallel Ingestion Pipeline

**Track ID:** `comparative_ingestion_20260322`
**Track Type:** Feature
**Date:** 2026-03-22
**Status:** Draft

---

## Overview

This feature adds an automated seeding pipeline for cross-cultural parallel data. The pipeline uses external AI/search APIs to surface candidate parallels between hadith and Jewish, Christian, and Zoroastrian source texts, stages them in a flat JSON file, routes them through a human review UI, and only writes approved candidates into the Neo4j graph. No candidate ever reaches the production graph without explicit human approval.

---

## Background

The `CrossCulturalParallel` node type and all required relationships already exist in Neo4j. The `comparative-actions.ts` server actions already provide `createCrossParallel`, `createSourceText`, and related mutations. What is missing is the data: the graph currently has no cross-cultural parallel nodes at scale. Manually curating hundreds of parallels is impractical. This pipeline automates the discovery step while keeping humans firmly in the approval loop before any data is committed.

---

## Functional Requirements

### FR-1: Parallel Discovery Script

**Description:** A standalone TypeScript script (`src/scripts/find-parallels.ts`) that reads Hadith nodes from Neo4j and, for each hadith (or a configurable batch), queries an external API to produce candidate parallel records. Candidates are written to `datasets/parallel-candidates.json`.

**Acceptance Criteria:**
- Script reads all Hadith nodes using an existing Neo4j query (`runQuery`).
- Script accepts CLI flags: `--batch-size <n>` (default 10), `--offset <n>` (default 0), `--tradition <JUDAISM|CHRISTIANITY|ZOROASTRIANISM>` (optional filter), `--dry-run` (prints candidates without writing to disk).
- Each candidate in the output JSON conforms to the `ParallelCandidate` interface (see Technical Considerations).
- Script does not write to Neo4j; it writes only to the staging JSON file.
- Script is safe to re-run; it appends to the staging file, not overwrites, unless `--overwrite` flag is passed.
- Script logs progress to stdout: hadith processed, candidates found, errors.
- Rate limiting is handled: a configurable delay between API calls (default 500ms) prevents hitting rate limits.
- A run summary is printed at the end: total hadiths processed, total candidates generated, total errors.

**Priority:** P0 (blocker for everything else)

---

### FR-2: Staging File Schema

**Description:** The staging file `datasets/parallel-candidates.json` is the contract between the discovery script and the review UI / ingestion script.

**Acceptance Criteria:**
- Each entry in the array has the following fields (all required unless marked optional):
  - `id`: UUID (generated at discovery time, stable across re-runs for the same hadith+tradition)
  - `status`: `"PENDING"` | `"APPROVED"` | `"REJECTED"`
  - `hadith_id`: Neo4j `Hadith.id`
  - `hadith_title`: string (denormalized for display)
  - `hadith_text_en`: string (denormalized for review)
  - `suggested_tradition`: `"JUDAISM"` | `"CHRISTIANITY"` | `"ZOROASTRIANISM"`
  - `suggested_parallel_type`: one of the six `ParallelType` enum values
  - `suggested_isra_iliyyat_status`: one of the four `IsraIliyyatStatus` values
  - `suggested_source_text_title`: string
  - `suggested_source_text_canonical_reference`: string (e.g., "Genesis 1:1", "Avesta, Yasna 30.3")
  - `suggested_source_text_en`: string (the parallel passage in English)
  - `suggested_source_text_original`: string (optional — original language text if available)
  - `suggested_confidence_level`: `"HIGH"` | `"MEDIUM"` | `"LOW"`
  - `suggested_scholarly_analysis`: string (LLM-generated rationale)
  - `suggested_motif_tags`: string[] (tag names from existing `MotifTag` categories)
  - `api_source`: string (identifies which API/model produced this candidate)
  - `search_query_used`: string
  - `generated_at`: ISO 8601 timestamp
  - `reviewed_at`: ISO 8601 timestamp (optional — set on accept/reject)
  - `reviewer_notes`: string (optional — set by human reviewer)
  - `override_parallel_type`: `ParallelType` (optional — set by reviewer if editing)
  - `override_isra_iliyyat_status`: `IsraIliyyatStatus` (optional)
  - `override_confidence_level`: `ConfidenceLevel` (optional)
  - `override_scholarly_analysis`: string (optional)

**Priority:** P0

---

### FR-3: Human Review UI

**Description:** A Next.js page at `/admin/comparative/review` that loads the staging JSON and allows a reviewer to accept, edit, or reject each candidate before it is committed to Neo4j.

**Acceptance Criteria:**
- Page displays candidates grouped by status (Pending first, then Approved, then Rejected).
- Each candidate card shows a side-by-side layout: hadith text on the left, candidate source text on the right.
- Each card displays: tradition badge, suggested parallel type, isra'iliyyat status, confidence level, API source, scholarly analysis.
- Reviewer can **Accept** a candidate (sets `status: "APPROVED"`, records `reviewed_at`).
- Reviewer can **Reject** a candidate (sets `status: "REJECTED"`, records `reviewed_at`).
- Reviewer can **Edit** fields before accepting: parallel type, isra'iliyyat status, confidence level, scholarly analysis, source text title, canonical reference, source text English. Edits populate the `override_*` fields.
- Reviewer can add free-text `reviewer_notes`.
- **Batch actions:** Select multiple candidates and approve or reject all selected.
- Filter controls: by tradition, by status, by confidence level.
- Count badges on filter tabs show how many candidates are in each state.
- Accepting or rejecting persists the updated staging file via a Server Action (no direct Neo4j writes).
- The review page does not require a running API key; it works on the static JSON only.

**Priority:** P1

---

### FR-4: Ingestion Script

**Description:** A standalone TypeScript script (`src/scripts/ingest-approved-parallels.ts`) that reads the staging JSON, finds all `APPROVED` candidates, and commits them to Neo4j using the existing `createCrossParallel` and `createSourceText` server action logic (or equivalent direct Cypher).

**Acceptance Criteria:**
- Script reads `datasets/parallel-candidates.json`.
- Script processes only candidates with `status: "APPROVED"`.
- For each approved candidate:
  - If a `SourceText` with the same `canonical_reference` already exists, reuse it (MERGE by `canonical_reference`).
  - If the `ReligiousTradition` node exists (MERGE by `name`), reuse it.
  - Create a `CrossCulturalParallel` node using override fields if present, falling back to suggested fields.
  - Link the parallel: `(Hadith)-[:HAS_PARALLEL]->(CrossCulturalParallel)-[:PARALLELS]->(SourceText)-[:BELONGS_TO]->(ReligiousTradition)`.
  - Link `(CrossCulturalParallel)-[:FROM_TRADITION]->(ReligiousTradition)`.
  - For each motif tag name in `suggested_motif_tags`, MERGE a `MotifTag` node and link `(CrossCulturalParallel)-[:TAGGED_WITH]->(MotifTag)`.
- Script is **idempotent**: re-running with the same approved candidates does not create duplicate nodes. Use MERGE on unique fields.
- After committing, marks each candidate `status: "COMMITTED"` in the staging file and sets `committed_at` timestamp.
- Prints a run summary: total approved, total committed, total skipped (already committed), total errors.
- Script accepts `--dry-run` flag to print what would be committed without writing to Neo4j.

**Priority:** P1

---

### FR-5: npm Script Registration

**Description:** New scripts are registered in `package.json` so they can be run consistently.

**Acceptance Criteria:**
- `"db:find-parallels": "tsx src/scripts/find-parallels.ts"` added to scripts.
- `"db:ingest-parallels": "tsx src/scripts/ingest-approved-parallels.ts"` added to scripts.

**Priority:** P1

---

## Non-Functional Requirements

### NFR-1: Safety — No Auto-Commit to Neo4j

All AI-generated candidates must pass through the human review step before touching the graph. The discovery script writes only to the JSON staging file. The review UI writes only to the staging file. Only `ingest-approved-parallels.ts`, run explicitly by a developer, writes to Neo4j.

### NFR-2: Idempotency

Both scripts must be safe to re-run. Use MERGE (not CREATE) for SourceText and ReligiousTradition nodes. Track committed candidates by status field.

### NFR-3: Rate Limit Compliance

The discovery script must respect API rate limits. Configurable inter-call delay (default 500ms). Errors from rate limiting are caught, logged, and the script continues with the next hadith.

### NFR-4: TypeScript Strict Mode

All new TypeScript files must compile under strict mode. No `any` except where interfacing with Neo4j driver result types (consistent with the rest of the codebase).

### NFR-5: Parameterized Queries

All Cypher in the ingestion script must use parameterized inputs, never string interpolation with dynamic values.

---

## User Stories

### Story 1: Batch Discovery Run

As a data contributor, I want to run `npm run db:find-parallels -- --batch-size 20 --offset 0` so that I can generate the first 20 hadith candidates without processing the entire corpus at once and hitting API limits.

**Given** the Neo4j database has Hadith nodes and a valid OpenAI API key is set in `.env.local`,
**When** I run the discovery script with `--batch-size 20`,
**Then** 20 hadiths are processed, candidates are appended to `datasets/parallel-candidates.json`, and the script prints a summary with the count of candidates generated.

---

### Story 2: Reviewing Candidates

As a reviewer, I want to open `/admin/comparative/review` and see a list of PENDING candidates sorted by tradition so I can quickly triage AI-generated suggestions.

**Given** `datasets/parallel-candidates.json` contains at least one PENDING candidate,
**When** I navigate to `/admin/comparative/review`,
**Then** I see all PENDING candidates displayed with the hadith text and source text side by side, and I can accept, reject, or edit each one.

---

### Story 3: Editing Before Accepting

As a reviewer, I notice the AI correctly identified the parallel but misclassified the parallel type. I want to correct it before accepting.

**Given** a PENDING candidate with `suggested_parallel_type: "CULTURAL_BLEED"` that I believe should be `"SHARED_SOURCE"`,
**When** I open the edit form on that card and change the parallel type, then click Accept,
**Then** the candidate's `override_parallel_type` is set to `"SHARED_SOURCE"`, `status` is set to `"APPROVED"`, and the change is persisted to the staging JSON.

---

### Story 4: Committing Approved Candidates

As a developer, I want to run `npm run db:ingest-parallels` after a review session to commit all approved candidates to Neo4j.

**Given** the staging JSON has 15 candidates with `status: "APPROVED"`,
**When** I run the ingestion script,
**Then** 15 CrossCulturalParallel nodes are created in Neo4j, linked to their hadiths and source texts, and each candidate's status in the staging file is updated to `"COMMITTED"`.

---

### Story 5: Idempotent Re-Run

As a developer, I want to re-run the ingestion script safely if I am unsure whether the previous run completed.

**Given** some candidates are already `"COMMITTED"` in the staging file,
**When** I re-run `npm run db:ingest-parallels`,
**Then** already-committed candidates are skipped and no duplicate nodes are created in Neo4j.

---

## Scope of Traditions

### Monotheistic & Proto-Monotheistic Traditions (Inclusive)

The pipeline is tradition-agnostic: any faith tradition with a credible scholarly argument for monotheism, henotheism, or a supreme-creator-deity framework may be studied. This follows the scholarly concepts of *Urmonotheismus* (Wilhelm Schmidt's original monotheism thesis), henotheism (one supreme deity above others), and the universal presence of supreme-creator archetypes documented in comparative religion.

Traditions of particular relevance (not exhaustive):

| Cluster | Traditions |
|---|---|
| **Abrahamic / Near Eastern** | Judaism, Christianity, Zoroastrianism, Mandaeism/Sabianism (Quran mentions as "People of the Book"), Manichaeism, Yazidism |
| **Sub-Saharan African** | Akan (Onyame), Yoruba (Olodumare), Igbo (Chukwu), Dinka (Nhialic), Zulu (uNkulunkulu), Dogon |
| **Ancient Egyptian** | Atenism (explicit monotheism under Akhenaten — a documented historical parallel of great scholarly interest) |
| **Central / Eurasian** | Tengrism (Eternal Blue Sky / Tengri — practiced by Turks and Mongols with whom the Islamic world had sustained contact) |
| **South Asian** | Sikhism (Ik Onkar), Brahmo Samaj, certain strands of Advaita Vedanta |
| **Modern Abrahamic derivative** | Baháʼí Faith |
| **Ancient Near East** | Canaanite (El as supreme father), Mesopotamian (Marduk supremacy), Sumerian |
| **Indigenous Americas** | Lakota (Wakan Tanka / Great Spirit), various Native American supreme-creator traditions, Inca (Inti/Viracocha), Maya |
| **Pacific / Oceania** | Māori, Indigenous Australian Dreaming creator figures |

The `ReligiousTradition` node in Neo4j is fully open — any tradition can be created via the admin. The `TraditionBadge` component assigns colors to known traditions and falls back to a deterministic hash-derived color for any unknown tradition name.

---

## API Recommendation

### Recommended Strategy: Option D — Hybrid (LLM + Verified APIs where available)

**Primary:** OpenAI GPT-4o with structured outputs (JSON mode)
**Verification tier 1 (Abrahamic):** Sefaria API (Jewish texts), Bible API (Christian texts)
**Verification tier 2 (all other traditions):** LLM only, with automatic confidence downgrade and explicit scholarly caveat in output

**Rationale:**

The pipeline must be tradition-agnostic because the scope covers dozens of traditions, many of which have no machine-readable corpus API. The LLM (GPT-4o with structured outputs) is the only tool capable of spanning this breadth. Hallucination risk is managed by:

1. **Verification APIs where they exist** — Sefaria for Jewish texts, Bible API for Christian. These are the two traditions with rich, freely accessible digital corpora.
2. **Confidence scoring as a proxy for verification** — any candidate that cannot be API-verified is automatically assigned `"LOW"` or `"MEDIUM"` confidence, making the human review step the trust gate.
3. **Scholarly analysis field** — the LLM is prompted to include its reasoning, allowing a human reviewer to evaluate the quality of the parallel before approving.

**Prompt design — tradition-agnostic, monotheism-focused:**

The GPT-4o system prompt instructs the model to:
- Consider parallels across *any* religious or spiritual tradition where a supreme creator deity or monotheistic framework is documented by scholarship
- Prioritize traditions geographically and culturally proximate to the hadith's transmission region (e.g., for a Kufan hadith: Zoroastrianism and Manichaeism; for a Yemeni narrator chain: South Arabian paganism, Sabianism)
- For each genuine parallel found, return structured JSON with tradition name exactly as it should appear in the database, source text details, parallel type, and scholarly rationale
- Indicate if the parallel is "condemnation of" vs. "bleed from" vs. "shared Abrahamic source" vs. "independent parallel evolution" — matching the `ParallelType` enum

**Verification tiers:**

| Tradition | Verification | Confidence if unverified |
|---|---|---|
| Judaism | Sefaria API | LOW |
| Christianity | scripture.api.bible | LOW |
| Zoroastrianism | LLM only | MEDIUM |
| Mandaeism, Manichaeism | LLM only | MEDIUM |
| African traditional | LLM only | LOW–MEDIUM |
| Tengrism | LLM only | MEDIUM |
| Sikhism | LLM only (Guru Granth Sahib is online but no structured API) | MEDIUM |
| Ancient / Indigenous | LLM only | LOW |

**Implementation detail for the discovery script:**

1. Call GPT-4o with hadith text + a system prompt explaining the scope (any monotheistic/supreme-creator tradition), requesting a JSON array of candidate parallels.
2. For each candidate, check `suggested_tradition` against a `VERIFIABLE_TRADITIONS` constant (`['JUDAISM', 'CHRISTIANITY']`).
3. If verifiable: call the relevant API, fetch authoritative text, upgrade to verified confidence level if successful, downgrade to LOW if not found.
4. If not verifiable: assign confidence tier from a `DEFAULT_CONFIDENCE` map keyed by tradition cluster; add a standard note to `scholarly_analysis` indicating verification was not available via API.
5. Build `ParallelCandidate` objects and append to staging file.

**Required environment variables (add to `.env.local`):**
```
OPENAI_API_KEY=<key>
SEFARIA_API_KEY=<optional — Sefaria has a public read tier>
BIBLE_API_KEY=<key from scripture.api.bible>
```

**Cost estimate:** GPT-4o structured output call per hadith: ~$0.003–0.008 (input + output tokens). For 1000 hadiths: $3–8 total. Acceptable for a research project.

---

## Technical Considerations

### ParallelCandidate TypeScript Interface

```typescript
export interface ParallelCandidate {
  id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'COMMITTED';
  hadith_id: string;
  hadith_title: string;
  hadith_text_en: string;
  suggested_tradition: string; // free-form tradition name matching ReligiousTradition.name in Neo4j
  suggested_parallel_type: ParallelType;
  suggested_isra_iliyyat_status: IsraIliyyatStatus;
  suggested_source_text_title: string;
  suggested_source_text_canonical_reference: string;
  suggested_source_text_en: string;
  suggested_source_text_original?: string;
  suggested_confidence_level: ConfidenceLevel;
  suggested_scholarly_analysis: string;
  suggested_motif_tags: string[];
  api_source: string;
  search_query_used: string;
  generated_at: string;
  reviewed_at?: string;
  reviewer_notes?: string;
  override_parallel_type?: ParallelType;
  override_isra_iliyyat_status?: IsraIliyyatStatus;
  override_confidence_level?: ConfidenceLevel;
  override_scholarly_analysis?: string;
  committed_at?: string;
}
```

### Staging File Location

`datasets/parallel-candidates.json` — tracked in git (gitignored drafts acceptable but reviewed/committed states should be committed to repo for auditability).

### Review UI Persistence

The review UI calls a Server Action that reads the JSON file from disk, mutates the relevant candidate by `id`, and rewrites the file. This is acceptable for a single-user admin tool. If concurrent reviewers become a concern in the future, migrate staging to a SQLite table via Prisma (Prisma is already in dependencies).

### MotifTag Handling

During ingestion, motif tags are MERGE'd by name within the correct category. The LLM is prompted to suggest tag names from the existing controlled vocabulary (`ESCHATOLOGY`, `CREATION`, `PROPHETIC_STORIES`, `LEGAL`, `WISDOM`, `PERSIAN_INFLUENCE`, `COSMOLOGY`). The ingestion script must validate suggested tag names against this enum before writing.

Note: as coverage of African, indigenous, and Central Asian traditions grows, new `MotifTag` categories may be needed (e.g., `ANCESTOR_VENERATION`, `SACRED_KINGSHIP`, `FLOOD_NARRATIVE`, `TRICKSTER_FIGURES`). These can be added via the admin's Motif Tags tab and the enum extended in `comparative-actions.ts`.

### Script File Location

All scripts go in `src/scripts/` per workflow conventions. Shared types for the candidate schema go in `src/scripts/types/parallel-candidate.ts` so both scripts can import them.

---

## Out of Scope

- Automatic commit to Neo4j without human review.
- Real-time streaming of API results to the review UI.
- Authentication for the review UI (the existing admin section is currently ungated; access control is out of scope for this track).
- Multi-user concurrent review (single-reviewer workflow assumed).
- Verified API coverage beyond Judaism and Christianity (no suitable public corpora exist for other traditions at this time).
- LLM fine-tuning or custom embeddings.
- A public-facing "suggest a parallel" interface for non-admin users.

---

## Open Questions

1. **Sefaria rate limits:** The Sefaria public API has no documented rate limit for read requests but does enforce reasonable use. Should we cache Sefaria responses locally (e.g., `datasets/sefaria-cache.json`) to avoid repeat calls on re-runs? Recommended: yes.

2. **Staging file in git:** Should `datasets/parallel-candidates.json` be committed to the repository or gitignored? Committing it provides a full audit trail of what was reviewed and approved. Recommended: commit it; add a note in `.gitignore` only if the file grows beyond a few MB.

3. **GPT-4o model version:** Should the script pin to a specific snapshot (e.g., `gpt-4o-2024-08-06`) for reproducibility, or use the rolling `gpt-4o` alias? Recommended: pin to a snapshot so re-runs produce comparable results.

4. **Review UI file reads:** The review page currently reads the JSON from disk via a Server Action. This works for local/self-hosted deployments but not for Vercel-deployed environments (no writable filesystem). Is Vercel deployment a near-term concern? If yes, the staging layer should be Neo4j `PendingParallel` nodes instead of a flat file.
