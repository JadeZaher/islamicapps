import 'dotenv/config';
import { runQuery } from '@/lib/db/neo4j';

(async () => {
    const r = await runQuery<{ pos: number; name: string; idx: number }>(
        `MATCH (h:Hadith {id: $id})-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator)
         RETURN i.position AS pos, n.name_english AS name, n.scholar_indx AS idx
         ORDER BY pos`,
        { id: '626a2cb0-2268-4c79-9ffb-d9f6eaf42ec9' }
    );
    console.log(`Tirmidhi #1 chain (live, ${r.length} narrators):`);
    for (const row of r) console.log(`  pos=${row.pos} idx=${row.idx} ${row.name}`);
    process.exit(0);
})();
