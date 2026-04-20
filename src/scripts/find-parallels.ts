/**
 * find-parallels.ts
 *
 * Batch pipeline script — loops through Hadith nodes in Neo4j, and for each
 * hadith calls you.com Research API once per faith tradition. Discovered
 * parallels are committed directly into the Neo4j schema as
 * CrossCulturalParallel, SourceText, ReligiousTradition, and MotifTag nodes.
 *
 * Usage:
 *   npm run db:find-parallels [-- options]
 *
 * Options:
 *   --batch-size <n>   Number of hadiths per run (default: 5)
 *   --offset <n>       Skip first N hadiths (default: 0)
 *   --faith <ID>       Limit to this tradition (repeat for multiple)
 *                        e.g. --faith JUDAISM --faith ZOROASTRIANISM
 *   --effort <level>   you.com effort: lite|standard|deep|exhaustive (default: standard)
 *   --delay-ms <n>     Delay between API calls in ms (default: 1500)
 *
 * Requires: YOU_API_KEY in .env.local
 *
 * Cost note: each (hadith × faith) is one you.com Research API call.
 *   5 hadiths × 15 faiths = 75 calls per run.
 *   Use --faith to target specific traditions first.
 */

import neo4j from 'neo4j-driver';
import { loadEnv, getRequiredEnv } from './lib/env';
import { processHadith } from '../lib/comparative/pipeline';
import { runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── CLI args ─────────────────────────────────────────────────────────────────

function parseArgs() {
    const args = process.argv.slice(2);
    const get = (flag: string, def: string) => {
        const i = args.indexOf(flag);
        return i !== -1 && args[i + 1] ? args[i + 1] : def;
    };
    const faithIds: string[] = [];
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--faith' && args[i + 1]) {
            faithIds.push(args[++i].toUpperCase());
        }
    }
    return {
        batchSize: parseInt(get('--batch-size', '5'), 10),
        offset: parseInt(get('--offset', '0'), 10),
        faithIds,
        effort: (get('--effort', 'standard') as 'lite' | 'standard' | 'deep' | 'exhaustive'),
        delayMs: parseInt(get('--delay-ms', '1500'), 10),
    };
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
    const opts = parseArgs();
    const youApiKey = getRequiredEnv('YOU_API_KEY');

    console.log('🔍 find-parallels — you.com Research Pipeline');
    console.log('═══════════════════════════════════════════════');
    console.log(`  Batch size : ${opts.batchSize} hadiths`);
    console.log(`  Offset     : ${opts.offset}`);
    console.log(`  Faiths     : ${opts.faithIds.length > 0 ? opts.faithIds.join(', ') : 'all (15)'}`);
    console.log(`  Effort     : ${opts.effort}`);
    console.log(`  Delay      : ${opts.delayMs}ms`);
    console.log('');

    // Fetch hadiths
    const hadiths = await runQuery<{
        id: string;
        title: string;
        text_english: string;
        primary_topic: string;
    }>(
        `MATCH (h:Hadith)
         WHERE h.text_english IS NOT NULL AND h.text_english <> ''
         RETURN h.id AS id, h.title AS title, h.text_english AS text_english,
                h.primary_topic AS primary_topic
         ORDER BY h.created_at
         SKIP $offset LIMIT $batchSize`,
        { offset: neo4j.int(opts.offset), batchSize: neo4j.int(opts.batchSize) }
    );

    if (hadiths.length === 0) {
        console.log('No hadiths found. Adjust --offset or check the database.');
        await closeDriver();
        return;
    }

    console.log(`📖 Processing ${hadiths.length} hadith(s)...\n`);

    let totalCreated = 0;
    let totalUpdated = 0;
    let totalErrors = 0;

    for (let i = 0; i < hadiths.length; i++) {
        const hadith = hadiths[i];
        console.log(`\n[${i + 1}/${hadiths.length}] ${hadith.title}`);

        const result = await processHadith(
            { ...hadith },
            {
                youApiKey,
                faithIds: opts.faithIds,
                effort: opts.effort,
                delayMs: opts.delayMs,
                verbose: true,
            }
        );

        totalCreated += result.parallels_created;
        totalUpdated += result.parallels_updated;
        totalErrors += result.errors;

        console.log(
            `  → ${result.parallels_found} parallel(s) found` +
            (result.parallels_created ? `, ${result.parallels_created} created` : '') +
            (result.parallels_updated ? `, ${result.parallels_updated} updated` : '') +
            (result.errors ? `, ${result.errors} error(s)` : '')
        );
    }

    console.log('\n═══════════════════════════════════════════════');
    console.log(`  Parallels created : ${totalCreated}`);
    console.log(`  Parallels updated : ${totalUpdated}`);
    console.log(`  Errors            : ${totalErrors}`);
    console.log('');

    await closeDriver();
}

main().catch((err) => {
    console.error('❌ Fatal:', err);
    process.exit(1);
});
