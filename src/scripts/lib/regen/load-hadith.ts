/**
 * load-hadith.ts — Hadith node loader for the regen pipeline.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   loadHadith(row, ctx) → Promise<void>
 *
 * Key invariants:
 *   - MERGE on stable business key (dataset_row_id else buildPipelineKey(source, hadith_no)).
 *   - NEVER on uuidv4(). NEVER writes scalar reliability/grade (G-1).
 *   - Tradition strings canonicalized on load (task 0.7 / FR-1.9).
 *   - Source.tradition comes from the validated row and is registry-checked.
 *   - Tombstone semantics applied on supersession (via tombstone.ts).
 *   - INGESTED_IN edge written to active DatasetVersion.
 *
 * FR-1.1, FR-1.10, NFR-2
 */

import { randomUUID } from 'crypto';
import { runWrite } from '../../../lib/db/neo4j';
import { mergeNodeByKey, buildPipelineKey } from '../../../lib/db/neo4j-helpers';
import { CANONICAL_SOURCES } from '../../../lib/constants/sources';
import type { UnifiedRow, LoadContext, Tradition } from './io';
import { canonicalizeTradition, isSupportedTradition } from './io';
import { linkHadithToDatasetVersion } from './dataset-version';
import { tombstone } from './tombstone';

// ─── Source tradition lookup ──────────────────────────────────────────────────

/** Track unknown sources so the warning fires only once per distinct name. */
const _unknownSourcesWarned = new Set<string>();
const _sourceTraditionsSeen = new Map<string, Tradition>();

/** Validate one source/tradition pair without inventing a default tradition. */
function getTraditionForSource(sourceName: string, rawRowTradition: string): Tradition {
    if (!sourceName.trim()) throw new Error('[load-hadith] Source name must be nonblank');
    if (!isSupportedTradition(rawRowTradition)) {
        throw new Error(`[load-hadith] Unsupported row tradition: ${rawRowTradition || '<blank>'}`);
    }
    const rowTradition = canonicalizeTradition(rawRowTradition);
    const observedTradition = _sourceTraditionsSeen.get(sourceName);
    if (observedTradition && observedTradition !== rowTradition) {
        throw new Error(
            `[load-hadith] Source "${sourceName}" has conflicting traditions ` +
            `${observedTradition} and ${rowTradition}`,
        );
    }

    const registered = Object.values(CANONICAL_SOURCES).find(
        (entry) => entry.canonical === sourceName,
    );
    if (registered && registered.tradition !== rowTradition) {
        throw new Error(
            `[load-hadith] Source registry mismatch for "${sourceName}": ` +
            `row=${rowTradition}, registry=${registered.tradition}`,
        );
    }
    _sourceTraditionsSeen.set(sourceName, rowTradition);

    if (!_unknownSourcesWarned.has(sourceName)) {
        if (!registered) {
            _unknownSourcesWarned.add(sourceName);
            console.warn(
                `[load-hadith] WARNING: Unknown source "${sourceName}"; ` +
                `using validated row tradition ${rowTradition}`,
            );
        }
    }
    return rowTradition;
}

// ─── Merge Source node ────────────────────────────────────────────────────────

async function mergeSourceNode(sourceName: string, tradition: string): Promise<void> {
    const cypher = `
        MERGE (s:Source { name: $name })
        ON CREATE SET
            s.id = $id,
            s.created_at = datetime(),
            s.tradition = $tradition
        ON MATCH SET
            s.tradition = $tradition,
            s.updated_at = datetime()
    `;
    await runWrite(cypher, {
        name: sourceName,
        id: randomUUID(),
        tradition,
    });
}

// ─── loadHadith ───────────────────────────────────────────────────────────────

/**
 * Idempotently MERGE a :Hadith node from a UnifiedRow.
 *
 * Business key resolution:
 *   1. If dataset_row_id is present (numeric), MERGE on dataset_row_id.
 *   2. Otherwise MERGE on pipeline_key = buildPipelineKey(source, hadith_no).
 *
 * Tradition is always written as the canonicalized form (Imami, Zaydi, etc.)
 * and cross-checked against CANONICAL_SOURCES for the source's tradition.
 *
 * INVARIANT: no scalar `reliability`, `grade`, or `assessment` property is
 * written to the :Hadith node (G-1). Grades → assessment.ts.
 */
