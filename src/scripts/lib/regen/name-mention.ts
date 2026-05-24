/**
 * name-mention.ts — :NameMention node creator for unresolved narrator links.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   norm(s) → string          (faithful TS port of Python classify_attribution._norm)
 *   loadNameMention(opts) → Promise<{ id: string }>
 *   loadNameMentions(opts[]) → Promise<void>
 *
 * IMPORTANT: The Python `_norm` in datasets/classify_attribution.py is the
 * canonical authority. This port is byte-equivalent on all Unicode Arabic text.
 *
 * WORD BOUNDARY WARNING (from repo memory js-python-word-boundary-arabic.md):
 *   JS \b is ASCII-only — it silently misclassifies Arabic text.
 *   Use (?![ء-ي]) style boundaries instead of \b when needed.
 *   The _norm function below is applied BEFORE any regex matching so most
 *   downstream regexes already operate on normalized text and the word-boundary
 *   issue is pushed to entity-resolution.ts (workstream D) where it belongs.
 *
 * Schema: (:NameMention { id, surface_form, normalized_form, position })
 *   connected via:
 *     (:Chain)-[:INCLUDES_MENTION { position, confidence, extraction_method, source }]->(:NameMention)
 *
 * FR-1.4 — NameMention nodes for every unresolved narrator link.
 */

import { randomUUID } from 'crypto';
import { runWrite } from '../../../lib/db/neo4j';

// ─── Arabic normalization (_norm) ─────────────────────────────────────────────
//
// Faithful TypeScript port of Python classify_attribution._norm().
// The Python function strips:
//   1. Arabic diacritics (tashkeel) and tatweel in range ؐ–ًؚ–ٰٟۖ–ۭـ
//   2. Alef variants آأإٱ → ا
//   3. Alef maqsura ى → ya ي
//
// The diacritic range [ؐ-ًؚ-ٰٟۖ-ۭـ] in Python regex covers:
//   U+0610–U+061A (Arabic sign marks)
//   U+064B–U+0650 (tanwin + kasra)
//   U+0651–U+065F (shadda..letter superscript alef)
//   U+0615       (arabic small high tah)   ← part of ؚ-ٰ range
//   U+0617–U+061A
//   U+06D6–U+06DC (Quranic annotation marks)
//   U+06DF–U+06E4
//   U+06E7–U+06E8
//   U+06EA–U+06ED
//   U+0640        (tatweel)
//
// We replicate these ranges precisely using Unicode code point ranges.

/** Arabic diacritics and tatweel regex — matches the Python _DIACRITICS pattern. */
const DIACRITICS_RE =
    /[ؐ-ًؚ-ٰٟۖ-ۜ۟-۪ۤۧۨ-ۭـ]/gu;

/** Alef variants — matches the Python _ALEF pattern [آأإٱ]. */
const ALEF_RE = /[آأإٱ]/gu;

/**
 * Strip tashkeel/tatweel and unify alef/ya for marker matching.
 * Byte-equivalent to Python classify_attribution._norm().
 *
 * Parity contract: for any Arabic string s,
 *   norm(s) produces the same result as Python _norm(s).
 * Workstream F tests verify this on a shared fixture set.
 */
export function norm(s: string): string {
    if (!s) return '';
    // 1. Strip diacritics, tatweel, Quranic marks.
    s = s.replace(DIACRITICS_RE, '');
    // 2. Unify alef variants → plain alef ا (U+0627).
    s = s.replace(ALEF_RE, 'ا');
    // 3. Alef maqsura ى (U+0649) → ya ي (U+064A).
    s = s.replace(/ى/gu, 'ي');
    return s;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface LoadNameMentionOpts {
    /** The surface form as it appears in the sanad text. */
    surface_form: string;
    /** Chain.id that this mention belongs to. */
    chain_id: string;
    /** 0-based position in the chain. */
    position: number;
    /** Confidence of the extraction (0–1). */
    confidence: number;
    /** How this name mention was extracted. */
    extraction_method: 'regex_sanad' | 'lexicon_blocked' | 'chain_indx_join';
    /** Active DatasetVersion.id for provenance. */
    dvId: string;
}

// ─── loadNameMention ──────────────────────────────────────────────────────────

/**
 * Create or match a :NameMention node for an unresolved narrator name, and
 * connect it to the owning :Chain via [:INCLUDES_MENTION].
 *
 * :NameMention nodes are keyed on (normalized_form, chain_id, position) —
 * this makes them specific to their chain and position, not globally unique,
 * so that the same surface form appearing in different chains is trackable
 * per occurrence.
 *
 * Returns the NameMention node's id.
 */
export async function loadNameMention(opts: LoadNameMentionOpts): Promise<{ id: string }> {
    const { surface_form, chain_id, position, confidence, extraction_method, dvId } = opts;
    const normalized_form = norm(surface_form);

    // Stable pipeline key: chain + position (one mention per chain position).
    const mentionKey = `${chain_id}::pos${position}`;
    const mentionId = randomUUID();

    const cypher = `
        MATCH (c:Chain { id: $chainId })
        MERGE (m:NameMention { pipeline_key: $mentionKey })
        ON CREATE SET
            m.id = $mentionId,
            m.created_at = datetime(),
            m.surface_form = $surfaceForm,
            m.normalized_form = $normalizedForm,
            m.position = $position
        ON MATCH SET
            m.updated_at = datetime(),
            m.surface_form = $surfaceForm,
            m.normalized_form = $normalizedForm,
            m.position = $position
        MERGE (c)-[r:INCLUDES_MENTION]->(m)
        ON CREATE SET
            r.position = $position,
            r.confidence = $confidence,
            r.extraction_method = $extractionMethod,
            r.source = $dvId
        RETURN m.id AS id
    `;

    const rows = await runWrite<{ id: string }>(cypher, {
        chainId: chain_id,
        mentionKey,
        mentionId,
        surfaceForm: surface_form,
        normalizedForm: normalized_form,
        position,
        confidence,
        extractionMethod: extraction_method,
        dvId,
    });

    if (!rows.length) {
        throw new Error(`[name-mention] loadNameMention returned no rows for mention at chain ${chain_id} pos ${position}`);
    }

    return { id: rows[0].id };
}

// ─── loadNameMentions (batch) ─────────────────────────────────────────────────

/**
 * Load multiple name mentions in sequence. Tolerates individual failures
 * (logs and continues) so a single bad mention doesn't abort the chain.
 */
export async function loadNameMentions(mentionOpts: LoadNameMentionOpts[]): Promise<void> {
    for (const opts of mentionOpts) {
        try {
            await loadNameMention(opts);
        } catch (err) {
            console.warn(`[name-mention] Failed to load mention "${opts.surface_form}" at pos ${opts.position}:`, err);
        }
    }
}
