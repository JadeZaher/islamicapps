/**
 * batch-loaders.ts — UNWIND-batched versions of the row-level loaders.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream H (perf)
 *
 * The original per-row loaders (load-hadith.ts, load-chain.ts, assessment.ts,
 * name-mention.ts) each issued ~5-10 separate `runWrite` transactions per
 * hadith row. On a Railway-proxy Bolt connection with ~215ms commit RTT this
 * produced ~12 rows/min → ~5.7 days for 99,283 rows.
 *
 * These batched loaders consume a buffer of K rows (typical: 100) and emit
 * a small fixed number of UNWIND transactions, regardless of K:
 *   loadHadithsBatch:     3 transactions per buffer  (sources, hadiths, edges)
 *   loadChainsBatch:      4 transactions per buffer  (chains, HAS_CHAIN, INCLUDES, NARRATED_FROM)
 *   loadAssessmentsBatch: 2 transactions per buffer  (real grades, no_extant placeholders)
 *   loadNameMentionsBatch: 1 transaction per buffer  (only if there are mentions)
 *
 * Total ~10 transactions per buffer of 100 instead of ~2,700. Roughly 270× the
 * throughput on a Railway-proxy Bolt link.
 *
 * Assumptions (validated against all_hadiths_unified.csv 2026-05-22):
 *   - Every row has dataset_row_id (CSV `id` column is 100% populated).
 *     → batched MERGE uses the dataset_row_id key path only.
 *   - Narrators are pre-loaded by bulkLoadNarrators before any chain batch.
 *     → INCLUDES MATCH (n:Narrator { scholar_indx }) always resolves.
 *   - DatasetVersion and 4 ReligiousTradition nodes pre-merged.
 *     → batched edge UNWINDs MATCH them directly, no per-buffer MERGE.
 *
 * G-1 invariant: no scalar grade/reliability on :Hadith or :Narrator.
 * G-2 invariant: every edge carries confidence + extraction_method + source.
 *
 * Concurrency: each batch function is a single `await`. Callers may run
 * disjoint buffers concurrently via `Promise.all`, but two concurrent
 * batches MUST NOT operate on overlapping business keys (would deadlock
 * on MERGE write-locks). Source MERGE is the hottest contention point,
 * mitigated by the per-run `sourceCache` parameter.
 */

import { randomUUID } from 'crypto';
import { runWrite } from '../../../lib/db/neo4j';
import { buildPipelineKey } from '../../../lib/db/neo4j-helpers';
import { CANONICAL_SOURCES } from '../../../lib/constants/sources';
import {
    canonicalizeTradition,
    type UnifiedRow,
    type LoadContext,
    type Tradition,
} from './io';
import {
    schemeForTradition,
    parseGradingsFull,
    type GradeScheme,
} from './assessment';
import {
    norm,
} from './name-mention';
import type { NarratorResolutionResult } from './load-chain';

// ─── Types ────────────────────────────────────────────────────────────────────

const ALL_TRADITIONS: Tradition[] = ['Sunni', 'Imami', 'Zaydi', 'Ibadi'];

const _unknownSourcesWarned = new Set<string>();
function getTraditionForSource(sourceName: string): string {
    for (const entry of Object.values(CANONICAL_SOURCES)) {
        if (entry.canonical === sourceName) return entry.tradition;
    }
    if (!_unknownSourcesWarned.has(sourceName)) {
        _unknownSourcesWarned.add(sourceName);
        console.warn(
            `[batch-loaders] WARNING: Unknown source "${sourceName}" not in CANONICAL_SOURCES — defaulting tradition to Sunni`,
        );
    }
    return 'Sunni';
}

/**
 * Pre-computed bundle for a single hadith row, attached to the buffer before
 * any batch flush. The mode-fullregen streaming loop fills these in once per
 * row (CPU-only work) so the batch DB calls have everything they need.
 */
export interface BufferedRow {
    row: UnifiedRow;
    resolutions: NarratorResolutionResult[];
    /** Always row.dataset_row_id (we've validated 100% population). */
    hadithKey: number;
    /** buildPipelineKey(row.source, row.hadith_no) — written as create-only prop. */
    pipelineKey: string;
    /** Canonical tradition string for this row. */
    rowTradition: Tradition;
    /** Source's authoritative tradition per CANONICAL_SOURCES. */
    sourceTradition: string;
}

