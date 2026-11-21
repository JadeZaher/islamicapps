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
const MISSING_OPTIONAL_VALUES = new Set(['', 'na', 'n/a', 'null', 'none', 'nan', 'unknown', '-']);
const OPTIONAL_STRING_PROPS = [
    'name_english',
    'name_arabic',
    '_raw_grade',
    'bio',
    'birth_date_hijri_raw',
    'birth_date_gregorian_raw',
    'birth_date_source_text',
    'birth_place',
    'death_date_hijri_raw',
    'death_date_gregorian_raw',
    'death_date_source_text',
    'death_place',
    'death_reason',
    'geographic_region',
    'tabaqah',
] as const;
const OPTIONAL_NUMBER_PROPS = [
    'birth_date_hijri',
    'birth_date_gregorian',
    'death_date_hijri',
    'death_date_gregorian',
] as const;

// See AGENTS.md: base imports fill gaps but never arbitrate scalar claims.
const FILL_MISSING_OPTIONAL_ASSIGNMENTS = [
    ...OPTIONAL_STRING_PROPS.map((prop) =>
        `n.${prop} = CASE
            WHEN n.${prop} IS NULL OR trim(toString(n.${prop})) = ''
            THEN coalesce(row.optional_props.${prop}, n.${prop})
            ELSE n.${prop}
         END`,
    ),
    ...OPTIONAL_NUMBER_PROPS.map((prop) =>
        `n.${prop} = coalesce(n.${prop}, row.optional_props.${prop})`,
    ),
].join(',\n                    ');

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BulkLoadResult {
    created: number;
    matched: number;
    errors: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function* chunkMap<K, V>(map: Map<K, V>, size: number): Iterable<V[]> {
    let chunk: V[] = [];
    for (const value of map.values()) {
        chunk.push(value);
        if (chunk.length === size) {
            yield chunk;
            chunk = [];
        }
    }
    if (chunk.length > 0) yield chunk;
}

/** Build a sparse property map so absent CSV columns never erase enrichment. */
export function buildNarratorOptionalProps(rawi: RawiRecord): Record<string, string | number> {
    const candidates: Record<string, string | number | null> = {
        name_english: rawi.name_english,
        name_arabic: rawi.name_arabic,
        _raw_grade: rawi.grade,
        bio: rawi.bio,
        birth_date_hijri: rawi.birth_date_hijri,
        birth_date_hijri_raw: rawi.birth_date_hijri_raw,
        birth_date_gregorian: rawi.birth_date_gregorian,
        birth_date_gregorian_raw: rawi.birth_date_gregorian_raw,
        birth_date_source_text: rawi.birth_date_source_text,
        birth_place: rawi.birth_place,
        death_date_hijri: rawi.death_date_hijri,
        death_date_hijri_raw: rawi.death_date_hijri_raw,
        death_date_gregorian: rawi.death_date_gregorian,
        death_date_gregorian_raw: rawi.death_date_gregorian_raw,
        death_date_source_text: rawi.death_date_source_text,
        death_place: rawi.death_place,
        death_reason: rawi.death_reason,
        geographic_region: rawi.geographic_region,
        tabaqah: rawi.tabaqah,
    };
    const sparse: Record<string, string | number> = {};
    for (const [key, value] of Object.entries(candidates)) {
        if (value === null) continue;
        if (typeof value === 'string') {
            const normalized = value.trim().toLowerCase();
            if (MISSING_OPTIONAL_VALUES.has(normalized)) continue;
        }
        sparse[key] = value;
    }
    return sparse;
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

    const totalBatches = Math.ceil(rawis.size / BATCH_SIZE);

    console.log(`[load-narrators] Starting bulk MERGE: ${rawis.size} rawis in ${totalBatches} batches (size=${BATCH_SIZE})`);

    let batchIdx = 0;
    for (const batch of chunkMap(rawis, BATCH_SIZE)) {

        // Shape each rawi into a plain params object (Neo4j driver serialises this).
        const rows = batch.map((r) => ({
            scholar_indx: r.scholar_indx,
            name: r.name,
            optional_props: buildNarratorOptionalProps(r),
            source: dvId,
        }));

        try {
            const cypher = `
                UNWIND $rows AS row
                OPTIONAL MATCH (existing:Narrator { scholar_indx: row.scholar_indx })
                WITH row, existing IS NOT NULL AS existed
                MERGE (n:Narrator { scholar_indx: row.scholar_indx })
                ON CREATE SET
                    n.id               = row.id,
                    n.name             = row.name,
                    n.source           = row.source,
                    n.created_at       = datetime(),
                    n += row.optional_props
                ON MATCH SET
                    n.name             = CASE WHEN trim(row.name) <> '' THEN row.name ELSE n.name END,
                    n.source           = row.source,
                    n.updated_at       = datetime(),
                    ${FILL_MISSING_OPTIONAL_ASSIGNMENTS}
                RETURN
                    sum(CASE WHEN existed THEN 0 ELSE 1 END) AS created,
                    sum(CASE WHEN existed THEN 1 ELSE 0 END) AS matched
            `;

            // Inject uuid per row at call time (not inside Cypher — APOC not guaranteed).
            const rowsWithUuid = rows.map((r) => ({ ...r, id: randomUUID() }));

            const counts = await runWrite<{ created: number; matched: number }>(cypher, { rows: rowsWithUuid });
            result.created += counts[0]?.created ?? 0;
            result.matched += counts[0]?.matched ?? 0;
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
        batchIdx++;
    }

    console.log(
        `[load-narrators] Complete: created=${result.created} matched=${result.matched} errors=${result.errors}`,
    );
    return result;
}
