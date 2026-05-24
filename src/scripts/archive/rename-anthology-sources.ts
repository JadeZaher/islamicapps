// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * rename-anthology-sources.ts
 *
 * Bulk rename Source nodes imported by import-pure-canon.ts. The importer
 * uses CONTAINER labels by default (e.g. "al-Albani's Hadith Authentications")
 * that are deliberately non-committal. When you learn the authoritative
 * published titles, edit the RENAMES map below and run this script — it
 * MATCHes Source nodes by their stable `source_slug` property and updates
 * only the `name` field.
 *
 * Idempotent. Safe to re-run.
 *
 * Usage:
 *   tsx src/scripts/rename-anthology-sources.ts            # dry-run
 *   tsx src/scripts/rename-anthology-sources.ts --apply    # actually update
 */

import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

// EDIT THIS MAP: source_slug → new display name.
// Leave a slug OUT of this map to skip it.
const RENAMES: Record<string, string> = {
    // albani:          "Sahih al-Jami' al-Saghir",
    // talidi:          "Tuhfat al-Qari",
    // talidi_khasais:  "Tahdhib al-Khasa'is al-Nabawiyyah",
    // talidi_tafsir:   "al-Talidi's Tafsir Hadith Selections",
    // talidi_shifa:    "Takhrij Ahadith al-Shifa",
    // ghumari_qudsi:   "al-Ghumari's Sacred Hadith Collection",
};

async function main() {
    const args = process.argv.slice(2);
    const apply = args.includes('--apply');

    if (Object.keys(RENAMES).length === 0) {
        console.log('No renames defined. Edit the RENAMES map in this file and re-run.');
        await closeDriver();
        return;
    }

    console.log('🔄 Anthology Source rename');
    console.log('==========================');
    console.log(`Mode: ${apply ? 'APPLY' : 'DRY-RUN'}`);
    console.log('');

    for (const [slug, newName] of Object.entries(RENAMES)) {
        // Look up current state
        const rows = await runQuery<{ id: string; current_name: string; hadith_count: unknown }>(
            `MATCH (s:Source {source_slug: $slug})
             OPTIONAL MATCH (h:Hadith)-[:FROM_SOURCE]->(s)
             WITH s, count(DISTINCT h) AS hadith_count
             RETURN s.id AS id, s.name AS current_name, hadith_count`,
            { slug }
        );

        if (rows.length === 0) {
            console.log(`  ⚠️  No Source node with source_slug='${slug}' found — skipping`);
            continue;
        }

        for (const row of rows) {
            const hcount = Number(row.hadith_count);
            console.log(`  ${slug}:`);
            console.log(`    current : "${row.current_name}"`);
            console.log(`    new     : "${newName}"`);
            console.log(`    hadiths : ${hcount}`);

            if (apply) {
                await runWrite(
                    `MATCH (s:Source {id: $id})
                     SET s.name = $newName, s.updated_at = datetime()`,
                    { id: row.id, newName }
                );
                console.log(`    ✅ renamed`);
            } else {
                console.log(`    (dry-run — not applied)`);
            }
        }
    }

    if (!apply) {
        console.log('\nRun with --apply to actually perform renames.');
    } else {
        console.log('\n✅ Renames applied.');
    }

    await closeDriver();
}

main().catch((err) => {
    console.error('❌ Rename failed:', err);
    process.exit(1);
});