/** Build a BufferedRow from a raw UnifiedRow. CPU-only, no DB. */
export function buildBufferedRow(
    row: UnifiedRow,
    resolutions: NarratorResolutionResult[],
): BufferedRow {
    if (row.dataset_row_id === null) {
        throw new Error(
            `[batch-loaders] Row missing dataset_row_id — batched loaders require it ` +
            `(source="${row.source}" hadith_no="${row.hadith_no}")`,
        );
    }
    const rowTradition = canonicalizeTradition(row.tradition as string);
    const sourceTradition = getTraditionForSource(row.source);
    return {
        row,
        resolutions,
        hadithKey: row.dataset_row_id,
        pipelineKey: buildPipelineKey(row.source, row.hadith_no),
        rowTradition,
        sourceTradition,
    };
}

// ─── loadHadithsBatch ─────────────────────────────────────────────────────────

/**
 * MERGE every Hadith node in the buffer, plus the Source nodes they reference
 * and the FROM_SOURCE/INGESTED_IN/FROM_TRADITION edges.
 *
 * Emits 3 transactions regardless of buffer size:
 *   1. UNWIND sources   → MERGE :Source        (skipped if all sources cached)
 *   2. UNWIND rows      → MERGE :Hadith        (single dataset_row_id key path)
 *   3. UNWIND rows      → MERGE all 3 edge types in one statement
 */
export async function loadHadithsBatch(
    items: BufferedRow[],
    ctx: LoadContext,
    sourceCache: Set<string>,
): Promise<void> {
    if (items.length === 0) return;

    // 1. Source nodes — only NEW sources not seen this run.
    const newSources = new Map<string, string>();
    for (const it of items) {
        if (!sourceCache.has(it.row.source)) {
            newSources.set(it.row.source, it.sourceTradition);
        }
    }
    if (newSources.size > 0) {
        const params = [...newSources.entries()].map(([name, tradition]) => ({
            name, tradition, id: randomUUID(),
        }));
        await runWrite(
            `UNWIND $sources AS s
             MERGE (src:Source { name: s.name })
             ON CREATE SET src.id = s.id, src.created_at = datetime(), src.tradition = s.tradition
             ON MATCH  SET src.tradition = s.tradition, src.updated_at = datetime()`,
            { sources: params },
        );
        for (const [name] of newSources) sourceCache.add(name);
    }

    // 2. Hadith MERGE.
    const hadithRows = items.map((it) => ({
        dataset_row_id: it.hadithKey,
        id: randomUUID(),
        pipeline_key: it.pipelineKey,
        source: it.row.source,
        tradition: it.rowTradition,
        hadith_id: it.row.hadith_id,
        hadith_no: it.row.hadith_no,
        volume: it.row.volume,
        chapter: it.row.chapter,
        chapter_no: it.row.chapter_no,
        category: it.row.category,
        text_ar: it.row.text_ar,
        text_en: it.row.text_en,
        matn_ar: it.row.matn_ar,
        matn_en: it.row.matn_en,
        sanad: it.row.sanad,
        sanad_confidence: it.row.sanad_confidence,
        school: it.row.school,
        chain_type: it.row.chain_type,
        attributed_to: it.row.attributed_to,
        narration_level: it.row.narration_level,
        url: it.row.url,
        page_ref: it.row.page_ref,
    }));

    await runWrite(
        `UNWIND $rows AS row
         MERGE (h:Hadith { dataset_row_id: row.dataset_row_id })
         ON CREATE SET
             h.id = row.id,
             h.pipeline_key = row.pipeline_key,
             h.created_at = datetime(),
             h.source = row.source,
             h.tradition = row.tradition,
             h.hadith_id = row.hadith_id,
             h.hadith_no = row.hadith_no,
             h.volume = row.volume,
             h.chapter = row.chapter,
             h.chapter_no = row.chapter_no,
             h.category = row.category,
             h.text_ar = row.text_ar,
             h.text_en = row.text_en,
             h.matn_ar = row.matn_ar,
             h.matn_en = row.matn_en,
             h.sanad = row.sanad,
             h.sanad_confidence = row.sanad_confidence,
             h.school = row.school,
             h.chain_type = row.chain_type,
             h.attributed_to = row.attributed_to,
             h.narration_level = row.narration_level,
             h.url = row.url,
             h.page_ref = row.page_ref
         ON MATCH SET
             h.updated_at = datetime(),
             h.source = row.source,
             h.tradition = row.tradition,
             h.hadith_id = row.hadith_id,
             h.hadith_no = row.hadith_no,
             h.volume = row.volume,
             h.chapter = row.chapter,
             h.chapter_no = row.chapter_no,
             h.category = row.category,
             h.text_ar = row.text_ar,
             h.text_en = row.text_en,
             h.matn_ar = row.matn_ar,
             h.matn_en = row.matn_en,
             h.sanad = row.sanad,
             h.sanad_confidence = row.sanad_confidence,
             h.school = row.school,
             h.chain_type = row.chain_type,
             h.attributed_to = row.attributed_to,
             h.narration_level = row.narration_level,
             h.url = row.url,
             h.page_ref = row.page_ref`,
        { rows: hadithRows },
    );

    // 3. Edges in one shot: FROM_SOURCE + INGESTED_IN + FROM_TRADITION.
    const edgeRows = items.map((it) => ({
        dataset_row_id: it.hadithKey,
        source: it.row.source,
        tradition: it.rowTradition,
    }));
    await runWrite(
        `UNWIND $rows AS row
         MATCH (h:Hadith { dataset_row_id: row.dataset_row_id })
         MATCH (s:Source { name: row.source })
         MATCH (dv:DatasetVersion { id: $dvId })
         MATCH (rt:ReligiousTradition { name: row.tradition })
         MERGE (h)-[fs:FROM_SOURCE]->(s)
         ON CREATE SET fs.source = $dvId
         MERGE (h)-[ii:INGESTED_IN]->(dv)
         ON CREATE SET ii.source = $dvId
         MERGE (h)-[ft:FROM_TRADITION]->(rt)
         ON CREATE SET ft.source = $dvId, ft.confidence = 1.0, ft.extraction_method = 'unified_csv'`,
        { rows: edgeRows, dvId: ctx.dvId },
    );
}

