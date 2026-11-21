// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * enrich-narrators-deep.ts
 * ========================
 * Phase 1: Infer tradition from graph (HEARD_FROM neighbors)
 * Phase 2: Extract geographic_region from name nisbas
 *
 * Usage: npx tsx src/scripts/enrich-narrators-deep.ts [--phase 1|2] [--limit N] [--dry-run]
 */

import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── CLI ─────────────────────────────────────────────────────────────────────

function parseArgs() {
    const argv = process.argv.slice(2);
    const args = { phase: 0, limit: 0, dryRun: false };
    for (let i = 0; i < argv.length; i++) {
        if (argv[i] === '--phase' && argv[i + 1]) args.phase = parseInt(argv[++i], 10);
        if (argv[i] === '--limit' && argv[i + 1]) args.limit = parseInt(argv[++i], 10);
        if (argv[i] === '--dry-run') args.dryRun = true;
    }
    return args;
}

// ─── PHASE 1: Tradition inference from direct HEARD_FROM neighbors ──────────

async function phase1_inferTradition(dryRun: boolean) {
    console.log('\n========================================');
    console.log('  PHASE 1: Tradition Inference (Graph)');
    console.log('========================================\n');

    // Step 1: Get all narrators with known tradition
    const known = await runQuery<{ id: string; tradition: string }>(
        `MATCH (n:Narrator) WHERE n.tradition IS NOT NULL AND n.tradition <> '' RETURN n.id AS id, n.tradition AS tradition`
    );
    const traditionMap = new Map<string, string>();
    for (const k of known) traditionMap.set(k.id, k.tradition);
    console.log(`Narrators with known tradition: ${traditionMap.size}`);

    // Step 2: Get all HEARD_FROM edges
    const edges = await runQuery<{ fromId: string; toId: string }>(
        `MATCH (a:Narrator)-[:HEARD_FROM]->(b:Narrator) RETURN a.id AS fromId, b.id AS toId`
    );
    console.log(`HEARD_FROM edges: ${edges.length}`);

    // Build adjacency list
    const neighbors = new Map<string, Set<string>>();
    for (const e of edges) {
        if (!neighbors.has(e.fromId)) neighbors.set(e.fromId, new Set());
        if (!neighbors.has(e.toId)) neighbors.set(e.toId, new Set());
        neighbors.get(e.fromId)!.add(e.toId);
        neighbors.get(e.toId)!.add(e.fromId);
    }

    // Step 3: Get all narrators without tradition
    const unknown = await runQuery<{ id: string }>(
        `MATCH (n:Narrator) WHERE n.tradition IS NULL OR n.tradition = '' RETURN n.id AS id`
    );
    console.log(`Narrators without tradition: ${unknown.length}`);

    // Step 4: Propagate tradition through BFS (multiple rounds)
    let updated = 0;
    const rows: Array<{ id: string; tradition: string }> = [];

    for (let round = 1; round <= 5; round++) {
        let roundUpdates = 0;
        const unknownIds = unknown.filter(u => !traditionMap.has(u.id));

        for (const u of unknownIds) {
            const nbrs = neighbors.get(u.id);
            if (!nbrs) continue;

            // Count traditions among neighbors
            const counts: Record<string, number> = {};
            for (const nbrId of nbrs) {
                const t = traditionMap.get(nbrId);
                if (t) counts[t] = (counts[t] || 0) + 1;
            }

            // Majority vote
            const entries = Object.entries(counts);
            if (entries.length === 0) continue;
            entries.sort((a, b) => b[1] - a[1]);
            const winner = entries[0][0];
            traditionMap.set(u.id, winner);
            rows.push({ id: u.id, tradition: winner });
            roundUpdates++;
        }

        console.log(`  Round ${round}: inferred ${roundUpdates} traditions`);
        updated += roundUpdates;
        if (roundUpdates === 0) break;
    }

    console.log(`\nTotal tradition inferences: ${updated}`);

    // Step 5: Batch update Neo4j
    if (!dryRun && rows.length > 0) {
        const BS = 500;
        for (let i = 0; i < rows.length; i += BS) {
            const batch = rows.slice(i, i + BS);
            await runWrite(
                `UNWIND $rows AS row
                 MATCH (n:Narrator {id: row.id})
                 WHERE n.tradition IS NULL OR n.tradition = ''
                 SET n.tradition = row.tradition`,
                { rows: batch }
            );
        }
        console.log(`Updated ${rows.length} narrators in Neo4j`);
    }

    // Verify
    const remaining = await runQuery<{ count: number }>(
        `MATCH (n:Narrator) WHERE n.tradition IS NULL OR n.tradition = '' RETURN count(n) AS count`
    );
    console.log(`Remaining without tradition: ${Number(remaining[0]?.count ?? 0)}`);
}

// ─── PHASE 2: Geographic region from name nisbas ────────────────────────────

