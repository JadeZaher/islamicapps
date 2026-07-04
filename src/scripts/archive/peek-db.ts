import { runQuery, closeDriver } from './src/lib/db/neo4j';
import { loadEnv } from './src/scripts/lib/env';
loadEnv();

async function main() {
    const [a] = await runQuery<{ n: number; r: number }>(
        `MATCH (n) WITH count(n) AS n OPTIONAL MATCH ()-[r]->() RETURN n, count(r) AS r`,
    );
    console.log('nodes:', a.n, 'rels:', a.r);

    const labels = await runQuery<{ label: string; c: number }>(
        `MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS c ORDER BY c DESC`,
    );
    console.log('\nby label:');
    labels.forEach((l) => console.log('  ', l.label, l.c));

    const rels = await runQuery<{ type: string; c: number }>(
        `MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS c ORDER BY c DESC`,
    );
    console.log('\nby rel:');
    rels.forEach((r) => console.log('  ', r.type, r.c));

    const [dv] = await runQuery<{ id: string; active: boolean; expected: number }>(
        `MATCH (dv:DatasetVersion) WHERE dv.active = true RETURN dv.id AS id, dv.active AS active, dv.expected_record_count AS expected LIMIT 1`,
    );
    console.log('\nactive DatasetVersion:', dv || 'NONE');

    await closeDriver();
}
main().catch(async (e) => {
    console.error(e);
    await closeDriver();
});
