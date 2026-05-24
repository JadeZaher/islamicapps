/**
 * tombstone.ts — Soft-delete utility for the regen pipeline.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   tombstone(nodeId, label, dvId) → Promise<void>
 *   tombstoneByKey(label, keyProp, keyValue, dvId) → Promise<void>
 *   excludeTombstoned() → string  (Cypher WHERE fragment)
 *   isTombstoned(properties) → boolean  (JS-side filter)
 *
 * NFR-2 / standing no-delete directive (feedback_no_delete_backup.md):
 *   NEVER use DETACH DELETE. Instead set:
 *     n.tombstoned = true
 *     n.superseded_by = <DatasetVersion.id>
 *     n.tombstoned_at = datetime()
 *
 * All projections that should exclude soft-deleted nodes MUST add
 * `WHERE NOT n.tombstoned = true` (use excludeTombstoned() helper).
 */

import { runWrite } from '../../../lib/db/neo4j';

// ─── tombstone (by Neo4j internal uuid-typed id) ─────────────────────────────

/**
 * Soft-delete a node by its application-level `id` property (uuid string).
 * The node remains in the graph but is excluded from live projections.
 *
 * @param nodeId   The node's `id` property value (NOT Neo4j element id).
 * @param label    PascalCase node label (for logging clarity only — Cypher uses `id`).
 * @param dvId     DatasetVersion.id that supersedes this node.
 */
export async function tombstone(nodeId: string, label: string, dvId: string): Promise<void> {
    const cypher = `
        MATCH (n { id: $nodeId })
        SET
            n.tombstoned = true,
            n.superseded_by = $dvId,
            n.tombstoned_at = datetime()
    `;
    await runWrite(cypher, { nodeId, dvId });
}

// ─── tombstoneByKey ───────────────────────────────────────────────────────────

/**
 * Soft-delete a node identified by a business key (e.g. pipeline_key, scholar_indx).
 * Safer than tombstone() when you have the biz key but not the internal uuid.
 *
 * @param label      PascalCase label, e.g. 'Hadith'
 * @param keyProp    Property name, e.g. 'pipeline_key'
 * @param keyValue   Property value
 * @param dvId       Superseding DatasetVersion.id
 */
export async function tombstoneByKey(
    label: string,
    keyProp: string,
    keyValue: string | number,
    dvId: string
): Promise<void> {
    const cypher = `
        MATCH (n:${label} { ${keyProp}: $keyValue })
        SET
            n.tombstoned = true,
            n.superseded_by = $dvId,
            n.tombstoned_at = datetime()
    `;
    await runWrite(cypher, { keyValue, dvId });
}

// ─── excludeTombstoned ────────────────────────────────────────────────────────

/**
 * Returns a Cypher WHERE clause fragment that filters out tombstoned nodes.
 * Usage: `MATCH (n:Narrator) WHERE ${excludeTombstoned()} RETURN n`
 * The alias `n` is assumed; pass `alias` to override.
 */
export function excludeTombstoned(alias = 'n'): string {
    return `NOT ${alias}.tombstoned = true`;
}

// ─── isTombstoned (JS-side filter) ───────────────────────────────────────────

/**
 * JS-side predicate for filtering tombstoned nodes out of in-memory arrays.
 * Use this when you already have the node properties in JS memory.
 */
export function isTombstoned(properties: Record<string, unknown>): boolean {
    return properties['tombstoned'] === true;
}
