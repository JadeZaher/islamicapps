/**
 * entity-resolution.ts — Tiered narrator entity resolution (Workstream D)
 * =========================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Phase 2 (FR-2.1..2.4, G-5, NFR-3)
 *
 * GLOBAL INVARIANTS:
 *   1. Identity ≠ Assessment — never write a grade.
 *   2. No auto-writes of :RESOLVES_TO or :SAME_AS without human approval.
 *   3. Stable business keys — MERGE narrators on RAWI:scholar_indx.
 *   4. Every edge: confidence ∈ [0,1], extraction_method ∈ ErTier.
 *   5. Tradition canonicalization — use "Imami"/"Zaydi" never "Shia Imami"/"Shia Zaydi".
 *   6. No-GIGO: unmeasured strata get quarantined=true.
 *
 * Tier 1 — chain_indx join (FR-2.1): deterministic, confidence=1.0.
 * Tier 2 — exact/blocked lexicon (FR-2.2): uses shared _norm; conf ≥ 0.9 exact.
 * Tier 3 — ambiguous collision core (FR-2.3, G-5): emit to staging only.
 *
 * NOTE: UnifiedRow and RawiRecord will be imported from io.ts once
 * Workstream C publishes them. Until then, minimal stubs are defined inline.
 * TODO(WorkstreamC): replace the stub interfaces below with:
 *   import type { UnifiedRow, RawiRecord } from './io';
 */

import fs from 'fs';
import path from 'path';
import { norm } from '../../../lib/attribution/classify-attribution';

// ─── Stub interfaces (TODO: replace with imports from ./io once Workstream C lands) ─

/**
 * One row from all_hadiths_unified.csv as parsed by io.ts (Workstream C).
 * Stub — keep in sync with whatever io.ts publishes.
 */
export interface UnifiedRow {
  dataset_row_id?: string | number;
  source?: string;
  hadith_no?: string;
  tradition?: string;
  text_ar?: string;
  sanad?: string;
  /** Serialized integer array, e.g. "[1,2,3]" or "1,2,3" */
  chain_indx?: string;
  [key: string]: unknown;
}

/**
 * One row from all_rawis.csv as loaded by io.ts (Workstream C).
 * Stub — keep in sync with whatever io.ts publishes.
 */
export interface RawiRecord {
  scholar_indx: number;
  name: string;
  grade?: string;
  death_date_hijri?: number | null;
  death_date_gregorian?: number | null;
  birth_date_hijri?: number | null;
  birth_date_gregorian?: number | null;
  /** Raw "students_inds" column, comma-separated integers */
  students_inds?: string;
  /** Raw "teachers_inds" column, comma-separated integers */
  teachers_inds?: string;
  [key: string]: unknown;
}

// ─── Public types ─────────────────────────────────────────────────────────────

/**
 * Extraction method tier. Corresponds to spec FR-2.1..2.4 and the per-edge
 * extraction_method property required by FR-1.4.
 */
export type ErTier =
  | 'chain_indx_join'  // Tier 1 — deterministic join on numeric chain_indx IDs
  | 'lexicon_exact'    // Tier 2 — exact match on normalized name
  | 'lexicon_blocked'  // Tier 2 — blocked/normalized-key candidate match
  | 'rerank'           // Tier 3 — human-approved from staging (written by ingest-er-approved.ts)
  | 'regex_sanad';     // Tier 2 fallback — classify_attribution terminus recorded

/** A narrator resolved to a controlled-vocabulary scholar_indx. */
export interface ResolvedNarrator {
  scholar_indx: number;
  position: number;
  confidence: number;
  /** The extraction tier that produced this resolution. */
  extraction_method: ErTier;
  /**
   * When true this resolution is from an unmeasured stratum (Imami-gap,
   * transliterated, cross-tradition) and must be excluded from downstream
   * analytics unless the caller opts in with an audit flag (NFR-3).
   */
  quarantined?: boolean;
}

/** An unresolved name occurring in an isnad; becomes a :NameMention node. */
export interface NameMentionDraft {
  surface_form: string;
  normalized_form: string;
  position: number;
}

/**
 * A ranked candidate emitted to er-staging.jsonl when a name is ambiguous.
 * Humans review these and mark approved: true; ingest-er-approved.ts commits
 * only the approved rows as :RESOLVES_TO edges.
 */
