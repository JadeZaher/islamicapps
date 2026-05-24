// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * fix-name-arabic.ts
 * Extract Arabic names from name_english field into name_arabic
 * for narrators where name_arabic is empty but name_english contains Arabic text.
 *
 * Usage: npx tsx src/scripts/fix-name-arabic.ts
 */
import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

const ARABIC_CHAR = /[\u0621-\u064A\u0671-\u06D3\u0640\u064B-\u0652\u0670]/;
const ARABIC_SEGMENT = /[\u0621-\u064A\u0671-\u06D3\u0640\u064B-\u0652\u0670\u200F\u200E\u0020\u00A0]+/g;

async function main() {
    console.log('=== Fix name_arabic: Extract from name_english ===\n');

    // Fetch all narrators without name_arabic
    const all = await runQuery<{ id: string; en: string }>(
        `MATCH (n:Narrator)
         WHERE (n.name_arabic IS NULL OR n.name_arabic = '')
           AND n.name_english IS NOT NULL
         RETURN n.id AS id, n.name_english AS en`
    );
    console.log(`Narrators without name_arabic: ${all.length}`);

    // Filter in JS — find those with Arabic characters in name_english
    const rows: Array<{ id: string; ar: string }> = [];
    for (const n of all) {
        if (!n.en || !ARABIC_CHAR.test(n.en)) continue;
        const matches = n.en.match(ARABIC_SEGMENT);
        if (matches) {
            const ar = matches.join(' ').replace(/\s+/g, ' ').trim();
            if (ar.length >= 3) {
                rows.push({ id: n.id, ar });
            }
        }
    }
    console.log(`With extractable Arabic text: ${rows.length}\n`);

    // Batch update
    const BS = 500;
    let done = 0;
    for (let i = 0; i < rows.length; i += BS) {
        const batch = rows.slice(i, i + BS);
        await runWrite(
            `UNWIND $rows AS row
             MATCH (n:Narrator {id: row.id})
             SET n.name_arabic = row.ar`,
            { rows: batch }
        );
        done += batch.length;
        console.log(`  Updated ${done}/${rows.length}`);
    }

    // Verify
    const v = await runQuery<{ total: number; with_ar: number }>(
        `MATCH (n:Narrator)
         RETURN count(n) AS total,
                count(CASE WHEN n.name_arabic IS NOT NULL AND n.name_arabic <> '' THEN 1 END) AS with_ar`
    );
    if (v[0]) {
        const pct = ((Number(v[0].with_ar) / Number(v[0].total)) * 100).toFixed(1);
        console.log(`\nname_arabic coverage: ${v[0].with_ar}/${v[0].total} (${pct}%)`);
    }

    console.log('\nDone!');
}

main()
    .catch((err) => { console.error('Error:', err); process.exit(1); })
    .finally(() => closeDriver());
