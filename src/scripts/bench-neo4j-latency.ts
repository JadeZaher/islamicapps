/**
 * Quick latency/throughput probe against the live Railway Neo4j.
 * Run with: npx tsx src/scripts/probe-neo4j-perf.ts
 */
import 'dotenv/config';
import { runQuery, runWrite } from '@/lib/db/neo4j';

async function main() {
    console.log('=== Railway Neo4j perf probe ===\n');

    const t0 = Date.now();
    const r1 = await runQuery<{ n: number }>('MATCH (n) RETURN count(n) AS n');
    console.log(`count(all nodes) = ${r1[0]?.n?.toLocaleString()} in ${Date.now() - t0} ms`);

    const t1 = Date.now();
    const r2 = await runQuery<{ n: number }>('MATCH (h:Hadith) RETURN count(h) AS n');
    console.log(`count(:Hadith) = ${r2[0]?.n?.toLocaleString()} in ${Date.now() - t1} ms`);

    const t2 = Date.now();
    const r3 = await runQuery<{ n: number }>('MATCH ()-[r:INCLUDES]->() RETURN count(r) AS n');
    console.log(`count(:INCLUDES) = ${r3[0]?.n?.toLocaleString()} in ${Date.now() - t2} ms`);

    const t3 = Date.now();
    const r4 = await runQuery<{ n: number }>('MATCH ()-[r:NARRATED_FROM]->() RETURN count(r) AS n');
    console.log(`count(:NARRATED_FROM) = ${r4[0]?.n?.toLocaleString()} in ${Date.now() - t3} ms`);

    const t4 = Date.now();
    const r5 = await runQuery<{ n: number }>('MATCH (n:Narrator) RETURN count(n) AS n');
    console.log(`count(:Narrator) = ${r5[0]?.n?.toLocaleString()} in ${Date.now() - t4} ms`);

    const t5 = Date.now();
    const r6 = await runQuery<{ n: number }>('MATCH (c:Chain) RETURN count(c) AS n');
    console.log(`count(:Chain) = ${r6[0]?.n?.toLocaleString()} in ${Date.now() - t5} ms`);

    // The smoking-gun pattern: a single Narrator MATCH on scholar_indx
    console.log('\n--- Single MATCH (Narrator { scholar_indx: 5 }) x 10 sequential ---');
    for (let i = 0; i < 10; i++) {
        const t = Date.now();
        const r = await runQuery<{ name: string }>(
            'MATCH (n:Narrator { scholar_indx: $id }) RETURN n.name_english AS name',
            { id: 5 + i },
        );
        console.log(`  trial ${i+1}: ${Date.now() - t} ms (${r[0]?.name})`);
    }

    // UNWIND 100 narrator MATCHes — mirrors the fullregen INCLUDES batch
    console.log('\n--- UNWIND 100 narrator MATCHes ---');
    const t6 = Date.now();
    const ids = Array.from({ length: 100 }, (_, i) => 5 + i);
    await runQuery(
        'UNWIND $ids AS id MATCH (n:Narrator { scholar_indx: id }) RETURN count(n)',
        { ids },
    );
    console.log(`UNWIND 100 MATCH narrators: ${Date.now() - t6} ms`);

    process.exit(0);
}

main().catch((e) => {
    console.error('FATAL:', e);
    process.exit(1);
});
