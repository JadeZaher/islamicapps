/**
 * link-sanad-chains.ts
 * ====================
 * Read parsed sanad data (from parse_sanad.py) and create graph relationships:
 *   Hadith → HAS_VARIATION → MatnVariation → TRANSMITTED_VIA → Chain → INCLUDES → Narrator
 *
 * For each parsed chain:
 *   1. Fuzzy-match each narrator name against existing Narrator nodes
 *   2. Create MatnVariation node (uses Hadith text)
 *   3. Create Chain node
 *   4. Link Chain → matched Narrators via INCLUDES
 *   5. Create HEARD_FROM relationships between consecutive narrators
 *
 * Usage:
 *   tsx src/scripts/link-sanad-chains.ts --input datasets/hadith-data/classical_sanad_parsed.jsonl
 *   tsx src/scripts/link-sanad-chains.ts --input ... --dry-run
 *   tsx src/scripts/link-sanad-chains.ts --input ... --sample 100
 *   tsx src/scripts/link-sanad-chains.ts --input ... --min-match 0.5
 */

import fs from 'fs';
import readline from 'readline';
import { randomUUID } from 'crypto';

import { loadEnv } from './lib/env';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── Types ───────────────────────────────────────────────────────────────────

interface ParsedNarrator {
    name_arabic: string;
    transmission_verb: string;
    position: number;
}

interface ParsedChain {
    hadith_id: string;
    source_canonical: string;
    row_no: string;
    chain_raw: string;
    narrators: ParsedNarrator[];
    narrator_count: number;
}

interface NarratorRecord {
    id: string;
    name_arabic: string;
    name_english: string;
    scholar_indx: number | null;
}

interface CliArgs {
    input: string;
    dryRun: boolean;
    sample: number;
    minMatch: number;
    batchSize: number;
}

// ─── CLI ─────────────────────────────────────────────────────────────────────

function parseArgs(): CliArgs {
    const argv = process.argv.slice(2);
    const args: CliArgs = {
        input: '',
        dryRun: false,
        sample: 0,
        minMatch: 0.5,
        batchSize: 200,
    };

    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--input' && argv[i + 1]) args.input = argv[++i];
        else if (a === '--dry-run') args.dryRun = true;
        else if (a === '--sample' && argv[i + 1]) args.sample = parseInt(argv[++i], 10);
        else if (a === '--min-match' && argv[i + 1]) args.minMatch = parseFloat(argv[++i]);
        else if (a === '--batch-size' && argv[i + 1]) args.batchSize = parseInt(argv[++i], 10);
    }

    if (!args.input) {
        console.error('ERROR: --input <path> is required');
        process.exit(1);
    }

    return args;
}

// ─── Arabic text normalization ───────────────────────────────────────────────

function normalizeAr(text: string): string {
    if (!text) return '';
    // Remove harakat (diacritics)
    text = text.replace(/[\u064B-\u0652]/g, '');
    // Normalize alif variants
    text = text.replace(/[\u0623\u0625\u0622]/g, '\u0627');
    // Normalize ta marbuta to ha
    text = text.replace(/\u0629/g, '\u0647');
    // Normalize alif maqsura to ya
    text = text.replace(/\u0649/g, '\u064A');
    // Remove non-Arabic non-space
    text = text.replace(/[^\u0621-\u064A\s]/g, '');
    // Collapse whitespace
    text = text.split(/\s+/).filter(Boolean).join(' ');
    return text.trim();
}

// ─── Fuzzy name matching ─────────────────────────────────────────────────────

/**
 * Simple token-overlap similarity between two Arabic names.
 * Returns a score between 0 and 1.
 */
function nameSimilarity(a: string, b: string): number {
    const tokensA = new Set(normalizeAr(a).split(' ').filter(t => t.length > 1));
    const tokensB = new Set(normalizeAr(b).split(' ').filter(t => t.length > 1));
    if (tokensA.size === 0 || tokensB.size === 0) return 0;

    let overlap = 0;
    for (const t of tokensA) {
        if (tokensB.has(t)) overlap++;
    }

    const minSize = Math.min(tokensA.size, tokensB.size);
    return overlap / minSize;
}

// ─── Narrator index ──────────────────────────────────────────────────────────

class NarratorIndex {
    private narrators: NarratorRecord[] = [];
    /** Normalized Arabic name → narrator records */
    private byNormName = new Map<string, NarratorRecord[]>();
    /** Single-token index for partial matching */
    private byToken = new Map<string, Set<number>>();

