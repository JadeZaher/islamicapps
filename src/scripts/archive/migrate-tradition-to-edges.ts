// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * migrate-tradition-to-edges.ts
 *
 * One-shot, idempotent migration that converts the `.tradition` string
 * property on Hadith, Narrator, and Source nodes into first-class edges
 * targeting :SchoolOfThought nodes.
 *
 *   Before: (:Hadith {tradition: 'Ibadi'})
 *   After:  (:Hadith)-[:IN_SCHOOL]->(:SchoolOfThought {name: 'Ibadi'})
 *
 * Mappings (by inspection of the current DB state):
 *   Hadith.tradition = 'Ibadi'  → IN_SCHOOL → Ibadi
 *   Hadith.tradition = null     → IN_SCHOOL → Sunni  (all UUID-id hadiths
 *                                  came from import-datasets.ts which is
 *                                  Sunni-focused)
 *   Narrator.tradition          → ACCEPTED_IN {status: 'THIQA'} → School
 *                                 (ACCEPTED_IN carries a per-school
 *                                 reputation; until a real rijal pass runs
 *                                 we default to THIQA, matching the value
 *                                 that import-musnad.ts writes today)
 *   Source.tradition            → CANON_OF → School
 *
 * Handles the legacy comma-delimited multi-tradition string
 * (import-musnad.ts:300-302) by splitting on commas and creating one
 * ACCEPTED_IN edge per school.
 *
 * This migration does NOT delete the `.tradition` string property on the
 * initial run — the property stays as a sentinel until the Phase 4
 * import-musnad.ts refactor lands and we want to deprecate it. Pass
 * `--cleanup` to also strip the property after migration succeeds.
 *
 * Usage:
 *   tsx src/scripts/migrate-tradition-to-edges.ts
 *   tsx src/scripts/migrate-tradition-to-edges.ts --cleanup
 */

import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

const DEFAULT_SUNNI_IF_NULL = true; // all null-tradition Hadiths/Narrators/Sources default to Sunni

type Plan = {
    label: 'Hadith' | 'Narrator' | 'Source';
    relType: 'IN_SCHOOL' | 'ACCEPTED_IN' | 'CANON_OF';
    /**
     * Optional properties set on the edge ON CREATE (e.g. {status: 'THIQA'}
     * for ACCEPTED_IN). Applied as `$prop_X` params.
     */
    edgeProps?: Record<string, unknown>;
};

const PLANS: Plan[] = [
    { label: 'Hadith', relType: 'IN_SCHOOL' },
    { label: 'Narrator', relType: 'ACCEPTED_IN', edgeProps: { status: 'THIQA', source: 'legacy_tradition_string' } },
    { label: 'Source', relType: 'CANON_OF' },
];

/** Split a legacy tradition string (may contain commas) into a clean list. */
function splitTradition(raw: string | null | undefined): string[] {
    if (!raw) return DEFAULT_SUNNI_IF_NULL ? ['Sunni'] : [];
    const parts = raw
        .split(',')
        .map((p) => p.trim())
        .filter((p) => p.length > 0);
    if (parts.length === 0) return DEFAULT_SUNNI_IF_NULL ? ['Sunni'] : [];
    return parts;
}

async function migratePlan(plan: Plan): Promise<{ nodes: number; edges: number }> {
    console.log(`\n📦 Migrating ${plan.label}.tradition -> [:${plan.relType}]`);

    // Group nodes by tradition value
    const groups = await runQuery<{ tradition: string | null; count: any }>(
        `MATCH (n:${plan.label})
         RETURN n.tradition AS tradition, count(*) AS count
         ORDER BY count DESC`
    );

    let totalNodes = 0;
    let totalEdges = 0;

    for (const g of groups) {
        const schools = splitTradition(g.tradition);
        if (schools.length === 0) {
            console.log(`  Skipping ${Number(g.count)} nodes with tradition=null (DEFAULT_SUNNI_IF_NULL=false)`);
            continue;
        }

        for (const schoolName of schools) {
            // Verify school exists
            const schoolCheck = await runQuery<{ id: string }>(
                `MATCH (s:SchoolOfThought {name: $name}) RETURN s.id AS id`,
                { name: schoolName }
            );
            if (schoolCheck.length === 0) {
                console.warn(`  ⚠️  SchoolOfThought "${schoolName}" not found in DB. Skipping.`);
                continue;
            }

            // Build the MERGE statement. For null tradition we match on IS NULL,
            // for string tradition we match on equality (or CONTAINS for comma hack).
            const matchClause =
                g.tradition === null
                    ? `n.tradition IS NULL`
                    : `n.tradition = $tradition`;

            const edgePropsSet =
                plan.edgeProps && Object.keys(plan.edgeProps).length > 0
                    ? `ON CREATE SET ${Object.keys(plan.edgeProps)
                          .map((k) => `r.${k} = $prop_${k}`)
                          .join(', ')}`
                    : '';

            // The params include tradition (if non-null) + edge props.
            const params: Record<string, unknown> = { schoolName };
            if (g.tradition !== null) params.tradition = g.tradition;
            if (plan.edgeProps) {
                for (const [k, v] of Object.entries(plan.edgeProps)) {
                    params[`prop_${k}`] = v;
                }
            }

            const cypher = `
                MATCH (n:${plan.label})
                WHERE ${matchClause}
                MATCH (s:SchoolOfThought {name: $schoolName})
                MERGE (n)-[r:${plan.relType}]->(s)
                ${edgePropsSet}
                RETURN count(n) AS nodes
            `;

            const result = await runWrite<{ nodes: any }>(cypher, params);
            const nodes = Number(result[0]?.nodes ?? 0);
            totalNodes += nodes;
            totalEdges += nodes;
            console.log(
                `  ${String(nodes).padStart(6)} ${plan.label} nodes (tradition="${g.tradition ?? 'null'}") -> ${schoolName}`
            );
        }
    }

    return { nodes: totalNodes, edges: totalEdges };
}