const NISBA_MAP: Record<string, string> = {
    // Cities
    'Madani': 'Medina', 'Madini': 'Medina', 'Madni': 'Medina',
    'Makki': 'Makkah', 'Mekki': 'Makkah',
    'Kufi': 'Kufa', 'Koofi': 'Kufa',
    'Basri': 'Basra', 'Basari': 'Basra',
    'Shami': 'Damascus', 'Dimashqi': 'Damascus', 'Damashqi': 'Damascus',
    'Misri': 'Egypt', 'Masri': 'Egypt',
    'Baghdadi': 'Baghdad',
    'Yamani': 'Yemen', 'Yemeni': 'Yemen',
    'Wasiti': 'Wasit',
    'Isfahani': 'Isfahan', 'Asfahani': 'Isfahan',
    'Razi': 'Rayy', 'Rai': 'Rayy',
    'Naysaburi': 'Nishapur', 'Nisaburi': 'Nishapur', 'Nishapuri': 'Nishapur',
    'Khurasani': 'Khurasan', 'Khorasani': 'Khurasan',
    'Hijazi': 'Hijaz',
    'Farsi': 'Persia', 'Irani': 'Persia',
    'Hindi': 'India',
    'Andalusi': 'Andalus',
    'Qayrawani': 'Qayrawan',
    'Samarqandi': 'Samarqand',
    'Bukhari': 'Bukhara',
    'Tirmidhi': 'Tirmidh',
    'Marwazi': 'Marw',
    'Hamadani': 'Hamadan',
    'Jurjani': 'Jurjan',
    'Tabarani': 'Tabaristan',
    // Tribal (can indicate city of settlement)
    'Ansari': 'Medina',
    'Qurayshi': 'Makkah', 'Qurashi': 'Makkah',
    'Hashimi': 'Makkah',
    'Thaqafi': 'Ta\'if',
    'Hudhali': 'Makkah',
    'Asadi': 'Kufa',
    'Tamimi': 'Basra',
    'Azdi': 'Basra',
    'Kinani': 'Makkah',
    'Bajli': 'Kufa',
    'Juhani': 'Medina',
    'Sulami': 'Kufa',
    'Nakhai': 'Kufa', 'Nakha\'i': 'Kufa',
    'Kindi': 'Kufa',
    'Harithi': 'Kufa',
    'Laithi': 'Medina', 'Laythi': 'Medina',
    'Zuhri': 'Medina',
    'Aslami': 'Medina',
    'Ghifari': 'Medina',
    'Muzani': 'Medina', 'Mazini': 'Medina',
    'Khuza\'i': 'Makkah', 'Khuzai': 'Makkah',
    'Sa\'di': 'Basra',
    'Kalbi': 'Kufa',
    'Hamdani': 'Kufa',
    'Abdi': 'Basra',
    'Dausi': 'Yemen',
    'Himyari': 'Yemen',
    'Tha\'labi': 'Kufa',
};

async function phase2_nisbaExtraction(dryRun: boolean) {
    console.log('\n========================================');
    console.log('  PHASE 2: Geographic Region from Nisbas');
    console.log('========================================\n');

    const narrators = await runQuery<{ id: string; en: string; ar: string | null }>(
        `MATCH (n:Narrator)
         WHERE n.geographic_region IS NULL OR n.geographic_region = ''
         RETURN n.id AS id, n.name_english AS en, n.name_arabic AS ar`
    );
    console.log(`Narrators without geographic_region: ${narrators.length}`);

    const rows: Array<{ id: string; region: string }> = [];

    for (const n of narrators) {
        const name = n.en || '';
        let matched = false;

        // Check for "al-Nisba" pattern in name
        for (const [nisba, region] of Object.entries(NISBA_MAP)) {
            // Match "al-Nisba" or just "Nisba" at word boundary
            const patterns = [
                new RegExp(`al-${nisba}\\b`, 'i'),
                new RegExp(`\\b${nisba}\\b`, 'i'),
            ];
            for (const pat of patterns) {
                if (pat.test(name)) {
                    rows.push({ id: n.id, region });
                    matched = true;
                    break;
                }
            }
            if (matched) break;
        }
    }

    console.log(`Extracted region from nisba for: ${rows.length} narrators`);

    // Show distribution
    const dist: Record<string, number> = {};
    for (const r of rows) dist[r.region] = (dist[r.region] || 0) + 1;
    const sorted = Object.entries(dist).sort((a, b) => b[1] - a[1]);
    for (const [region, count] of sorted.slice(0, 15)) {
        console.log(`  ${region.padEnd(15)} ${count}`);
    }

    if (!dryRun && rows.length > 0) {
        const BS = 500;
        let done = 0;
        for (let i = 0; i < rows.length; i += BS) {
            const batch = rows.slice(i, i + BS);
            await runWrite(
                `UNWIND $rows AS row
                 MATCH (n:Narrator {id: row.id})
                 WHERE n.geographic_region IS NULL OR n.geographic_region = ''
                 SET n.geographic_region = row.region`,
                { rows: batch }
            );
            done += batch.length;
        }
        console.log(`\nUpdated ${done} narrators in Neo4j`);
    }

    const remaining = await runQuery<{ count: number }>(
        `MATCH (n:Narrator) WHERE n.geographic_region IS NULL OR n.geographic_region = '' RETURN count(n) AS count`
    );
    console.log(`Remaining without region: ${Number(remaining[0]?.count ?? 0)}`);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
    const args = parseArgs();

    console.log('='.repeat(50));
    console.log('  Deep Narrator Enrichment');
    console.log('='.repeat(50));
    console.log(`Phase: ${args.phase || 'all'}`);
    console.log(`Limit: ${args.limit || 'none'}`);
    console.log(`Dry run: ${args.dryRun}`);

    if (args.phase === 0 || args.phase === 1) {
        await phase1_inferTradition(args.dryRun);
    }
    if (args.phase === 0 || args.phase === 2) {
        await phase2_nisbaExtraction(args.dryRun);
    }

    console.log('\nDone!');
}

main()
    .catch((err) => { console.error('\nFatal error:', err); process.exit(1); })
    .finally(() => closeDriver());
