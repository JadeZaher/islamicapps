/**
 * dataset-version.ts — DatasetVersion provenance node management.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   mergeDatasetVersion(opts) → Promise<{ id: string }>
 *   linkHadithToDatasetVersion(hadithKey, keyProp, dvId) → Promise<void>
 *
 * FR-0.2 / FR-0.3 / tasks 0.10, 0.11
 *
 * Every regen run creates or merges a :DatasetVersion node that pins:
 *   - expected_record_count (69,368 or future total)
 *   - per-tradition sub-counts
 *   - content_hash (sha256 of input CSVs)
 *   - measured_unknown_fraction (was going NULL in legacy — this fixes it)
 *   - active = true (toggled off on supersession)
 *
 * INGESTED_IN edges from :Hadith to :DatasetVersion are written by
 * linkHadithToDatasetVersion(), called from loadHadith.
 */

import { randomUUID } from 'crypto';
import { runWrite } from '../../../lib/db/neo4j';

// ─── Public types ─────────────────────────────────────────────────────────────

export interface MergeDatasetVersionOpts {
    /** Total expected CSV records (canonical ground truth). */
    expectedRecordCount: number;
    /** Per-tradition record counts, e.g. { Sunni: 34441, Imami: 33225, ... } */
    perTraditionCounts: Record<string, number>;
    /** sha256 hex of the input CSV(s). */
    contentHash: string;
    /** Fraction of rows where attribution is unknown/unresolved (0–1). */
    measuredUnknownFraction?: number;
    /** Optional human-readable label for this version. */
    versionLabel?: string;
}

// ─── Attribution disclaimer (G-3) ────────────────────────────────────────────

const ATTRIBUTION_DISCLAIMER =
    'Graph metrics reflect kathrat al-riwāya (volume of transmission), NOT ʿadāla/ḍabṭ ' +
    'or any authenticity ḥukm. Algorithmic output is never a scholarly verdict.';

// ─── mergeDatasetVersion ──────────────────────────────────────────────────────

/**
 * Idempotently MERGE a :DatasetVersion node keyed on contentHash.
 * If a node with this hash already exists, it is matched (not duplicated).
 * Returns the node's stable id.
 *
 * Idempotency: keyed on contentHash so the same dataset file always maps to
 * the same version node. A different CSV produces a new DatasetVersion.
 */
export async function mergeDatasetVersion(
    opts: MergeDatasetVersionOpts
): Promise<{ id: string }> {
    const {
        expectedRecordCount,
        perTraditionCounts,
        contentHash,
        measuredUnknownFraction = 0,
        versionLabel = '',
    } = opts;

    const newId = randomUUID();
    const now = new Date().toISOString();

    // Build per-tradition props (flattened into top-level node properties).
    const traditionProps: Record<string, unknown> = {};
    for (const [tradition, count] of Object.entries(perTraditionCounts)) {
        // e.g. subcount_sunni, subcount_imami — lowercase, safe property names
        const key = `subcount_${tradition.toLowerCase().replace(/[^a-z]/g, '_')}`;
        traditionProps[key] = count;
    }

    // MERGE on contentHash (stable; same CSV = same version node).
    // ON CREATE: set id, all properties, active=true.
    // ON MATCH: refresh mutable fields (measured_unknown_fraction, updated_at).
    const cypher = `
        MERGE (dv:DatasetVersion { content_hash: $contentHash })
        ON CREATE SET
            dv.id = $id,
            dv.created_at = datetime(),
            dv.active = true,
            dv.expected_record_count = $expectedRecordCount,
            dv.measured_unknown_fraction = $measuredUnknownFraction,
            dv.attribution_disclaimer = $disclaimer,
            dv.version_label = $versionLabel,
            dv._per_tradition = $perTraditionJson
        ON MATCH SET
            dv.updated_at = datetime(),
            dv.measured_unknown_fraction = $measuredUnknownFraction,
            dv.active = true
        WITH dv
        RETURN dv.id AS id
    `;

    const params: Record<string, unknown> = {
        contentHash,
        id: newId,
        expectedRecordCount,
        measuredUnknownFraction,
        disclaimer: ATTRIBUTION_DISCLAIMER,
        versionLabel: versionLabel || `regen-${now.slice(0, 10)}`,
        perTraditionJson: JSON.stringify(perTraditionCounts),
    };

    const rows = await runWrite<{ id: string }>(cypher, params);
    if (!rows.length) {
        throw new Error('[dataset-version] mergeDatasetVersion returned no rows');
    }

    const dvId = rows[0].id;

    // Also write per-tradition flattened sub-count properties directly onto node.
    // Doing this in a second pass keeps the MERGE clause above clean.
    if (Object.keys(traditionProps).length > 0) {
        const setParts = Object.keys(traditionProps)
            .map((k) => `dv.${k} = $${k}`)
            .join(', ');
        const setCypher = `
            MATCH (dv:DatasetVersion { id: $dvId })
            SET ${setParts}
        `;
        await runWrite(setCypher, { dvId, ...traditionProps });
    }

    return { id: dvId };
}

// ─── linkHadithToDatasetVersion ───────────────────────────────────────────────

/**
 * Write an idempotent [:INGESTED_IN] edge from a :Hadith to a :DatasetVersion.
 * Called by loadHadith for every ingested row.
 *
 * @param hadithKey   Value of the business key property on :Hadith
 * @param keyProp     'dataset_row_id' | 'pipeline_key'
 * @param dvId        DatasetVersion.id (uuid)
 */
export async function linkHadithToDatasetVersion(
    hadithKey: string | number,
    keyProp: 'dataset_row_id' | 'pipeline_key',
    dvId: string
): Promise<void> {
    const cypher = `
        MATCH (h:Hadith { ${keyProp}: $hadithKey })
        MATCH (dv:DatasetVersion { id: $dvId })
        MERGE (h)-[:INGESTED_IN]->(dv)
    `;
    await runWrite(cypher, { hadithKey, dvId });
}

// ─── deactivateOtherVersions ──────────────────────────────────────────────────

/**
 * Mark all DatasetVersion nodes except the given id as active=false.
 * Called from mode-fullregen before loading a new version.
 * Never deletes — tombstone semantics are in tombstone.ts.
 */
export async function deactivateOtherVersions(activeDvId: string): Promise<void> {
    const cypher = `
        MATCH (dv:DatasetVersion)
        WHERE dv.id <> $activeDvId
        SET dv.active = false, dv.updated_at = datetime()
    `;
    await runWrite(cypher, { activeDvId });
}