    async load(): Promise<void> {
        console.log('Loading narrators from Neo4j...');

        const result = await runQuery<{
            id: string;
            ar: string | null;
            en: string | null;
            idx: number | null;
        }>(`
            MATCH (n:Narrator)
            RETURN n.id as id, n.name_arabic as ar, n.name_english as en, n.scholar_indx as idx
        `);

        for (const r of result) {
            const rec: NarratorRecord = {
                id: r.id,
                name_arabic: r.ar ?? '',
                name_english: r.en ?? '',
                scholar_indx: typeof r.idx === 'number' ? r.idx : null,
            };
            const index = this.narrators.length;
            this.narrators.push(rec);

            // Index by normalized full name
            const normName = normalizeAr(rec.name_arabic);
            if (normName) {
                const existing = this.byNormName.get(normName) ?? [];
                existing.push(rec);
                this.byNormName.set(normName, existing);
            }

            // Index by individual tokens
            const tokens = normName.split(' ').filter(t => t.length > 1);
            for (const token of tokens) {
                const set = this.byToken.get(token) ?? new Set();
                set.add(index);
                this.byToken.set(token, set);
            }
        }

        console.log(`  Loaded ${this.narrators.length} narrators (${this.byNormName.size} unique Arabic names)`);
    }

    /**
     * Find the best matching narrator for an Arabic name extracted from the chain.
     * Returns null if no match above the threshold.
     */
    findBest(chainName: string, minScore: number): NarratorRecord | null {
        const norm = normalizeAr(chainName);
        if (!norm || norm.length < 2) return null;

        // Exact match
        const exact = this.byNormName.get(norm);
        if (exact && exact.length > 0) return exact[0];

        // Token-based candidate retrieval
        const tokens = norm.split(' ').filter(t => t.length > 1);
        const candidateIndices = new Set<number>();
        for (const token of tokens) {
            const indices = this.byToken.get(token);
            if (indices) {
                for (const idx of indices) candidateIndices.add(idx);
            }
        }

        if (candidateIndices.size === 0) return null;

        // Score candidates
        let bestScore = 0;
        let bestRecord: NarratorRecord | null = null;

        for (const idx of candidateIndices) {
            const rec = this.narrators[idx];
            const score = nameSimilarity(chainName, rec.name_arabic);
            if (score > bestScore) {
                bestScore = score;
                bestRecord = rec;
            }
        }

        return bestScore >= minScore ? bestRecord : null;
    }
}

// ─── Batched graph creation ──────────────────────────────────────────────────

interface ChainBatchItem {
    hadithId: string;
    variationId: string;
    chainId: string;
    narratorIds: string[];
}

/**
 * Flush a batch of chain graphs to Neo4j using UNWIND for each operation type.
 * This is ~50x faster than individual writes per chain.
 */
async function flushChainBatch(batch: ChainBatchItem[], dryRun: boolean): Promise<void> {
    if (batch.length === 0 || dryRun) return;

    // 1. Create MatnVariation nodes + link Hadith → HAS_VARIATION → MatnVariation
    await runWrite(`
        UNWIND $rows AS row
        MATCH (h:Hadith {id: row.hadithId})
        CREATE (m:MatnVariation {
            id: row.variationId,
            source_book: h.source,
            text_arabic: h.text_arabic,
            text_english: h.text_english
        })
        CREATE (h)-[:HAS_VARIATION]->(m)
    `, { rows: batch.map(b => ({ hadithId: b.hadithId, variationId: b.variationId })) });

    // 2. Create Chain nodes + link MatnVariation → TRANSMITTED_VIA → Chain
    await runWrite(`
        UNWIND $rows AS row
        MATCH (m:MatnVariation {id: row.variationId})
        CREATE (c:Chain {
            id: row.chainId,
            is_golden_chain: false,
            created_at: datetime()
        })
        CREATE (m)-[:TRANSMITTED_VIA]->(c)
    `, { rows: batch.map(b => ({ variationId: b.variationId, chainId: b.chainId })) });

    // 3. Chain → INCLUDES → Narrator (flatten all chain-narrator pairs)
    const includeRows: Array<{ chainId: string; narratorId: string }> = [];
    for (const item of batch) {
        for (const nId of item.narratorIds) {
            includeRows.push({ chainId: item.chainId, narratorId: nId });
        }
    }
    if (includeRows.length > 0) {
        await runWrite(`
            UNWIND $rows AS row
            MATCH (c:Chain {id: row.chainId})
            MATCH (n:Narrator {id: row.narratorId})
            MERGE (c)-[:INCLUDES]->(n)
        `, { rows: includeRows });
    }

    // 4. HEARD_FROM between consecutive narrators in each chain
    const heardFromRows: Array<{ studentId: string; teacherId: string }> = [];
    for (const item of batch) {
        for (let i = 0; i < item.narratorIds.length - 1; i++) {
            heardFromRows.push({
                studentId: item.narratorIds[i],
                teacherId: item.narratorIds[i + 1],
            });
        }
    }
    if (heardFromRows.length > 0) {
        await runWrite(`
            UNWIND $rows AS row
            MATCH (student:Narrator {id: row.studentId})
            MATCH (teacher:Narrator {id: row.teacherId})
            MERGE (student)-[:HEARD_FROM]->(teacher)
        `, { rows: heardFromRows });
    }
}

