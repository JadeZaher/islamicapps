import { loadEnv } from './lib/env';
import { runQuery, closeDriver } from '../lib/db/neo4j';
loadEnv();

(async () => {
    try {
        console.log('\n=== Hadith IN_SCHOOL ===');
        const h = await runQuery<any>(
            `MATCH (h:Hadith)-[:IN_SCHOOL]->(s:SchoolOfThought)
             RETURN s.name AS school, count(*) AS n
             ORDER BY n DESC`
        );
        for (const r of h) console.log(`  ${r.school.padEnd(14)} ${Number(r.n)}`);

        console.log('\n=== Narrator ACCEPTED_IN ===');
        const n = await runQuery<any>(
            `MATCH (n:Narrator)-[:ACCEPTED_IN]->(s:SchoolOfThought)
             RETURN s.name AS school, count(*) AS c
             ORDER BY c DESC`
        );
        for (const r of n) console.log(`  ${r.school.padEnd(14)} ${Number(r.c)}`);

        console.log('\n=== Source CANON_OF ===');
        const sc = await runQuery<any>(
            `MATCH (s:Source)-[:CANON_OF]->(o:SchoolOfThought)
             RETURN o.name AS school, count(*) AS c
             ORDER BY c DESC`
        );
        for (const r of sc) console.log(`  ${r.school.padEnd(14)} ${Number(r.c)}`);

        console.log('\n=== Orphan counts ===');
        const orphH = await runQuery<any>(
            `MATCH (h:Hadith) WHERE NOT (h)-[:IN_SCHOOL]->(:SchoolOfThought) RETURN count(h) AS c`
        );
        console.log(`  Hadith without IN_SCHOOL   : ${Number(orphH[0].c)}`);

        const orphN = await runQuery<any>(
            `MATCH (n:Narrator) WHERE NOT (n)-[:ACCEPTED_IN]->(:SchoolOfThought) RETURN count(n) AS c`
        );
        console.log(`  Narrator without ACCEPTED_IN: ${Number(orphN[0].c)}`);

        const orphS = await runQuery<any>(
            `MATCH (s:Source) WHERE NOT (s)-[:CANON_OF]->(:SchoolOfThought) RETURN count(s) AS c`
        );
        console.log(`  Source without CANON_OF    : ${Number(orphS[0].c)}`);

        console.log('');
    } catch (err) {
        console.error('Verify failed:', err);
        process.exit(1);
    } finally {
        await closeDriver();
    }
})();
