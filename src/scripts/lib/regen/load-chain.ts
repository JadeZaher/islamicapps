/**
 * load-chain.ts — Reified :Chain node loader and narrator-edge materializer.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   loadChain(hadiths, resolvedNarrators, ctx) → Promise<void>
 *   loadChainForRow(row, resolvedNarrators, ctx) → Promise<{ chainIds: string[] }>
 *
 * Schema contract (FR-1.2 / FR-1.3):
 *   (:Hadith)-[:HAS_CHAIN]->(:Chain)-[:INCLUDES {position}]->(:Narrator)
 *   (:Narrator)-[:NARRATED_FROM {confidence, extraction_method, source}]->(:Narrator)
 *     ← shortcut edges ONLY between RESOLVED narrators (not NameMentions).
 *
 * Multi-isnad hadith: one :Chain node per distinct isnad (not merged).
 *
 * Every edge carries (G-4, G-6):
 *   confidence (0–1), extraction_method (ErTier string), source (dvId)
 *
 * NEVER writes reliability/grade on :Narrator (G-1).
 */

import { randomUUID } from 'crypto';
import { runWrite } from '../../../lib/db/neo4j';
import { buildPipelineKey } from '../../../lib/db/neo4j-helpers';
import type { UnifiedRow, LoadContext } from './io';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ErTier =
    | 'chain_indx_join'
    | 'lexicon_exact'
    | 'lexicon_blocked'
    | 'rerank'
    | 'regex_sanad';

/** A narrator that has been fully resolved to a :Narrator node by scholar_indx. */
export interface ResolvedNarrator {
    scholar_indx: number;
    position: number; // 0-based position in the chain
    confidence: number;
    method: ErTier;
}

/** Represents an unresolved narrator that will become a :NameMention node. */
export interface NameMentionDraft {
    surface_form: string;
    normalized_form: string;
    position: number;
    hadith_key: string | number;
    hadith_key_prop: 'dataset_row_id' | 'pipeline_key';
}

/** Full resolution result from entity-resolution.ts (workstream D contract). */
export interface NarratorResolutionResult {
    resolved: ResolvedNarrator[];
    mentions: NameMentionDraft[];
    method: ErTier;
    chain_index: number; // which isnad (0-based) in a multi-isnad hadith
}

// ─── Chain business key ───────────────────────────────────────────────────────

/**
 * Build a stable business key for a :Chain node.
 * Multi-isnad hadiths get one key per chain index.
 */
function buildChainKey(
    hadithKey: string | number,
    keyProp: 'dataset_row_id' | 'pipeline_key',
    chainIndex: number
): string {
    return buildPipelineKey(String(hadithKey), keyProp, String(chainIndex));
}

// ─── loadChainForRow ──────────────────────────────────────────────────────────

/**
 * Load all :Chain nodes for a single hadith row, plus :INCLUDES edges and
 * :NARRATED_FROM shortcut edges between resolved narrators.
 *
 * @param row           The unified CSV row (already merged as :Hadith).
 * @param resolutions   One NarratorResolutionResult per distinct isnad.
 * @param ctx           LoadContext carrying dvId, mode, log.
 */