export interface StagingRecord {
  /** Unix epoch ms — for deduplication. */
  staged_at: number;
  surface_form: string;
  normalized_form: string;
  /** Row key for back-reference. */
  source_row_id: string;
  tradition: string;
  position: number;
  /** Ranked candidates (best first). */
  candidates: Array<{
    scholar_indx: number;
    name: string;
    grade?: string;
    death_date_hijri?: number | null;
    score: number;
    features: Record<string, unknown>;
  }>;
  /** HITL fields — filled by human reviewer, not by this code. */
  approved?: boolean;
  approved_scholar_indx?: number;
  reviewed_by?: string;
  reviewed_at?: string;
  /** Quarantined if from an unmeasured stratum (NFR-3). */
  quarantined?: boolean;
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

/**
 * Parse chain_indx from a CSV field that may be:
 *   - a JSON array string: "[1,2,3]"
 *   - a comma-separated string: "1,2,3"
 *   - empty/null
 */
function parseChainIndx(raw: string | undefined): number[] {
  if (!raw) return [];
  const trimmed = raw.trim();
  if (!trimmed || trimmed === '[]' || trimmed === 'nan') return [];
  // Try JSON array first
  if (trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) return parsed.map(Number).filter(n => !isNaN(n) && n > 0);
    } catch {
      // fall through
    }
  }
  // Comma-separated fallback
  return trimmed
    .replace(/[\[\]]/g, '')
    .split(',')
    .map(s => parseInt(s.trim(), 10))
    .filter(n => !isNaN(n) && n > 0);
}

/**
 * Extract individual narrator name tokens from a sanad string.
 * Splits on transmission verbs (حدثنا / عن / أخبرنا / رويت / قال / عن).
 * Returns non-empty, whitespace-trimmed tokens.
 */
function splitSanadNames(sanad: string): string[] {
  const normalized = norm(sanad);
  // Transmission-verb delimiters common to Sunni/Imami/Zaydi/Ibadi isnads
  const parts = normalized.split(
    /حدثنا|حدثني|اخبرنا|اخبرني|انبانا|عن|قال|روي|روينا|رويت/
  );
  return parts.map((p: string) => p.trim()).filter((p: string) => p.length > 2);
}

/**
 * Build a normalized lookup key from a rawi name for blocked matching.
 * Strips kunya prefixes (ابن/ابو/ابي/بنت) and uses only the core ism.
 * This is the "blocked key" for Tier-2 candidate generation.
 */
function blockedKey(name: string): string {
  const n = norm(name);
  // Remove kunya/nisbah prefixes that create collision noise
  return n
    .replace(/^(?:ابو|ابي|ام|ابن|بنت)\s+/, '')
    .replace(/\s+(?:بن|بنت|ابن)\s+.*$/, '')  // keep only first word after stripping patronymic
    .trim()
    .split(/\s+/)[0] ?? n;  // use first token of core name as the block key
}

/**
 * Ambiguous-core kunya patterns whose collisions require HITL.
 * These names map to multiple valid scholars and cannot be auto-resolved.
 * Sources: spec FR-2.3, classify_attribution.py Imam markers.
 */
const AMBIGUOUS_KUNYAS: ReadonlyArray<RegExp> = [
  /^ابو\s+جعفر$/u,          // al-Kulaynī / al-Bāqir / al-Jawād
  /^ابو\s+عبد\s+الله$/u,    // al-Ṣādiq / others
  /^ابو\s+الحسن$/u,         // al-Kāẓim / al-Riḍā / al-Hādī
  /^ابو\s+محمد$/u,           // al-Ḥasan al-ʿAskarī / others
  /^ابو\s+ابراهيم$/u,        // al-Kāẓim (kunya)
];

function isAmbiguousKunya(normalizedName: string): boolean {
  return AMBIGUOUS_KUNYAS.some(rx => rx.test(normalizedName.trim()));
}

/**
 * Score a rawi candidate against a name token using available features.
 * Returns a confidence score in [0, 1].
 */
function scoreCandidate(
  normalizedToken: string,
  rawi: RawiRecord,
  contextTradition: string,
): { score: number; features: Record<string, unknown> } {
  const rawiNorm = norm(rawi.name);
  const features: Record<string, unknown> = {};

  // Exact normalized match
  const exactMatch = rawiNorm === normalizedToken;
  features['exact_match'] = exactMatch;

  // Blocked key match
  const bkToken = blockedKey(normalizedToken);
  const bkRawi = blockedKey(rawi.name);
  const blockedMatch = bkRawi === bkToken && bkToken.length > 2;
  features['blocked_match'] = blockedMatch;

  // Grade context: Imami scholars get a prior boost in Imami rows
  const isImami = contextTradition === 'Imami';
  const gradeStr = (rawi.grade || '').toLowerCase();
  const imamiBias = isImami && (
    gradeStr.includes('imam') ||
    gradeStr.includes('shia') ||
    gradeStr.includes('كوفي') ||
    gradeStr.includes('بغدادي')
  );
  features['tradition_bias'] = imamiBias;

  // Death date available (temporal plausibility handled in temporal-plausibility.ts)
  features['death_date_hijri'] = rawi.death_date_hijri ?? null;

  if (exactMatch) return { score: 0.92, features };
  if (blockedMatch) return { score: imamiBias ? 0.78 : 0.72, features };
  return { score: 0.0, features };
}