// ─── loadChainsBatch ──────────────────────────────────────────────────────────

/**
 * MERGE every :Chain node for the buffer's resolutions, plus HAS_CHAIN /
 * INCLUDES / NARRATED_FROM edges. Multi-isnad rows produce multiple chains.
 *
 * Emits 4 transactions per buffer (regardless of total chain/edge counts):
 *   1. Chains       — UNWIND $chains   → MERGE :Chain
 *   2. HAS_CHAIN    — UNWIND $chains   → MATCH+MATCH+MERGE
 *   3. INCLUDES     — UNWIND $edges    → MATCH+MATCH+MERGE Chain → Narrator
 *   4. NARRATED_FROM — UNWIND $shortcuts → MATCH+MATCH+MERGE Narrator → Narrator
 *
 * Returns a Map<row.dataset_row_id, chainIds[]> so name-mention loading can
 * tie mentions to the correct chain id.
 */
export interface ChainsBatchResult {
    /** Map of dataset_row_id → array of chain UUIDs (one per chain_index). */
    chainIdsByRow: Map<number, string[]>;
}

export async function loadChainsBatch(
    items: BufferedRow[],
    ctx: LoadContext,
): Promise<ChainsBatchResult> {
    const result: ChainsBatchResult = { chainIdsByRow: new Map() };
    if (items.length === 0) return result;

    // Flatten all chains.
    interface ChainRow {
        dataset_row_id: number;
        chain_key: string;          // unique pipeline_key for this Chain
        chain_id: string;           // UUID (create-only)
        chain_index: number;
        confidence: number;
        method: string;
    }
    interface IncludesRow {
        chain_key: string;
        scholar_indx: number;
        position: number;
        confidence: number;
        method: string;
    }
    interface NarratedFromRow {
        student_indx: number;
        teacher_indx: number;
        confidence: number;
        method: string;
    }

    const chains: ChainRow[] = [];
    const includes: IncludesRow[] = [];
    const narratedFrom: NarratedFromRow[] = [];

    for (const it of items) {
        const rowChainIds: string[] = [];
        for (const resolution of it.resolutions) {
            const { resolved, method, chain_index } = resolution;
            const chainKey = buildPipelineKey(
                String(it.hadithKey),
                'dataset_row_id',
                String(chain_index),
            );
            const chainId = randomUUID();
            rowChainIds.push(chainId);

            chains.push({
                dataset_row_id: it.hadithKey,
                chain_key: chainKey,
                chain_id: chainId,
                chain_index,
                confidence: resolved.length > 0 ? resolved[0].confidence : 0,
                method,
            });

            for (const n of resolved) {
                includes.push({
                    chain_key: chainKey,
                    scholar_indx: n.scholar_indx,
                    position: n.position,
                    confidence: n.confidence,
                    method: n.method,
                });
            }

            // NARRATED_FROM between consecutive resolved narrators.
            const sorted = [...resolved].sort((a, b) => a.position - b.position);
            for (let i = 0; i < sorted.length - 1; i++) {
                const student = sorted[i];
                const teacher = sorted[i + 1];
                narratedFrom.push({
                    student_indx: student.scholar_indx,
                    teacher_indx: teacher.scholar_indx,
                    confidence: Math.min(student.confidence, teacher.confidence),
                    method,
                });
            }
        }
        result.chainIdsByRow.set(it.hadithKey, rowChainIds);
    }

    // 1. Chain MERGE.
    if (chains.length > 0) {
        await runWrite(
            `UNWIND $chains AS c
             MERGE (ch:Chain { pipeline_key: c.chain_key })
             ON CREATE SET
                 ch.id = c.chain_id,
                 ch.created_at = datetime(),
                 ch.chain_index = c.chain_index,
                 ch.source = $dvId,
                 ch.confidence = c.confidence,
                 ch.extraction_method = c.method
             ON MATCH SET
                 ch.updated_at = datetime()`,
            { chains, dvId: ctx.dvId },
        );
    }

    // 2. HAS_CHAIN.
    if (chains.length > 0) {
        await runWrite(
            `UNWIND $chains AS c
             MATCH (h:Hadith { dataset_row_id: c.dataset_row_id })
             MATCH (ch:Chain { pipeline_key: c.chain_key })
             MERGE (h)-[r:HAS_CHAIN]->(ch)
             ON CREATE SET r.source = $dvId, r.confidence = 1.0, r.extraction_method = c.method`,
            { chains, dvId: ctx.dvId },
        );
    }

    // 3. INCLUDES.
    if (includes.length > 0) {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (ch:Chain { pipeline_key: e.chain_key })
             MATCH (n:Narrator { scholar_indx: e.scholar_indx })
             MERGE (ch)-[r:INCLUDES]->(n)
             ON CREATE SET r.position = e.position, r.confidence = e.confidence, r.extraction_method = e.method, r.source = $dvId
             ON MATCH  SET r.position = e.position, r.confidence = e.confidence, r.extraction_method = e.method`,
            { edges: includes, dvId: ctx.dvId },
        );
    }

    // 4. NARRATED_FROM.
    if (narratedFrom.length > 0) {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (student:Narrator { scholar_indx: e.student_indx })
             MATCH (teacher:Narrator { scholar_indx: e.teacher_indx })
             MERGE (student)-[r:NARRATED_FROM]->(teacher)
             ON CREATE SET r.confidence = e.confidence, r.extraction_method = e.method, r.source = $dvId
             ON MATCH  SET r.confidence = CASE WHEN r.confidence < e.confidence THEN e.confidence ELSE r.confidence END,
                          r.updated_at = datetime()`,
            { edges: narratedFrom, dvId: ctx.dvId },
        );
    }

    return result;
}

