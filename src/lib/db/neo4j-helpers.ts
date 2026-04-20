/**
 * neo4j-helpers.ts
 *
 * Generic MERGE helpers that encode the project's idempotency conventions:
 *
 *   1. Every node has a `:id` UUID constraint AND a business-key MERGE anchor.
 *   2. Composite idempotency keys use `::` delimiter and UPPERCASE categorical fields.
 *   3. ON CREATE SET assigns `id` + `created_at` + immutable + initial mutable props.
 *   4. ON MATCH SET refreshes mutable props and always sets `updated_at`.
 *   5. The `created` return flag uses a sentinel on ON CREATE / ON MATCH — not
 *      a brittle `created_at = updated_at` expression (which is the bug in
 *      src/lib/comparative/neo4j-commit.ts:162 that this helper supersedes).
 *
 * These helpers are intended to replace the ad-hoc per-label merge functions
 * in neo4j-commit.ts (mergeTradition, mergeSourceText, mergeMotifTag) and to
 * provide the shape for all new scholarship-layer helpers (Scholar,
 * ScholarVerdict, Commentary, SchoolOfThought, Practice, etc.).
 */

import { randomUUID } from 'crypto';
import { runWrite } from './neo4j';

// ─── Types ────────────────────────────────────────────────────────────────────

/** Parameters passed straight to a Cypher query. */
type Props = Record<string, unknown>;

export interface MergeNodeInput {
    /** PascalCase node label, e.g. "SchoolOfThought". */
    label: string;
    /**
     * Name of the business-key property to MERGE on, e.g. "name" or
     * "pipeline_key". Must be one of the uniqueness-constrained properties.
     */
    keyProp: string;
    /** Value of the business-key property. */
    keyValue: string | number;
    /**
     * Properties to set ON CREATE. `id` is auto-populated if not present.
     * `created_at = datetime()` is always added.
     */
    createProps?: Props;
    /**
     * Properties to set on BOTH create and match (i.e. always-refreshed fields).
     * `updated_at = datetime()` is always added on ON MATCH.
     */
    mutableProps?: Props;
}

export interface MergeNodeResult {
    id: string;
    created: boolean;
}

// ─── Cypher building ──────────────────────────────────────────────────────────

function buildSetClause(propNames: string[], paramPrefix: string): string {
    if (propNames.length === 0) return '';
    return propNames.map((p) => `n.${p} = $${paramPrefix}_${p}`).join(', ');
}

function prefixParams(props: Props, paramPrefix: string): Record<string, unknown> {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(props)) {
        out[`${paramPrefix}_${k}`] = v;
    }
    return out;
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Idempotently MERGE a node by business key, returning its `id` and whether
 * it was freshly created on this call.
 *
 * Design notes:
 * - Uses a `_merge_sentinel` property that is set to `true` ON CREATE and
 *   `false` ON MATCH, read in the same transaction, then REMOVEd. This is
 *   the correct pattern for "was this just created?" in Neo4j MERGE.
 * - Calls `runWrite` (which uses `executeWrite`) so retries are safe under
 *   transient connection errors.
 */
export async function mergeNodeByKey(
    input: MergeNodeInput
): Promise<MergeNodeResult> {
    const { label, keyProp, keyValue } = input;
    const createProps = { ...(input.createProps ?? {}) };
    const mutableProps = { ...(input.mutableProps ?? {}) };

    // Auto-populate id on create if not provided.
    if (!('id' in createProps)) {
        createProps.id = randomUUID();
    }

    const createPropNames = Object.keys(createProps);
    const mutablePropNames = Object.keys(mutableProps);

    // Avoid collision: mutableProps takes precedence on ON MATCH, so we only
    // emit ON CREATE SET for fields not also in mutableProps.
    const createOnlyNames = createPropNames.filter((p) => !mutablePropNames.includes(p));

    const onCreateSets: string[] = [];
    if (createOnlyNames.length > 0) {
        onCreateSets.push(buildSetClause(createOnlyNames, 'create'));
    }
    onCreateSets.push('n.created_at = datetime()');
    onCreateSets.push('n._merge_sentinel = true');
    if (mutablePropNames.length > 0) {
        onCreateSets.push(buildSetClause(mutablePropNames, 'mut'));
    }

    const onMatchSets: string[] = ['n._merge_sentinel = false'];
    if (mutablePropNames.length > 0) {
        onMatchSets.push(buildSetClause(mutablePropNames, 'mut'));
        onMatchSets.push('n.updated_at = datetime()');
    }

    const cypher = `
        MERGE (n:${label} {${keyProp}: $keyValue})
        ON CREATE SET ${onCreateSets.join(', ')}
        ON MATCH SET ${onMatchSets.join(', ')}
        WITH n, n._merge_sentinel AS created
        REMOVE n._merge_sentinel
        RETURN n.id AS id, created
    `;

    const params: Record<string, unknown> = {
        keyValue,
        ...prefixParams(
            Object.fromEntries(createOnlyNames.map((k) => [k, createProps[k]])),
            'create'
        ),
        ...prefixParams(mutableProps, 'mut'),
    };

    const rows = await runWrite<{ id: string; created: boolean }>(cypher, params);
    if (rows.length === 0) {
        throw new Error(`mergeNodeByKey(${label}, ${keyProp}=${keyValue}) returned no rows`);
    }
    return { id: rows[0].id, created: rows[0].created };
}

// ─── Edge helpers ─────────────────────────────────────────────────────────────

export interface MergeEdgeInput {
    fromLabel: string;
    fromKey: { prop: string; value: string | number };
    toLabel: string;
    toKey: { prop: string; value: string | number };
    relType: string;
    /** Properties set on the relationship (ON CREATE only). */
    props?: Props;
}

/**
 * Idempotently MERGE a relationship between two nodes identified by business
 * keys. Properties are only set ON CREATE (edges are immutable unless you
 * have a specific reason to update them — e.g. ACCEPTED_IN.status may need
 * a separate `updateEdgeProps` helper later).
 */
export async function mergeEdge(input: MergeEdgeInput): Promise<void> {
    const { fromLabel, fromKey, toLabel, toKey, relType } = input;
    const props = input.props ?? {};
    const propNames = Object.keys(props);

    const setClause =
        propNames.length > 0
            ? `ON CREATE SET ${propNames.map((p) => `r.${p} = $prop_${p}`).join(', ')}`
            : '';

    const cypher = `
        MATCH (a:${fromLabel} {${fromKey.prop}: $fromValue})
        MATCH (b:${toLabel} {${toKey.prop}: $toValue})
        MERGE (a)-[r:${relType}]->(b)
        ${setClause}
    `;

    const params: Record<string, unknown> = {
        fromValue: fromKey.value,
        toValue: toKey.value,
        ...prefixParams(props, 'prop'),
    };

    await runWrite(cypher, params);
}

// ─── Composite idempotency key ────────────────────────────────────────────────

/**
 * Build a composite `pipeline_key` from parts, following the convention
 * established in src/lib/comparative/neo4j-commit.ts:120 — parts joined with
 * `::`, categorical strings should be upper-cased by the caller.
 *
 * Example:
 *   buildPipelineKey('musnad_0001', 'ZOROASTRIANISM', 'Avesta-Vendidad-5.1')
 *   -> 'musnad_0001::ZOROASTRIANISM::Avesta-Vendidad-5.1'
 */
export function buildPipelineKey(...parts: (string | number)[]): string {
    return parts.map((p) => String(p)).join('::');
}