// ─── Progress ────────────────────────────────────────────────────────────────

function formatDuration(ms: number): string {
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}m${rem}s`;
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
    const args = parseArgs();

    console.log('='.repeat(60));
    console.log('  Sanad Chain Linker');
    console.log('='.repeat(60));
    console.log(`\nInput:       ${args.input}`);
    console.log(`Dry run:     ${args.dryRun}`);
    console.log(`Min match:   ${args.minMatch}`);
    if (args.sample) console.log(`Sample:      ${args.sample}`);

    // Load narrator index
    const index = new NarratorIndex();
    await index.load();

    const startedAt = Date.now();
    let processed = 0;
    let linked = 0;
    let totalMatched = 0;
    let totalNarrators = 0;
    let noMatches = 0;
    let errors = 0;

    let chainBatch: ChainBatchItem[] = [];

    const rl = readline.createInterface({
        input: fs.createReadStream(args.input, 'utf8'),
        crlfDelay: Infinity,
    });

    for await (const line of rl) {
        if (args.sample && processed >= args.sample) break;

        const trimmed = line.trim();
        if (!trimmed) continue;

        let parsed: ParsedChain;
        try {
            parsed = JSON.parse(trimmed);
        } catch {
            continue;
        }

        processed++;

        // Match each narrator
        const matchedIds: string[] = [];
        for (const narrator of parsed.narrators) {
            totalNarrators++;
            const best = index.findBest(narrator.name_arabic, args.minMatch);
            if (best) {
                matchedIds.push(best.id);
                totalMatched++;
            }
        }

        if (matchedIds.length === 0) {
            noMatches++;
        } else {
            chainBatch.push({
                hadithId: parsed.hadith_id,
                variationId: randomUUID(),
                chainId: randomUUID(),
                narratorIds: matchedIds,
            });
            linked++;
        }

        // Flush batch
        if (chainBatch.length >= args.batchSize) {
            try {
                await flushChainBatch(chainBatch, args.dryRun);
            } catch (err) {
                console.error(`  [ERROR] batch flush:`, err);
                errors++;
            }
            chainBatch = [];

            const elapsed = Date.now() - startedAt;
            const matchRate = totalNarrators > 0
                ? ((totalMatched / totalNarrators) * 100).toFixed(1)
                : '0';
            console.log(
                `  [${processed.toLocaleString()}] ${linked} linked, ` +
                `${matchRate}% match rate — ` +
                `${formatDuration(elapsed)} elapsed`
            );
        }
    }

    // Flush remaining
    if (chainBatch.length > 0) {
        try {
            await flushChainBatch(chainBatch, args.dryRun);
        } catch (err) {
            console.error(`  [ERROR] final batch flush:`, err);
            errors++;
        }
    }

    const elapsed = Date.now() - startedAt;
    const matchRate = totalNarrators > 0
        ? ((totalMatched / totalNarrators) * 100).toFixed(1)
        : '0';

    console.log('\n' + '='.repeat(60));
    console.log('  ' + (args.dryRun ? 'Dry-Run ' : '') + 'Complete');
    console.log('='.repeat(60));
    console.log(`  Chains processed:  ${processed.toLocaleString()}`);
    console.log(`  Chains linked:     ${linked.toLocaleString()}`);
    console.log(`  No matches:        ${noMatches.toLocaleString()}`);
    console.log(`  Narrator refs:     ${totalNarrators.toLocaleString()}`);
    console.log(`  Matched:           ${totalMatched.toLocaleString()} (${matchRate}%)`);
    console.log(`  Errors:            ${errors}`);
    console.log(`  Duration:          ${formatDuration(elapsed)}`);

    if (args.dryRun) {
        console.log('\n  [DRY-RUN] No writes were issued to Neo4j.');
    }
}

main()
    .catch((err) => {
        console.error('\nFatal error:', err);
        process.exit(1);
    })
    .finally(() => closeDriver());