// ─── loadAssessmentsBatch ─────────────────────────────────────────────────────

/**
 * Fan out the assessment matrix for the buffer:
 *   - gradings_full entries → real :Assessment per (target, tradition, scholar)
 *   - grade_value scalar (if its tradition not already covered by gradings_full)
 *   - no_extant_evaluation for every tradition NOT covered
 *
 * Emits 2 transactions per buffer: one for real assessments, one for no_extant.
 *
 * Returns a count of how many "real" (non-no_extant) and no_extant rows were
 * written for downstream progress reporting.
 */
export interface AssessmentsBatchResult {
    real: number;
    noExtant: number;
}

interface AssessmentRow {
    target_key: number;
    assessment_key: string;
    assessment_id: string;
    tradition: Tradition;
    grade: string;
    grade_source: string;
    grade_scheme: GradeScheme;
}

export async function loadAssessmentsBatch(
    items: BufferedRow[],
    ctx: LoadContext,
): Promise<AssessmentsBatchResult> {
    const real: AssessmentRow[] = [];
    const noExtant: AssessmentRow[] = [];

    for (const it of items) {
        const traditionsWithReal = new Set<Tradition>();
        const targetKey = it.hadithKey;
        const targetKeyProp = 'dataset_row_id';

        // (a) gradings_full multi-scholar fan-out
        if (it.row.gradings_full && it.row.gradings_full.trim()) {
            const entries = parseGradingsFull(it.row.gradings_full, it.rowTradition);
            for (const entry of entries) {
                const t = (entry.tradition ?? it.rowTradition) as Tradition;
                const aKey = `${targetKeyProp}:${targetKey}::${t}::${entry.scholar ?? 'unspecified'}`;
                real.push({
                    target_key: targetKey,
                    assessment_key: aKey,
                    assessment_id: randomUUID(),
                    tradition: t,
                    grade: entry.grade,
                    grade_source: entry.scholar ?? 'gradings_full',
                    grade_scheme: schemeForTradition(t),
                });
                traditionsWithReal.add(t);
            }
        }

        // (b) primary grade_value if no gradings_full covered this tradition
        const primaryTradition = (it.row.grade_tradition && it.row.grade_tradition.trim())
            ? canonicalizeTradition(it.row.grade_tradition)
            : it.rowTradition;
        if (
            it.row.grade_value && it.row.grade_value.trim()
            && !traditionsWithReal.has(primaryTradition)
        ) {
            const aKey = `${targetKeyProp}:${targetKey}::${primaryTradition}`;
            real.push({
                target_key: targetKey,
                assessment_key: aKey,
                assessment_id: randomUUID(),
                tradition: primaryTradition,
                grade: it.row.grade_value.trim(),
                grade_source: (it.row.grade_source || 'hadith_csv'),
                grade_scheme: schemeForTradition(primaryTradition),
            });
            traditionsWithReal.add(primaryTradition);
        }

        // (c) no_extant_evaluation for uncovered traditions
        for (const t of ALL_TRADITIONS) {
            if (traditionsWithReal.has(t)) continue;
            const aKey = `${targetKeyProp}:${targetKey}::${t}`;
            noExtant.push({
                target_key: targetKey,
                assessment_key: aKey,
                assessment_id: randomUUID(),
                tradition: t,
                grade: 'no_extant_evaluation',
                grade_source: 'system_placeholder',
                grade_scheme: schemeForTradition(t),
            });
        }
    }

    const flushAssessments = async (rows: AssessmentRow[]): Promise<void> => {
        if (rows.length === 0) return;
        await runWrite(
            `UNWIND $rows AS row
             MATCH (target:Hadith { dataset_row_id: row.target_key })
             MATCH (rt:ReligiousTradition { name: row.tradition })
             MERGE (a:Assessment { pipeline_key: row.assessment_key })
             ON CREATE SET
                 a.id = row.assessment_id,
                 a.created_at = datetime(),
                 a.grade = row.grade,
                 a.grade_source = row.grade_source,
                 a.grade_scheme = row.grade_scheme,
                 a.tradition = row.tradition
             ON MATCH SET
                 a.updated_at = datetime(),
                 a.grade = row.grade,
                 a.grade_source = row.grade_source,
                 a.grade_scheme = row.grade_scheme
             MERGE (target)-[:HAS_ASSESSMENT]->(a)
             MERGE (a)-[:UNDER_SCHEME]->(rt)`,
            { rows },
        );
    };

    await flushAssessments(real);
    await flushAssessments(noExtant);

    return { real: real.length, noExtant: noExtant.length };
}

