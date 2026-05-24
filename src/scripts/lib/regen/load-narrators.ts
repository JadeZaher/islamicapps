/**
 * load-narrators.ts — Bulk-MERGE :Narrator nodes from the rawis Map.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Worker H2
 *
 * Must be called ONCE at the start of a fullregen run (before any chain-loading
 * loop) so that load-chain.ts MATCH (n:Narrator { scholar_indx: ... }) resolves.
 *
 * Invariant G-1 (ABSOLUTE): `grade`, `reliability`, or any scalar verdict MUST
 * NOT appear on the :Narrator node. The raw CSV `grade` field is stashed as
 * `_raw_grade` (a breadcrumb — not an indexed verdict).
 *
 * TODO(follow-up): Fan-out `_raw_grade` into per-tradition :Assessment nodes
 *   using loadAssessment from ./assessment.ts once the tradition mapping for
 *   narrator reliability grades is finalised.
 */

import { randomUUID } from 'crypto';
import { runWrite } from '../../../lib/db/neo4j';
import { RawiRecord } from './io';

// ─── Constants ────────────────────────────────────────────────────────────────

/** Batch size kept small to stay under Neo4j transaction memory limits.
 *  The drain phase proved 200 is safe; use the same guard here. */
const BATCH_SIZE = 200;

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BulkLoadResult {
    created: number;
    matched: number;
    errors: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function chunkMap<K, V>(map: Map<K, V>, size: number): V[][] {
    const values = Array.from(map.values());
    const chunks: V[][] = [];
    for (let i = 0; i < values.length; i += size) {
        chunks.push(values.slice(i, i + size));
    }
    return chunks;
}

// ─── bulkLoadNarrators ────────────────────────────────────────────────────────

/**
 * Bulk-MERGE every rawi in the Map as a :Narrator node.
 *
 * @param rawis  Full rawis Map as returned by readAllRawis().
 * @param dvId   Active DatasetVersion.id — written as `source` for G-4 provenance.
 */
export async function bulkLoadNarrators(
    rawis: Map<number, RawiRecord>,
    dvId: string,
): Promise<BulkLoadResult> {
    const result: BulkLoadResult = { created: 0, matched: 0, errors: 0 };

    const chunks = chunkMap(rawis, BATCH_SIZE);
    const totalBatches = chunks.length;

    console.log(`[load-narrators] Starting bulk MERGE: ${rawis.size} rawis in ${totalBatches} batches (size=${BATCH_SIZE})`);

    for (let batchIdx = 0; batchIdx < chunks.length; batchIdx++) {
        const batch = chunks[batchIdx];

        // Shape each rawi into a plain params object (Neo4j driver serialises this).
        const rows = batch.map((r) => ({
            scholar_indx: r.scholar_indx,
            name: r.name,
            name_english: r.name_english,
            name_arabic: r.name_arabic,
            // _raw_grade: breadcrumb only — not a verdict (G-1 compliant).
            _raw_grade: r.grade ?? null,
            bio: r.bio ?? null,
            death_date_hijri: r.death_date_hijri ?? null,
            death_date_gregorian: r.death_date_gregorian ?? null,
            geographic_region: r.geographic_region ?? null,
            tabaqah: r.tabaqah ?? null,
            source: dvId,
        }));

        // Pre-count existing narrators in this batch to derive created vs matched.
        const existingKeys: number[] = await runWrite<{ scholar_indx: number }>(
            `UNWIND $keys AS k
             MATCH (n:Narrator { scholar_indx: k })
             RETURN n.scholar_indx AS scholar_indx`,
            { keys: rows.map((r) => r.scholar_indx) },
        ).then((records) => records.map((rec) => rec.scholar_indx)).catch(() => []);

        const existingSet = new Set(existingKeys);

        try {
            const cypher = `
                UNWIND $rows AS row
                MERGE (n:Narrator { scholar_indx: row.scholar_indx })
                ON CREATE SET
                    n.id               = row.id,
                    n.name             = row.name,
                    n.name_english     = row.name_english,
                    n.name_arabic      = row.name_arabic,
                    n._raw_grade       = row._raw_grade,
                    n.bio              = row.bio,
                    n.death_date_hijri = row.death_date_hijri,
                    n.death_date_gregorian = row.death_date_gregorian,
                    n.geographic_region = row.geographic_region,
                    n.tabaqah          = row.tabaqah,
                    n.source           = row.source,
                    n.created_at       = datetime()
                ON MATCH SET
                    n.name             = row.name,
                    n.name_english     = row.name_english,
                    n.name_arabic      = row.name_arabic,
                    n._raw_grade       = row._raw_grade,
                    n.bio              = row.bio,
                    n.death_date_hijri = row.death_date_hijri,
                    n.death_date_gregorian = row.death_date_gregorian,
                    n.geographic_region = row.geographic_region,
                    n.tabaqah          = row.tabaqah,
                    n.source           = row.source,
                    n.updated_at       = datetime()
                RETURN n.scholar_indx AS scholar_indx
            `;

            // Inject uuid per row at call time (not inside Cypher — APOC not guaranteed).
            const rowsWithUuid = rows.map((r) => ({ ...r, id: randomUUID() }));

            await runWrite(cypher, { rows: rowsWithUuid });

            for (const r of rows) {
                if (existingSet.has(r.scholar_indx)) {
                    result.matched++;
                } else {
                    result.created++;
                }
            }
        } catch (err) {
            console.error(`[load-narrators] Batch ${batchIdx + 1}/${totalBatches} failed:`, err);
            result.errors += batch.length;
        }

        if ((batchIdx + 1) % 10 === 0 || batchIdx + 1 === totalBatches) {
            console.log(
                `[load-narrators] Batch ${batchIdx + 1}/${totalBatches} done | ` +
                `created=${result.created} matched=${result.matched} errors=${result.errors}`,
            );
        }
    }

    console.log(
        `[load-narrators] Complete: created=${result.created} matched=${result.matched} errors=${result.errors}`,
    );
    return result;
}