export async function loadHadith(row: UnifiedRow, ctx: LoadContext): Promise<void> {
    const { dvId, log } = ctx;

    // Determine stable business key.
    const hasRowId = row.dataset_row_id !== null;
    const hadithKey: string | number = hasRowId
        ? row.dataset_row_id!
        : buildPipelineKey(row.source, row.hadith_no);
    const keyProp: 'dataset_row_id' | 'pipeline_key' = hasRowId
        ? 'dataset_row_id'
        : 'pipeline_key';

    // Tradition is explicit in the row and cross-checked with source metadata.
    const sourceTradition = getTraditionForSource(row.source, row.tradition);
    const tradition = sourceTradition;

    // Mutable props (always refreshed on MATCH).
    // NOTE: grade-related fields (grade_value, grade_tradition, grade_source, gradings_full)
    // are intentionally excluded — they belong on Assessment nodes (H2/G-1 invariant).
    const mutableProps: Record<string, unknown> = {
        source: row.source,
        tradition,
        hadith_id: row.hadith_id,
        hadith_no: row.hadith_no,
        volume: row.volume,
        chapter: row.chapter,
        chapter_no: row.chapter_no,
        category: row.category,
        text_ar: row.text_ar,
        text_en: row.text_en,
        matn_ar: row.matn_ar,
        matn_en: row.matn_en,
        sanad: row.sanad,
        sanad_confidence: row.sanad_confidence,
        school: row.school,
        chain_type: row.chain_type,
        attributed_to: row.attributed_to,
        narration_level: row.narration_level,
        url: row.url,
        page_ref: row.page_ref,
    };

    // Create-only props.
    const createProps: Record<string, unknown> = {
        id: randomUUID(),
        ...(hasRowId ? { dataset_row_id: row.dataset_row_id! } : {}),
        pipeline_key: buildPipelineKey(row.source, row.hadith_no),
    };

    try {
        const result = await mergeNodeByKey({
            label: 'Hadith',
            keyProp,
            keyValue: hadithKey,
            createProps,
            mutableProps,
        });

        // Handle tombstone supersession: if an older duplicate exists on the
        // OTHER key, tombstone it pointing at the active dvId.
        // (Active deduplication is workstream D's ER job — here we only handle
        //  the case where dataset_row_id exists but a pipeline_key duplicate was
        //  written in a prior run without dataset_row_id.)
        if (hasRowId) {
            await tombstoneOrphanPipelineKey(row, dvId);
        }

        // Write INGESTED_IN edge.
        await linkHadithToDatasetVersion(hadithKey, keyProp, dvId);

        // Ensure Source node exists with correct tradition.
        await mergeSourceNode(row.source, sourceTradition);

        // Link Hadith → Source (idempotent).
        const linkCypher = `
            MATCH (h:Hadith { ${keyProp}: $hadithKey })
            MATCH (s:Source { name: $sourceName })
            MERGE (h)-[:FROM_SOURCE]->(s)
        `;
        await runWrite(linkCypher, { hadithKey, sourceName: row.source });

        log({
            action: result.created ? 'created' : 'matched',
            entity: 'Hadith',
            key: hadithKey,
            keyProp,
            tradition,
            dvId,
        });
    } catch (err) {
        log({
            action: 'error',
            entity: 'Hadith',
            key: hadithKey,
            keyProp,
            error: String(err),
        });
        throw err;
    }
}

// ─── Orphan pipeline_key tombstoning ─────────────────────────────────────────

/**
 * If a :Hadith was previously merged on pipeline_key (no dataset_row_id) but
 * now the row has a dataset_row_id, any orphan node with the same pipeline_key
 * but no dataset_row_id should be tombstoned and superseded by the current dvId.
 *
 * This is a soft deduplication — we never delete (NFR-2).
 */
async function tombstoneOrphanPipelineKey(row: UnifiedRow, dvId: string): Promise<void> {
    const pipelineKey = buildPipelineKey(row.source, row.hadith_no);

    // Find any node keyed on pipeline_key that doesn't have dataset_row_id set.
    const findCypher = `
        MATCH (h:Hadith { pipeline_key: $pipelineKey })
        WHERE h.dataset_row_id IS NULL AND NOT h.tombstoned = true
        RETURN h.id AS id
    `;
    const orphans = await runWrite<{ id: string }>(findCypher, { pipelineKey });

    for (const orphan of orphans) {
        await tombstone(orphan.id, 'Hadith', dvId);
    }
}