async function verify(): Promise<void> {
    console.log('\n🔍 Verifying migration...');

    // Hadith coverage
    const hadithCoverage = await runQuery<{ total: any; with_edge: any }>(
        `MATCH (h:Hadith)
         WITH count(h) AS total,
              count{ (h)-[:IN_SCHOOL]->(:SchoolOfThought) } AS with_edge_raw
         RETURN total, with_edge_raw AS with_edge`
    );
    if (hadithCoverage[0]) {
        const t = Number(hadithCoverage[0].total);
        const e = Number(hadithCoverage[0].with_edge);
        console.log(`  Hadith   : ${e}/${t} nodes have [:IN_SCHOOL] edge`);
        if (e !== t) console.warn(`  ⚠️  ${t - e} Hadith nodes missing IN_SCHOOL edge`);
    }

    // Narrator coverage
    const narratorCoverage = await runQuery<{ total: any; with_edge: any }>(
        `MATCH (n:Narrator)
         WITH count(n) AS total,
              count{ (n)-[:ACCEPTED_IN]->(:SchoolOfThought) } AS with_edge_raw
         RETURN total, with_edge_raw AS with_edge`
    );
    if (narratorCoverage[0]) {
        const t = Number(narratorCoverage[0].total);
        const e = Number(narratorCoverage[0].with_edge);
        console.log(`  Narrator : ${e}/${t} nodes have [:ACCEPTED_IN] edge`);
        if (e !== t) console.warn(`  ⚠️  ${t - e} Narrator nodes missing ACCEPTED_IN edge`);
    }

    // Source coverage
    const sourceCoverage = await runQuery<{ total: any; with_edge: any }>(
        `MATCH (s:Source)
         WITH count(s) AS total,
              count{ (s)-[:CANON_OF]->(:SchoolOfThought) } AS with_edge_raw
         RETURN total, with_edge_raw AS with_edge`
    );
    if (sourceCoverage[0]) {
        const t = Number(sourceCoverage[0].total);
        const e = Number(sourceCoverage[0].with_edge);
        console.log(`  Source   : ${e}/${t} nodes have [:CANON_OF] edge`);
        if (e !== t) console.warn(`  ⚠️  ${t - e} Source nodes missing CANON_OF edge`);
    }

    // Multi-tradition narrators sanity check (comma hack)
    const multiTrad = await runQuery<{ count: any }>(
        `MATCH (n:Narrator)-[:ACCEPTED_IN]->(s:SchoolOfThought)
         WITH n, count(s) AS schools
         WHERE schools > 1
         RETURN count(n) AS count`
    );
    const multi = Number(multiTrad[0]?.count ?? 0);
    console.log(`  Multi-school narrators (ACCEPTED_IN > 1 school): ${multi}`);
}

async function cleanup(): Promise<void> {
    console.log('\n🧹 --cleanup: removing .tradition string properties...');

    for (const plan of PLANS) {
        const result = await runWrite<{ affected: any }>(
            `MATCH (n:${plan.label}) WHERE n.tradition IS NOT NULL
             REMOVE n.tradition
             RETURN count(n) AS affected`
        );
        console.log(`  Removed .tradition from ${Number(result[0]?.affected ?? 0)} ${plan.label} nodes`);
    }
}

async function main() {
    const args = process.argv.slice(2);
    const shouldCleanup = args.includes('--cleanup');

    console.log('🔄 Tradition string → edge migration');
    console.log('====================================');

    try {
        let grandTotal = 0;
        for (const plan of PLANS) {
            const { nodes } = await migratePlan(plan);
            grandTotal += nodes;
        }
        console.log(`\n✅ Migration applied to ${grandTotal.toLocaleString()} nodes.`);

        await verify();

        if (shouldCleanup) {
            await cleanup();
            console.log('\n✅ Cleanup complete.');
        } else {
            console.log(
                '\n💡 Run with --cleanup to remove the .tradition string property. Current run left it in place as a sentinel.'
            );
        }
    } catch (err) {
        console.error('❌ Migration failed:', err);
        process.exit(1);
    } finally {
        await closeDriver();
    }
}

main();