export async function loadChainForRow(
    row: UnifiedRow,
    resolutions: NarratorResolutionResult[],
    ctx: LoadContext
): Promise<{ chainIds: string[] }> {
    const { dvId, log } = ctx;

    const hasRowId = row.dataset_row_id !== null;
    const hadithKey: string | number = hasRowId
        ? row.dataset_row_id!
        : buildPipelineKey(row.source, row.hadith_no);
    const keyProp: 'dataset_row_id' | 'pipeline_key' = hasRowId
        ? 'dataset_row_id'
        : 'pipeline_key';

    const chainIds: string[] = [];

    for (const resolution of resolutions) {
        const { resolved, method, chain_index } = resolution;

        const chainKey = buildChainKey(hadithKey, keyProp, chain_index);

        // 1. MERGE :Chain node.
        const chainId = randomUUID();
        const chainCypher = `
            MERGE (c:Chain { pipeline_key: $chainKey })
            ON CREATE SET
                c.id = $chainId,
                c.created_at = datetime(),
                c.chain_index = $chainIndex,
                c.source = $dvId,
                c.confidence = $confidence,
                c.extraction_method = $method
            ON MATCH SET
                c.updated_at = datetime()
            RETURN c.id AS id
        `;
        const chainRows = await runWrite<{ id: string }>(chainCypher, {
            chainKey,
            chainId,
            chainIndex: chain_index,
            dvId,
            confidence: resolved.length > 0 ? resolved[0].confidence : 0,
            method,
        });

        if (!chainRows.length) {
            log({ action: 'error', entity: 'Chain', key: chainKey, error: 'MERGE returned no rows' });
            continue;
        }
        const actualChainId = chainRows[0].id;
        chainIds.push(actualChainId);

        // 2. HAS_CHAIN: Hadith → Chain (idempotent).
        const hadithChainCypher = `
            MATCH (h:Hadith { ${keyProp}: $hadithKey })
            MATCH (c:Chain { id: $chainId })
            MERGE (h)-[r:HAS_CHAIN]->(c)
            ON CREATE SET
                r.source = $dvId,
                r.confidence = 1.0,
                r.extraction_method = $method
        `;
        await runWrite(hadithChainCypher, {
            hadithKey,
            chainId: actualChainId,
            dvId,
            method,
        });

        // 3. INCLUDES: Chain → Narrator for each resolved narrator.
        for (const narrator of resolved) {
            const includesCypher = `
                MATCH (c:Chain { id: $chainId })
                MATCH (n:Narrator { scholar_indx: $scholarIndx })
                MERGE (c)-[r:INCLUDES]->(n)
                ON CREATE SET
                    r.position = $position,
                    r.confidence = $confidence,
                    r.extraction_method = $method,
                    r.source = $dvId
                ON MATCH SET
                    r.position = $position,
                    r.confidence = $confidence,
                    r.extraction_method = $method
            `;
            await runWrite(includesCypher, {
                chainId: actualChainId,
                scholarIndx: narrator.scholar_indx,
                position: narrator.position,
                confidence: narrator.confidence,
                method: narrator.method,
                dvId,
            });
        }

        // 4. NARRATED_FROM shortcut edges between consecutive RESOLVED narrators.
        // Only between resolved narrators (not between NameMentions — per spec).
        // Position ordering: narrator[i] narrated FROM narrator[i+1]
        // (i.e., later in list = earlier in time = teacher).
        const sorted = [...resolved].sort((a, b) => a.position - b.position);
        for (let i = 0; i < sorted.length - 1; i++) {
            const student = sorted[i];
            const teacher = sorted[i + 1];
            const narratedFromCypher = `
                MATCH (student:Narrator { scholar_indx: $studentIndx })
                MATCH (teacher:Narrator { scholar_indx: $teacherIndx })
                MERGE (student)-[r:NARRATED_FROM]->(teacher)
                ON CREATE SET
                    r.confidence = $confidence,
                    r.extraction_method = $method,
                    r.source = $dvId
                ON MATCH SET
                    r.confidence = CASE WHEN r.confidence < $confidence THEN $confidence ELSE r.confidence END,
                    r.updated_at = datetime()
            `;
            const edgeConfidence = Math.min(student.confidence, teacher.confidence);
            await runWrite(narratedFromCypher, {
                studentIndx: student.scholar_indx,
                teacherIndx: teacher.scholar_indx,
                confidence: edgeConfidence,
                method,
                dvId,
            });
        }

        log({
            action: 'chain_loaded',
            entity: 'Chain',
            key: chainKey,
            chain_index,
            resolved_count: resolved.length,
            method,
            dvId,
        });
    }
    return { chainIds };
}

// ─── Tier-1 chain loading (chain_indx direct join) ───────────────────────────

/**
 * Convenience function for the common Tier-1 case: the row has chain_indx
 * already (array of scholar_indx values), so we skip entity resolution and
 * directly emit ResolvedNarrator objects.
 *
 * Returns the NarratorResolutionResult array suitable for loadChainForRow().
 */
export function buildTier1Resolution(row: UnifiedRow): NarratorResolutionResult[] {
    if (row.chain_indx.length === 0) return [];

    const resolved: ResolvedNarrator[] = row.chain_indx.map((idx, pos) => ({
        scholar_indx: idx,
        position: pos,
        confidence: 1.0,
        method: 'chain_indx_join',
    }));

    return [
        {
            resolved,
            mentions: [],
            method: 'chain_indx_join',
            chain_index: 0,
        },
    ];
}