// ─── Staging JSONL writer ──────────────────────────────────────────────────────

const STAGING_PATH = path.join(process.cwd(), 'datasets', 'hadith-data', 'er-staging.jsonl');

/**
 * Append a staging record to er-staging.jsonl.
 * The file starts with a comment-header (written once on first creation).
 * This function is append-only — it never rewrites existing records.
 */
function appendToStaging(record: StagingRecord): void {
  fs.appendFileSync(STAGING_PATH, JSON.stringify(record) + '\n', 'utf8');
}

// ─── Main export: resolveNarrators ────────────────────────────────────────────

/**
 * Resolve narrator identities for one unified CSV row.
 *
 * Returns:
 *   resolved  — narrators successfully resolved to a scholar_indx.
 *   mentions  — unresolved names that become :NameMention nodes.
 *   method    — the dominant ErTier for this row.
 *
 * INVARIANT: this function NEVER writes :RESOLVES_TO or :SAME_AS to Neo4j.
 * Tier-3 ambiguous candidates are written to datasets/hadith-data/er-staging.jsonl
 * only. Human approval via ingest-er-approved.ts commits them.
 */
export async function resolveNarrators(
  row: UnifiedRow,
  rawis: Map<number, RawiRecord>,
): Promise<{ resolved: ResolvedNarrator[]; mentions: NameMentionDraft[]; method: ErTier }> {
  const resolved: ResolvedNarrator[] = [];
  const mentions: NameMentionDraft[] = [];
  const tradition = String(row.tradition ?? '');
  const sourceRowId = String(
    row.dataset_row_id ?? `${row.source ?? ''}|${row.hadith_no ?? ''}`
  );

  // ── Tier 1: chain_indx join (FR-2.1) ────────────────────────────────────────
  //
  // For Sunni rows (and Imami rows where Workstream A populated chain_indx),
  // chain_indx is a pre-resolved numeric ID array. Each ID maps directly to a
  // scholar_indx in all_rawis.csv.
  //
  // Verified coverage targets:
  //   Sunni K6 ≥ 99% | Sunni classical ≥ 55% (after WS-A) | Imami ≥ 84%
  //   Ibadi = 0%      | Zaydi = 0%  (these go to Tier 2)

  const chainIds = parseChainIndx(row.chain_indx as string | undefined);

  if (chainIds.length > 0) {
    let position = 0;
    for (const id of chainIds) {
      if (rawis.has(id)) {
        resolved.push({
          scholar_indx: id,
          position,
          confidence: 1.0,
          extraction_method: 'chain_indx_join',
        });
      } else {
        // chain_indx present but no matching scholar_indx → audit flag (spec FR-2.1)
        // Emit as a NameMention so the isnad link is never silently dropped (FR-1.3).
        mentions.push({
          surface_form: `[chain_indx:${id}]`,
          normalized_form: `[chain_indx:${id}]`,
          position,
        });
      }
      position++;
    }
    if (resolved.length > 0) {
      return { resolved, mentions, method: 'chain_indx_join' };
    }
    // All IDs had no matching rawi — fall through to Tier 2.
  }

  // ── Tier 2: exact / blocked lexicon (FR-2.2) ──────────────────────────────
  //
  // For rows missing chain_indx (Ibadi 100%, Zaydi 100%, Imami ~16% gap,
  // Sunni ~1%). Extract names from the sanad text, then:
  //   exact normalized match  → lexicon_exact, conf ≥ 0.9
  //   blocked key match       → lexicon_blocked, conf 0.7–0.8
  //   no match                → NameMention (unresolved; FR-1.3)
  //
  // Unmeasured strata (Imami-gap, Ibadi, Zaydi) get quarantined=true (NFR-3).
  const isUnmeasuredStratum =
    tradition === 'Ibadi' ||
    tradition === 'Zaydi' ||
    (tradition === 'Imami' && chainIds.length === 0);

  const sanadText = String(row.sanad ?? '');
  if (!sanadText.trim()) {
    // No sanad text — matn-only; nothing to resolve.
    return { resolved, mentions, method: 'lexicon_exact' };
  }

  const nameTokens = splitSanadNames(sanadText);
  let dominantMethod: ErTier = 'lexicon_exact';
  let anyResolved = false;

  // Build a normalized-name index for fast exact lookup.
  // (This is built per-call; callers should cache rawis Map and pass it.)
  const normIndex = new Map<string, RawiRecord[]>();
  const blockIndex = new Map<string, RawiRecord[]>();

  for (const rawi of rawis.values()) {
    const nk = norm(rawi.name);
    if (!normIndex.has(nk)) normIndex.set(nk, []);
    normIndex.get(nk)!.push(rawi);

    const bk = blockedKey(rawi.name);
    if (bk.length > 2) {
      if (!blockIndex.has(bk)) blockIndex.set(bk, []);
      blockIndex.get(bk)!.push(rawi);
    }
  }

  let position = 0;
  for (const token of nameTokens) {
    const normToken = norm(token);
    if (normToken.length < 3) { position++; continue; }

    // ── Tier 3 check: ambiguous kunya → staging queue, never auto-resolve ──
    if (isAmbiguousKunya(normToken)) {
      const blockCandidates = blockIndex.get(blockedKey(token)) ?? [];
      const scored = blockCandidates
        .map(r => {
          const { score, features } = scoreCandidate(normToken, r, tradition);
          return { scholar_indx: r.scholar_indx, name: r.name, grade: r.grade, death_date_hijri: r.death_date_hijri ?? null, score, features };
        })
        .filter(c => c.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 5);

      const stagingRecord: StagingRecord = {
        staged_at: Date.now(),
        surface_form: token,
        normalized_form: normToken,
        source_row_id: sourceRowId,
        tradition,
        position,
        candidates: scored,
        quarantined: isUnmeasuredStratum,
      };
      appendToStaging(stagingRecord);

      // Do NOT push to resolved — this is HITL only (spec FR-2.3, G-5).
      // Add a NameMention so the isnad link is not silently dropped.
      mentions.push({ surface_form: token, normalized_form: normToken, position });
      dominantMethod = 'rerank'; // signals ambiguous core was encountered
      position++;
      continue;
    }

    // Exact lexicon match
    const exactMatches = normIndex.get(normToken) ?? [];
    if (exactMatches.length === 1) {
      resolved.push({
        scholar_indx: exactMatches[0].scholar_indx,
        position,
        confidence: 0.92,
        extraction_method: 'lexicon_exact',
        ...(isUnmeasuredStratum ? { quarantined: true } : {}),
      });
      anyResolved = true;
      position++;
      continue;
    }

    if (exactMatches.length > 1) {
      // Multiple exact matches → ambiguous, emit all to staging.
      const scored = exactMatches
        .map(r => {
          const { score, features } = scoreCandidate(normToken, r, tradition);
          return { scholar_indx: r.scholar_indx, name: r.name, grade: r.grade, death_date_hijri: r.death_date_hijri ?? null, score, features };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 5);

      appendToStaging({
        staged_at: Date.now(),
        surface_form: token,
        normalized_form: normToken,
        source_row_id: sourceRowId,
        tradition,
        position,
        candidates: scored,
        quarantined: isUnmeasuredStratum,
      });
      mentions.push({ surface_form: token, normalized_form: normToken, position });
      dominantMethod = 'rerank';
      position++;
      continue;
    }

    // Blocked key match (normalized-key candidate)
    const bk = blockedKey(token);
    const blockCandidates = bk.length > 2 ? (blockIndex.get(bk) ?? []) : [];
    if (blockCandidates.length === 1) {
      const rawi = blockCandidates[0];
      const { score } = scoreCandidate(normToken, rawi, tradition);
      if (score >= 0.6) {
        resolved.push({
          scholar_indx: rawi.scholar_indx,
          position,
          confidence: score,
          extraction_method: 'lexicon_blocked',
          ...(isUnmeasuredStratum ? { quarantined: true } : {}),
        });
        anyResolved = true;
        if (dominantMethod === 'lexicon_exact') dominantMethod = 'lexicon_blocked';
        position++;
        continue;
      }
    }

    if (blockCandidates.length > 1) {
      // Blocked match but multiple candidates → staging
      const scored = blockCandidates
        .map(r => {
          const { score, features } = scoreCandidate(normToken, r, tradition);
          return { scholar_indx: r.scholar_indx, name: r.name, grade: r.grade, death_date_hijri: r.death_date_hijri ?? null, score, features };
        })
        .filter(c => c.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 5);

      if (scored.length > 0) {
        appendToStaging({
          staged_at: Date.now(),
          surface_form: token,
          normalized_form: normToken,
          source_row_id: sourceRowId,
          tradition,
          position,
          candidates: scored,
          quarantined: isUnmeasuredStratum,
        });
      }
      mentions.push({ surface_form: token, normalized_form: normToken, position });
      if (dominantMethod === 'lexicon_exact') dominantMethod = 'lexicon_blocked';
      position++;
      continue;
    }

    // No match at all → NameMention
    mentions.push({ surface_form: token, normalized_form: normToken, position });
    position++;
  }

  const effectiveMethod: ErTier = anyResolved
    ? dominantMethod
    : mentions.some(m => m.surface_form.startsWith('[chain_indx:'))
      ? 'chain_indx_join'
      : 'regex_sanad';

  return { resolved, mentions, method: effectiveMethod };
}