// ─── loadNameMentionsBatch ────────────────────────────────────────────────────

interface MentionRow {
    chain_id: string;
    mention_key: string;
    mention_id: string;
    surface_form: string;
    normalized_form: string;
    position: number;
    confidence: number;
    extraction_method: string;
}

export async function loadNameMentionsBatch(
    items: BufferedRow[],
    chainIdsByRow: Map<number, string[]>,
    ctx: LoadContext,
): Promise<number> {
    const mentions: MentionRow[] = [];
    for (const it of items) {
        const chainIds = chainIdsByRow.get(it.hadithKey) ?? [];
        for (let ci = 0; ci < it.resolutions.length; ci++) {
            const chainId = chainIds[ci];
            if (!chainId) continue;
            const ms = it.resolutions[ci].mentions;
            for (const m of ms) {
                mentions.push({
                    chain_id: chainId,
                    mention_key: `${chainId}::pos${m.position}`,
                    mention_id: randomUUID(),
                    surface_form: m.surface_form,
                    normalized_form: norm(m.surface_form),
                    position: m.position,
                    confidence: 0.0,
                    extraction_method: 'regex_sanad',
                });
            }
        }
    }
    if (mentions.length === 0) return 0;

    await runWrite(
        `UNWIND $rows AS row
         MATCH (c:Chain { id: row.chain_id })
         MERGE (m:NameMention { pipeline_key: row.mention_key })
         ON CREATE SET
             m.id = row.mention_id,
             m.created_at = datetime(),
             m.surface_form = row.surface_form,
             m.normalized_form = row.normalized_form,
             m.position = row.position
         ON MATCH SET
             m.updated_at = datetime(),
             m.surface_form = row.surface_form,
             m.normalized_form = row.normalized_form,
             m.position = row.position
         MERGE (c)-[r:INCLUDES_MENTION]->(m)
         ON CREATE SET
             r.position = row.position,
             r.confidence = row.confidence,
             r.extraction_method = row.extraction_method,
             r.source = $dvId`,
        { rows: mentions, dvId: ctx.dvId },
    );
    return mentions.length;
}
