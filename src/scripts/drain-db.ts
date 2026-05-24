import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';
import dotenv from 'dotenv';

dotenv.config({ path: '.env' });

// Lowered from 1,000 to 250 after v2 regen produced a denser graph (Narrators
// + INCLUDES + NARRATED_FROM edges) that exceeded the Neo4j 716 MiB per-tx
// memory cap with 1,000-node batches. 250 leaves comfortable headroom.
const BATCH_SIZE = 250;

async function main(): Promise<void> {
    const [{ nodes, rels }] = await runQuery<{ nodes: number; rels: number }>(`
        MATCH (n) WITH count(n) AS nodes
        OPTIONAL MATCH ()-[r]->() RETURN nodes, count(r) AS rels
    `);
    console.log(`[drain] start — nodes=${nodes} rels=${rels}`);

    if (nodes === 0) {
        console.log('[drain] empty — nothing to do');
        await closeDriver();
        return;
    }

    let total = 0;
    let round = 0;
    while (true) {
        round++;
        const [{ deleted }] = await runWrite<{ deleted: number }>(
            `MATCH (n) WITH n LIMIT ${BATCH_SIZE} DETACH DELETE n RETURN count(n) AS deleted`,
        );
        total += deleted;
        console.log(`[drain] round=${round} deleted=${deleted} total=${total}`);
        if (deleted === 0) break;
    }

    const [{ remaining }] = await runQuery<{ remaining: number }>(`MATCH (n) RETURN count(n) AS remaining`);
    console.log(`[drain] done — total_deleted=${total} remaining=${remaining}`);
    if (remaining !== 0) {
        console.error(`[drain] FAIL — ${remaining} nodes still present`);
        process.exitCode = 1;
    }
    await closeDriver();
}

main().catch(async (err) => {
    console.error('[drain] error:', err);
    await closeDriver();
    process.exitCode = 1;
});
