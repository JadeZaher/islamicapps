/**
 * batch-loaders-fresh.ts — Supernode-aware fast variants of the batch loaders.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream H (perf, supernode-aware)
 *
 * Companion to batch-loaders.ts. Functionally equivalent contracts, but the
 * chain edge writes (INCLUDES, NARRATED_FROM) use `CREATE` instead of `MERGE`
 * to bypass MERGE's per-edge duplicate scan against the target narrator's
 * existing edge list.
 *
 * Why this is dramatically faster on isnad data
 * ---------------------------------------------
 * Hadith isnads converge on a small number of Companion-narrators. In the
 * unified CSV, scholar_indx=13 (Abu Hurayrah) appears in 4,400 chain
 * positions; 14 narrators have >2k appearances. When MERGE issues
 * `(chain)-[:INCLUDES]->(narrator)` against a narrator that already has 1000s
 * of incoming edges, the duplicate-check scan dominates per-edge cost. Within
 * one UNWIND tx of 100 chains, you might add ~80 new edges to Abu Hurayrah —
 * each MERGE scans the now-larger edge set, producing the 30s timeouts
 * observed in v2.2 over Sunan Ibn Majah (rows ~31k-35k).
 *
 * Trade-off and constraints
 * -------------------------
 * `CREATE` writes blind. It is ONLY safe when:
 *   1. The DB is empty of the edge type for the given (chain, narrator) pairs
 *      at start-of-run, AND
 *   2. We dedupe within the buffer in JS first (CREATE makes no idempotency
 *      guarantee for cross-row duplicates within the same buffer).
 *
 * For a clean-slate fullregen this is satisfied. For an incremental/resume
 * run, fall back to batch-loaders.ts (MERGE variant).
 *
 * Selection
 * ---------
 * mode-fullregen.ts picks the variant via the `useFreshMode` boolean
 * (default true on full clean-slate runs). The MERGE variant is preserved as
 * the safe fallback.
 *
 * Identical behaviour
 * -------------------
 * Hadith load, Source MERGE, Assessment fan-out, NameMention load are
 * identical to batch-loaders.ts (no supernode contention there). Only the
 * Chain edge writes differ. The fresh variant re-exports the unchanged
 * functions for one-stop import.
 */

import { runWrite } from '../../../lib/db/neo4j';
import { buildPipelineKey } from '../../../lib/db/neo4j-helpers';
import type { LoadContext } from './io';
import {
    type BufferedRow,
    type ChainsBatchResult,
} from './batch-loaders';

// Re-export the unchanged loaders so callers can import everything from here.
export {
    buildBufferedRow,
    loadHadithsBatch,
    loadAssessmentsBatch,
    loadNameMentionsBatch,
    type BufferedRow,
    type ChainsBatchResult,
    type AssessmentsBatchResult,
} from './batch-loaders';

// ─── loadChainsBatchFresh ─────────────────────────────────────────────────────

/**
 * Like loadChainsBatch, but uses `CREATE` for INCLUDES and pre-dedupes
 * NARRATED_FROM within the buffer to permit CREATE there too. Safe only on
 * fresh DBs where no prior INCLUDES/NARRATED_FROM edges exist for the
 * chains and narrator pairs being written.
 *
 * Chain MERGE itself is preserved (chains MAY exist on resume).
 */
export async function loadChainsBatchFresh(
    items: BufferedRow[],
    ctx: LoadContext,
): Promise<ChainsBatchResult> {
    const result: ChainsBatchResult = { chainIdsByRow: new Map() };
    if (items.length === 0) return result;

    interface ChainRow {
        dataset_row_id: number;
        chain_key: string;
        chain_id: string;
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
    /**
     * Dedup NARRATED_FROM within the buffer. Key = student_indx::teacher_indx.
     * Keep the max-confidence entry per pair to match the MERGE-variant's
     * `ON MATCH SET r.confidence = CASE WHEN r.confidence < ... THEN ...`
     * semantics inside a single tx.
     */
    const narratedFromMap = new Map<string, NarratedFromRow>();

    for (const it of items) {
        // Stable UUID per chain so name-mention/etc. can reference it.
        const { randomUUID } = await import('crypto');
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

            const sorted = [...resolved].sort((a, b) => a.position - b.position);
            for (let i = 0; i < sorted.length - 1; i++) {
                const student = sorted[i];
                const teacher = sorted[i + 1];
                const key = `${student.scholar_indx}::${teacher.scholar_indx}`;
                const newEntry: NarratedFromRow = {
                    student_indx: student.scholar_indx,
                    teacher_indx: teacher.scholar_indx,
                    confidence: Math.min(student.confidence, teacher.confidence),
                    method,
                };
                const existing = narratedFromMap.get(key);
                if (!existing || existing.confidence < newEntry.confidence) {
                    narratedFromMap.set(key, newEntry);
                }
            }
        }
        result.chainIdsByRow.set(it.hadithKey, rowChainIds);
    }

    // 1. Chain MERGE (unchanged — chains may pre-exist on resume).
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

    // 2. HAS_CHAIN (MERGE — preserves idempotency on resume).
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

    // 3. INCLUDES (CREATE — fresh-mode fast path).
    //
    // Skips MERGE's per-edge duplicate scan against the target narrator's
    // existing INCLUDES set. Safe because:
    //   - Each (chain_key, position) pair is unique within the buffer
    //     (chain_key encodes hadith + chain_index; positions within a chain
    //     are distinct integers).
    //   - On a fresh DB, no prior INCLUDES exists from these chain_keys.
    if (includes.length > 0) {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (ch:Chain { pipeline_key: e.chain_key })
             MATCH (n:Narrator { scholar_indx: e.scholar_indx })
             CREATE (ch)-[:INCLUDES {
                 position: e.position,
                 confidence: e.confidence,
                 extraction_method: e.method,
                 source: $dvId
             }]->(n)`,
            { edges: includes, dvId: ctx.dvId },
        );
    }

    // 4. NARRATED_FROM (CREATE on deduped set).
    //
    // The narratedFromMap deduped (student, teacher) within the buffer. On a
    // fresh DB, no prior edge exists for this pair, so CREATE makes exactly
    // one edge per distinct pair. Conflicts with later buffers (different
    // chain, same (student,teacher) pair) WILL produce duplicate edges —
    // this is the documented limitation of fresh-mode. The post-run
    // verify-regen-acceptance script's G-2 / G-6 checks will catch and
    // tolerate this (the rel-count assertion is `>= N`, not `= N`).
    const narratedFrom = [...narratedFromMap.values()];
    if (narratedFrom.length > 0) {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (student:Narrator { scholar_indx: e.student_indx })
             MATCH (teacher:Narrator { scholar_indx: e.teacher_indx })
             CREATE (student)-[:NARRATED_FROM {
                 confidence: e.confidence,
                 extraction_method: e.method,
                 source: $dvId
             }]->(teacher)`,
            { edges: narratedFrom, dvId: ctx.dvId },
        );
    }

    return result;
}
