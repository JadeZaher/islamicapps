import 'dotenv/config';
import { runQuery } from '@/lib/db/neo4j';

(async () => {
    const sources = ['Al-Kāfi', 'Musnad al-Imam Zayd ibn Ali', "Jami' al-Tirmidhi", 'Sahih Bukhari',
                     'Sahih Muslim', 'al-Jami al-Sahih (Musnad al-Rabi ibn Habib)',
                     'Man Lā Yaḥḍuruh al-Faqīh'];
    console.log('Per-source chain stats (live):');
    for (const src of sources) {
        const r = await runQuery<{ avg_narr: number; with_chain: number; total: number }>(
            `MATCH (h:Hadith {source: $src})
             OPTIONAL MATCH (h)-[:HAS_CHAIN]->(c:Chain)-[:INCLUDES]->(n:Narrator)
             WITH h, count(DISTINCT n) AS n_count
             RETURN avg(CASE WHEN n_count > 0 THEN n_count ELSE null END) AS avg_narr,
                    sum(CASE WHEN n_count > 0 THEN 1 ELSE 0 END) AS with_chain,
                    count(h) AS total`,
            { src }
        );
        const row = r[0];
        const avgN = typeof row.avg_narr === 'number' ? row.avg_narr.toFixed(2) : 'N/A';
        console.log(`  ${src.padEnd(45)} | total=${String(row.total).padStart(5)} | with_chain=${String(row.with_chain).padStart(5)} | avg_n=${avgN}`);
    }
    process.exit(0);
})();
