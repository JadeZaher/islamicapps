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
 *   - Every release row passes preflight with a unique durable record_id.
 *     → dataset_row_id is retained only as positional compatibility metadata.
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

/**
 * Pre-computed bundle for a single hadith row, attached to the buffer before
 * any batch flush. The mode-fullregen streaming loop fills these in once per
 * row (CPU-only work) so the batch DB calls have everything they need.
 */
export interface BufferedRow {
    row: UnifiedRow;
    resolutions: NarratorResolutionResult[];
    /** Durable Hadith.record_id used by every downstream node/edge key. */
    hadithKey: string;
    /** Positional legacy id retained as metadata, never used as identity. */
    datasetRowId: number | null;
    /** buildPipelineKey(row.source, row.hadith_no) — written as create-only prop. */
    pipelineKey: string;
    /** Canonical tradition string for this row. */
    rowTradition: Tradition;
    /** Source tradition validated across the complete input during preflight. */
    sourceTradition: Tradition;
}

/** Build a BufferedRow from a raw UnifiedRow. CPU-only, no DB. */
export function buildBufferedRow(
    row: UnifiedRow,
    resolutions: NarratorResolutionResult[],
): BufferedRow {
    if (!row.record_id) {
        throw new Error(
            `[batch-loaders] Row missing record_id; run the curation preflight first ` +
            `(source="${row.source}" hadith_no="${row.hadith_no}")`,
        );
    }
    if (!row.source.trim()) {
        throw new Error('[batch-loaders] Row source must be nonblank');
    }
    const rowTradition = row.tradition;
    if (!ALL_TRADITIONS.includes(rowTradition)) {
        throw new Error(`[batch-loaders] Unsupported row tradition: ${String(rowTradition)}`);
    }
    const sourceTradition = rowTradition;
    return {
        row,
        resolutions,
        hadithKey: row.record_id,
        datasetRowId: row.dataset_row_id,
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
 *   2. UNWIND rows      → MERGE :Hadith        (durable record_id key path)
 *   3. UNWIND rows      → MERGE all 3 edge types in one statement
 */
export async function loadHadithsBatch(
    items: BufferedRow[],
    ctx: LoadContext,
    sourceCache: Map<string, Tradition>,
): Promise<void> {
    if (items.length === 0) return;

    // 1. Source nodes — only NEW sources not seen this run.
    const newSources = new Map<string, {
        tradition: Tradition;
        sourceWorkId: string;
        sourceDisplayLabel: string;
        compiler: string;
    }>();
    for (const it of items) {
        const cachedTradition = sourceCache.get(it.row.source);
        const pendingTradition = newSources.get(it.row.source);
        const knownTradition = cachedTradition ?? pendingTradition?.tradition;
        if (knownTradition && knownTradition !== it.sourceTradition) {
            throw new Error(
                `[batch-loaders] Source "${it.row.source}" has conflicting traditions ` +
                `${knownTradition} and ${it.sourceTradition}`,
            );
        }
        if (
            pendingTradition &&
            (pendingTradition.sourceWorkId !== it.row.source_work_id ||
             pendingTradition.sourceDisplayLabel !== it.row.source_display_label)
        ) {
            throw new Error(
                `[batch-loaders] Source "${it.row.source}" has conflicting durable work/display metadata`,
            );
        }
        if (!cachedTradition) {
            const registryEntry = Object.values(CANONICAL_SOURCES).find(
                (entry) => entry.canonical === it.row.source,
            );
            newSources.set(it.row.source, {
                tradition: it.sourceTradition,
                sourceWorkId: it.row.source_work_id,
                sourceDisplayLabel: it.row.source_display_label,
                compiler: registryEntry?.compiler ?? '',
            });
        }
    }
    if (newSources.size > 0) {
        const params = [...newSources.entries()].map(([name, source]) => ({
            name, id: randomUUID(), ...source,
        }));
        await runWrite(
            `UNWIND $sources AS s
             MERGE (src:Source { name: s.name })
             ON CREATE SET src.id = s.id, src.created_at = datetime(), src.tradition = s.tradition,
                           src.source_work_id = CASE WHEN s.sourceWorkId <> '' THEN s.sourceWorkId ELSE null END,
                           src.source_display_label = CASE WHEN s.sourceDisplayLabel <> '' THEN s.sourceDisplayLabel ELSE null END,
                           src.compiler_name = CASE WHEN s.compiler <> '' THEN s.compiler ELSE null END
             ON MATCH SET src.tradition = s.tradition, src.updated_at = datetime(),
                          src.source_work_id = CASE WHEN s.sourceWorkId <> '' THEN s.sourceWorkId ELSE src.source_work_id END,
                          src.source_display_label = CASE WHEN s.sourceDisplayLabel <> '' THEN s.sourceDisplayLabel ELSE src.source_display_label END,
                          src.compiler_name = CASE WHEN s.compiler <> '' THEN s.compiler ELSE src.compiler_name END`,
            { sources: params },
        );
        for (const [name, source] of newSources) sourceCache.set(name, source.tradition);
    }

    // 2. Hadith MERGE.
    const hadithRows = items.map((it) => ({
        record_id: it.hadithKey,
        dataset_row_id: it.datasetRowId,
        id: randomUUID(),
        pipeline_key: it.pipelineKey,
        source: it.row.source,
        source_work_id: it.row.source_work_id,
        source_display_label: it.row.source_display_label,
        tradition: it.rowTradition,
        hadith_id: it.row.hadith_id,
        hadith_no: it.row.hadith_no,
        volume: it.row.volume,
        chapter: it.row.chapter,
        chapter_no: it.row.chapter_no,
        category: it.row.category,
        text_ar: it.row.text_ar,
        text_en: it.row.text_en,
        source_record_id: it.row.source_record_id,
        provenance_source: it.row.provenance_source,
        translation_status: it.row.translation_status,
        translation_source: it.row.translation_source,
        translation_model: it.row.translation_model,
        translation_review_status: it.row.translation_review_status,
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
         MERGE (h:Hadith { record_id: row.record_id })
         ON CREATE SET
             h.id = row.id,
             h.dataset_row_id = row.dataset_row_id,
             h.pipeline_key = row.pipeline_key,
             h.created_at = datetime(),
             h.source = row.source,
             h.source_work_id = row.source_work_id,
             h.source_display_label = row.source_display_label,
             h.tradition = row.tradition,
             h.hadith_id = row.hadith_id,
             h.hadith_no = row.hadith_no,
             h.volume = row.volume,
             h.chapter = row.chapter,
             h.chapter_no = row.chapter_no,
             h.category = row.category,
             h.text_ar = row.text_ar,
             h.text_en = row.text_en,
             h.source_record_id = row.source_record_id,
             h.provenance_source = row.provenance_source,
             h.translation_status = row.translation_status,
             h.translation_source = row.translation_source,
             h.translation_model = row.translation_model,
             h.translation_review_status = row.translation_review_status,
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
             h.dataset_row_id = row.dataset_row_id,
             h.source = row.source,
             h.source_work_id = row.source_work_id,
             h.source_display_label = row.source_display_label,
             h.tradition = row.tradition,
             h.hadith_id = row.hadith_id,
             h.hadith_no = row.hadith_no,
             h.volume = row.volume,
             h.chapter = row.chapter,
             h.chapter_no = row.chapter_no,
             h.category = row.category,
             h.text_ar = row.text_ar,
             h.text_en = row.text_en,
             h.source_record_id = row.source_record_id,
             h.provenance_source = row.provenance_source,
             h.translation_status = row.translation_status,
             h.translation_source = row.translation_source,
             h.translation_model = row.translation_model,
             h.translation_review_status = row.translation_review_status,
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
        record_id: it.hadithKey,
        source: it.row.source,
        tradition: it.rowTradition,
    }));
    await runWrite(
        `UNWIND $rows AS row
         MATCH (h:Hadith { record_id: row.record_id })
         MATCH (s:Source { name: row.source })
         MATCH (dv:DatasetVersion { id: $dvId })
         MATCH (rt:ReligiousTradition { name: row.tradition })
         MERGE (h)-[fs:FROM_SOURCE]->(s)
         SET fs.source = $dvId, fs.confidence = 1.0, fs.extraction_method = 'unified_csv'
         MERGE (h)-[ii:INGESTED_IN]->(dv)
         SET ii.source = $dvId, ii.confidence = 1.0, ii.extraction_method = 'unified_csv'
         MERGE (h)-[ft:FROM_TRADITION]->(rt)
         SET ft.source = $dvId, ft.confidence = 1.0, ft.extraction_method = 'unified_csv'`,
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
 * Returns a Map<record_id, chain pipeline keys[]> so name-mention loading can
 * tie mentions to the correct stable chain.
 */
export interface ChainsBatchResult {
    /** Map of record_id → array of chain pipeline keys (one per chain_index). */
    chainKeysByRow: Map<string, string[]>;
}

export async function loadChainsBatch(
    items: BufferedRow[],
    ctx: LoadContext,
): Promise<ChainsBatchResult> {
    const result: ChainsBatchResult = { chainKeysByRow: new Map() };
    if (items.length === 0) return result;

    // Flatten all chains.
    interface ChainRow {
        record_id: string;
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
    const narratedFrom = new Map<string, NarratedFromRow>();

    for (const it of items) {
        const rowChainKeys: string[] = [];
        for (const resolution of it.resolutions) {
            const { resolved, method, chain_index } = resolution;
            const chainKey = buildPipelineKey(
                String(it.hadithKey),
                'record_id',
                String(chain_index),
            );
            const chainId = randomUUID();
            rowChainKeys.push(chainKey);

            chains.push({
                record_id: it.hadithKey,
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
                if (teacher.position !== student.position + 1) continue;
                const edge = {
                    student_indx: student.scholar_indx,
                    teacher_indx: teacher.scholar_indx,
                    confidence: Math.min(student.confidence, teacher.confidence),
                    method,
                };
                const edgeKey = `${edge.student_indx}::${edge.teacher_indx}`;
                const prior = narratedFrom.get(edgeKey);
                if (!prior || prior.confidence < edge.confidence) narratedFrom.set(edgeKey, edge);
            }
        }
        result.chainKeysByRow.set(it.hadithKey, rowChainKeys);
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
                 ch.updated_at = datetime(),
                 ch.chain_index = c.chain_index,
                 ch.source = $dvId,
                 ch.confidence = c.confidence,
                 ch.extraction_method = c.method`,
            { chains, dvId: ctx.dvId },
        );
    }

    // 2. HAS_CHAIN.
    if (chains.length > 0) {
        await runWrite(
            `UNWIND $chains AS c
             MATCH (h:Hadith { record_id: c.record_id })
             MATCH (ch:Chain { pipeline_key: c.chain_key })
             MERGE (h)-[r:HAS_CHAIN]->(ch)
             SET r.source = $dvId, r.confidence = 1.0, r.extraction_method = c.method`,
            { chains, dvId: ctx.dvId },
        );
    }

    // 3. INCLUDES.
    if (includes.length > 0) {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (ch:Chain { pipeline_key: e.chain_key })
             MATCH (n:Narrator { scholar_indx: e.scholar_indx })
             MERGE (ch)-[r:INCLUDES { position: e.position }]->(n)
             ON CREATE SET r.confidence = e.confidence, r.extraction_method = e.method, r.source = $dvId
             ON MATCH  SET r.confidence = e.confidence, r.extraction_method = e.method, r.source = $dvId`,
            { edges: includes, dvId: ctx.dvId },
        );
    }

    // 4. NARRATED_FROM.
    if (narratedFrom.size > 0) {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (student:Narrator { scholar_indx: e.student_indx })
             MATCH (teacher:Narrator { scholar_indx: e.teacher_indx })
             MERGE (student)-[r:NARRATED_FROM]->(teacher)
             ON CREATE SET r.confidence = e.confidence, r.extraction_method = e.method, r.source = $dvId
             ON MATCH  SET r.extraction_method = CASE WHEN coalesce(r.confidence, -1.0) < e.confidence THEN e.method ELSE coalesce(r.extraction_method, e.method) END,
                          r.confidence = CASE WHEN coalesce(r.confidence, -1.0) < e.confidence THEN e.confidence ELSE coalesce(r.confidence, e.confidence) END,
                          r.source = $dvId,
                          r.updated_at = datetime()`,
            { edges: [...narratedFrom.values()], dvId: ctx.dvId },
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
    target_key: string;
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
        const targetKeyProp = 'record_id';

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
             MATCH (target:Hadith { record_id: row.target_key })
             MATCH (rt:ReligiousTradition { name: row.tradition })
             MERGE (a:Assessment { pipeline_key: row.assessment_key })
             ON CREATE SET
                 a.id = row.assessment_id,
                 a.created_at = datetime(),
                 a.grade = row.grade,
                 a.grade_source = row.grade_source,
                 a.grade_scheme = row.grade_scheme,
                 a.tradition = row.tradition,
                 a.source = $dvId
             ON MATCH SET
                 a.updated_at = datetime(),
                 a.grade = row.grade,
                 a.grade_source = row.grade_source,
                 a.grade_scheme = row.grade_scheme,
                 a.source = $dvId
             MERGE (target)-[ha:HAS_ASSESSMENT]->(a)
             SET ha.source = $dvId, ha.confidence = 1.0, ha.extraction_method = 'assessment_matrix'
             MERGE (a)-[us:UNDER_SCHEME]->(rt)
             SET us.source = $dvId, us.confidence = 1.0, us.extraction_method = 'assessment_matrix'`,
            { rows, dvId: ctx.dvId },
        );
    };

    await flushAssessments(real);
    await flushAssessments(noExtant);

    return { real: real.length, noExtant: noExtant.length };
}

// ─── loadNameMentionsBatch ────────────────────────────────────────────────────

interface MentionRow {
    chain_key: string;
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
    chainKeysByRow: Map<string, string[]>,
    ctx: LoadContext,
): Promise<number> {
    const mentions: MentionRow[] = [];
    for (const it of items) {
        const chainKeys = chainKeysByRow.get(it.hadithKey) ?? [];
        for (let ci = 0; ci < it.resolutions.length; ci++) {
            const chainKey = chainKeys[ci];
            if (!chainKey) continue;
            const ms = it.resolutions[ci].mentions;
            for (const m of ms) {
                mentions.push({
                    chain_key: chainKey,
                    mention_key: `${chainKey}::pos${m.position}`,
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
         MATCH (c:Chain { pipeline_key: row.chain_key })
         MERGE (m:NameMention { pipeline_key: row.mention_key })
         ON CREATE SET
             m.id = row.mention_id,
             m.created_at = datetime(),
             m.surface_form = row.surface_form,
             m.normalized_form = row.normalized_form,
             m.position = row.position,
             m.source = $dvId
         ON MATCH SET
             m.updated_at = datetime(),
             m.surface_form = row.surface_form,
             m.normalized_form = row.normalized_form,
             m.position = row.position,
             m.source = $dvId
         MERGE (c)-[r:INCLUDES_MENTION]->(m)
         SET r.position = row.position,
             r.confidence = row.confidence,
             r.extraction_method = row.extraction_method,
             r.source = $dvId`,
        { rows: mentions, dvId: ctx.dvId },
    );
    return mentions.length;
}
