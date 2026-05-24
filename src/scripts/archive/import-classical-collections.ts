// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * import-classical-collections.ts
 * ================================
 * Import classical hadith collections from CSV or JSONL into Neo4j.
 *
 * Handles:
 *   - datasets/hadith-data/classical_canon_translated.csv   (29,917 rows)
 *   - datasets/hadith-data/classical_collections_final.jsonl (20,977 rows — subset)
 *
 * The CSV is a superset. The JSONL contains refined translations for 20,977 of those rows.
 * Recommended workflow:
 *   1. Import CSV first (all rows)
 *   2. Import JSONL second (updates translations via MERGE)
 *
 * Usage:
 *   tsx src/scripts/import-classical-collections.ts --input datasets/hadith-data/classical_canon_translated.csv
 *   tsx src/scripts/import-classical-collections.ts --input datasets/hadith-data/classical_collections_final.jsonl
 *   tsx src/scripts/import-classical-collections.ts --input <file> --dry-run
 *   tsx src/scripts/import-classical-collections.ts --input <file> --sample 500
 *   tsx src/scripts/import-classical-collections.ts --input <file> --batch-size 500
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { randomUUID } from 'crypto';

import { loadEnv } from './lib/env';
import { runWrite, closeDriver } from '../lib/db/neo4j';
import { mergeNodeByKey, mergeEdge } from '../lib/db/neo4j-helpers';
import { normalizeArabic } from '../lib/import/canon-normalize';
import { CANONICAL_SOURCES, getCanonicalName } from '../lib/constants/sources';

// ─── Reverse lookup: source_canonical → slug ─────────────────────────────────

const CANONICAL_TO_SLUG: Record<string, string> = {};
for (const [slug, entry] of Object.entries(CANONICAL_SOURCES)) {
    CANONICAL_TO_SLUG[entry.canonical] = slug;
}

/** Classical slugs that this script handles */
const ALLOWED_SLUGS = new Set(['ahmad', 'darimi', 'shafii', 'muwatta']);

function resolveSlug(sourceCanonical: string): string | null {
    const slug = CANONICAL_TO_SLUG[sourceCanonical];
    if (slug && ALLOWED_SLUGS.has(slug)) return slug;
    return null;
}

// ─── Types ───────────────────────────────────────────────────────────────────

interface InputRow {
    id: string;
    source_canonical: string;
    hadith_no: string;
    topics: string;
    ruling: string;
    chain: string;
    text_ar: string;
    text_en: string;
    shelf_no: string;
    row_no: string;
}

interface CliArgs {
    input: string;
    dryRun: boolean;
    sample: number | null;
    batchSize: number;
}

// ─── CLI Parsing ─────────────────────────────────────────────────────────────

function parseArgs(): CliArgs {
    const argv = process.argv.slice(2);
    const args: CliArgs = {
        input: '',
        dryRun: false,
        sample: null,
        batchSize: 1000,
    };

    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--input' && argv[i + 1]) {
            args.input = argv[++i];
        } else if (a === '--dry-run') {
            args.dryRun = true;
        } else if (a === '--sample' && argv[i + 1]) {
            args.sample = parseInt(argv[++i], 10);
        } else if (a === '--batch-size' && argv[i + 1]) {
            args.batchSize = parseInt(argv[++i], 10);
        }
    }

    if (!args.input) {
        console.error('ERROR: --input <path> is required');
        process.exit(1);
    }

    if (!fs.existsSync(args.input)) {
        console.error(`ERROR: Input file not found: ${args.input}`);
        process.exit(1);
    }

    return args;
}

// ─── Format detection ────────────────────────────────────────────────────────

type InputFormat = 'csv' | 'jsonl';

function detectFormat(filePath: string): InputFormat {
    const ext = path.extname(filePath).toLowerCase();
    if (ext === '.csv') return 'csv';
    if (ext === '.jsonl' || ext === '.json') return 'jsonl';
    // Peek at first line
    const firstLine = fs.readFileSync(filePath, 'utf8').split('\n')[0].trim();
    if (firstLine.startsWith('{')) return 'jsonl';
    return 'csv';
}

// ─── CSV Parser ──────────────────────────────────────────────────────────────

function parseCSVLine(line: string): string[] {
    const result: string[] = [];
    let current = '';
    let insideQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        const nextChar = line[i + 1];

        if (char === '"') {
            if (insideQuotes && nextChar === '"') {
                current += '"';
                i++;
            } else {
                insideQuotes = !insideQuotes;
            }
        } else if (char === ',' && !insideQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    result.push(current);
    return result;
}

/**
 * Stream rows from a CSV file handling multi-line quoted fields and BOM.
 */
async function* streamCSV(filePath: string): AsyncGenerator<InputRow> {
    const content = fs.readFileSync(filePath, 'utf8');
    // Strip BOM
    const clean = content.charCodeAt(0) === 0xFEFF ? content.slice(1) : content;

    // Split respecting quoted newlines
    const lines: string[] = [];
    let current = '';
    let insideQuotes = false;
    for (let i = 0; i < clean.length; i++) {
        const char = clean[i];
        if (char === '"') insideQuotes = !insideQuotes;
        if ((char === '\n' || char === '\r') && !insideQuotes) {
            if (char === '\r' && clean[i + 1] === '\n') i++;
            if (current.trim()) lines.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    if (current.trim()) lines.push(current);

    if (lines.length === 0) return;

    // Parse header
    const headers = parseCSVLine(lines[0]).map(h => h.trim());

    for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i]);
        const row: Record<string, string> = {};
        for (let j = 0; j < headers.length; j++) {
            row[headers[j]] = (values[j] ?? '').trim();
        }
        yield row as unknown as InputRow;
    }
}

/**
 * Stream rows from a JSONL file.
 */
async function* streamJSONL(filePath: string): AsyncGenerator<InputRow> {
    const rl = readline.createInterface({
        input: fs.createReadStream(filePath, 'utf8'),
        crlfDelay: Infinity,
    });

    for await (const line of rl) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
            const obj = JSON.parse(trimmed);
            yield {
                id: obj.id ?? '',
                source_canonical: obj.source_canonical ?? '',
                hadith_no: String(obj.hadith_no ?? ''),
                topics: obj.topics ?? '',
                ruling: obj.ruling ?? '',
                chain: obj.chain ?? '',
                text_ar: obj.text_ar ?? '',
                text_en: obj.text_en ?? '',
                shelf_no: String(obj.shelf_no ?? ''),
                row_no: String(obj.row_no ?? ''),
            };
        } catch {
            console.error(`  JSON parse error: ${trimmed.slice(0, 80)}`);
        }
    }
}

// ─── Progress helpers ────────────────────────────────────────────────────────

function formatNum(n: number): string {
    return n.toLocaleString('en-US');
}

function formatDuration(ms: number): string {
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    if (m < 60) return rem > 0 ? `${m}m${rem}s` : `${m}m`;
    const h = Math.floor(m / 60);
    const rm = m % 60;
    return `${h}h${rm}m`;
}

// ─── Neo4j batch merge ───────────────────────────────────────────────────────

interface HadithBatchRow {
    id: string;
    title: string;
    primary_topic: string;
    source: string;
    source_slug: string;
    hadith_no: string;
    text_arabic: string;
    text_english: string;
    isnad_arabic: string;
    chain_text_arabic: string;
    topics: string;
    display_grade: string;
    transmission_type: string;
    tradition: string;
    matn_fingerprint: string;
    source_role: string;
    shelf_no: string;
}

async function batchMergeHadiths(rows: HadithBatchRow[], dryRun: boolean): Promise<void> {
    if (rows.length === 0 || dryRun) return;

    const cypher = `
        UNWIND $rows AS row
        MERGE (h:Hadith {id: row.id})
        ON CREATE SET
            h.title           = row.title,
            h.primary_topic   = row.primary_topic,
            h.source          = row.source,
            h.source_slug     = row.source_slug,
            h.hadith_no       = row.hadith_no,
            h.text_arabic     = row.text_arabic,
            h.text_english    = row.text_english,
            h.isnad_arabic    = row.isnad_arabic,
            h.chain_text_arabic = row.chain_text_arabic,
            h.topics          = row.topics,
            h.display_grade   = row.display_grade,
            h.transmission_type = row.transmission_type,
            h.tradition       = row.tradition,
            h.matn_fingerprint = row.matn_fingerprint,
            h.source_role     = row.source_role,
            h.shelf_no        = row.shelf_no,
            h.created_at      = datetime()
        ON MATCH SET
            h.title           = row.title,
            h.primary_topic   = row.primary_topic,
            h.text_arabic     = row.text_arabic,
            h.text_english    = row.text_english,
            h.isnad_arabic    = row.isnad_arabic,
            h.chain_text_arabic = row.chain_text_arabic,
            h.matn_fingerprint = row.matn_fingerprint,
            h.topics          = row.topics,
            h.updated_at      = datetime()
    `;
    await runWrite(cypher, { rows });
}

interface EdgeBatchRow {
    hadith_id: string;
    source_name: string;
}

async function batchMergeFromSourceEdges(rows: EdgeBatchRow[], dryRun: boolean): Promise<void> {
    if (rows.length === 0 || dryRun) return;

    const cypher = `
        UNWIND $rows AS row
        MATCH (h:Hadith {id: row.hadith_id})
        MATCH (s:Source {name: row.source_name})
        MERGE (h)-[:FROM_SOURCE]->(s)
    `;
    await runWrite(cypher, { rows });
}

async function batchMergeInSchoolEdges(hadithIds: string[], dryRun: boolean): Promise<void> {
    if (hadithIds.length === 0 || dryRun) return;

    const cypher = `
        UNWIND $ids AS hadithId
        MATCH (h:Hadith {id: hadithId})
        MATCH (sch:SchoolOfThought {name: 'Sunni'})
        MERGE (h)-[:IN_SCHOOL]->(sch)
    `;
    await runWrite(cypher, { ids: hadithIds });
}

// ─── Ensure singleton nodes ──────────────────────────────────────────────────

async function ensureSunniSchool(dryRun: boolean): Promise<void> {
    if (dryRun) return;
    await mergeNodeByKey({
        label: 'SchoolOfThought',
        keyProp: 'name',
        keyValue: 'Sunni',
        createProps: { tradition: 'Sunni' },
    });
}

async function ensureSource(
    sourceName: string,
    sourceSlug: string,
    sourceCache: Map<string, string>,
    dryRun: boolean
): Promise<void> {
    if (sourceCache.has(sourceSlug)) return;

    if (dryRun) {
        sourceCache.set(sourceSlug, sourceName);
        return;
    }

    const result = await mergeNodeByKey({
        label: 'Source',
        keyProp: 'name',
        keyValue: sourceName,
        createProps: { source_slug: sourceSlug },
        mutableProps: { source_slug: sourceSlug },
    });
    sourceCache.set(sourceSlug, result.id);

    // Source -[:CANON_OF]-> Sunni
    await mergeEdge({
        fromLabel: 'Source',
        fromKey: { prop: 'id', value: result.id },
        toLabel: 'SchoolOfThought',
        toKey: { prop: 'name', value: 'Sunni' },
        relType: 'CANON_OF',
    });
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
    loadEnv();

    const args = parseArgs();
    const format = detectFormat(args.input);

    console.log('='.repeat(70));
    console.log('  Classical Collections -> Neo4j Import');
    console.log('='.repeat(70));
    console.log(`\nInput file:  ${args.input}`);
    console.log(`Format:      ${format.toUpperCase()}`);
    console.log(`Batch size:  ${args.batchSize}`);
    console.log(`Dry run:     ${args.dryRun}`);
    if (args.sample !== null) console.log(`Sample:      ${args.sample}`);

    // Ensure SchoolOfThought:Sunni exists
    await ensureSunniSchool(args.dryRun);

    const sourceCache = new Map<string, string>();
    const sourceCounts: Record<string, number> = {};

    let processed = 0;
    let skipped = 0;
    let errors = 0;
    const startedAt = new Date();

    // Batch buffers
    let hadithBatch: HadithBatchRow[] = [];
    let fromSourceBatch: EdgeBatchRow[] = [];
    let inSchoolBatch: string[] = [];
    let batchIndex = 0;

    const flushBatch = async (): Promise<void> => {
        batchIndex++;
        await batchMergeHadiths(hadithBatch, args.dryRun);
        await batchMergeFromSourceEdges(fromSourceBatch, args.dryRun);
        await batchMergeInSchoolEdges(inSchoolBatch, args.dryRun);
        hadithBatch = [];
        fromSourceBatch = [];
        inSchoolBatch = [];

        const elapsed = Date.now() - startedAt.getTime();
        const rate = processed > 0 ? elapsed / processed : 0;
        const etaStr = args.sample
            ? formatDuration(rate * (args.sample - processed))
            : '';
        console.log(
            `  [batch ${batchIndex}] ${formatNum(processed)} rows processed` +
            (etaStr ? ` — ETA ${etaStr}` : '') +
            ` — ${formatDuration(elapsed)} elapsed`
        );
    };

    // Stream rows from the appropriate format
    const stream = format === 'csv'
        ? streamCSV(args.input)
        : streamJSONL(args.input);

    for await (const row of stream) {
        if (args.sample !== null && processed >= args.sample) break;

        // Resolve source
        const slug = resolveSlug(row.source_canonical);
        if (!slug) {
            if (row.source_canonical) {
                // Only warn once per unknown source
                if (!sourceCounts[`__unknown_${row.source_canonical}`]) {
                    console.warn(`  [SKIP] Unknown source_canonical: "${row.source_canonical}"`);
                    sourceCounts[`__unknown_${row.source_canonical}`] = 0;
                }
                sourceCounts[`__unknown_${row.source_canonical}`]++;
            }
            skipped++;
            continue;
        }

        // Assign ID if missing
        const id = row.id || `cc_${slug}_${row.row_no || randomUUID()}`;

        const sourceName = getCanonicalName(slug);
        const displayLabel = CANONICAL_SOURCES[slug]?.displayLabel ?? sourceName;
        const matnFp = normalizeArabic(row.text_ar).slice(0, 120);

        // Generate title from source + row_no (row_no is always unique per hadith)
        // hadith_no is stored separately but is not unique for Ahmad/Shafi'i
        const title = `${displayLabel} ${row.row_no || row.hadith_no || id}`;

        // Extract primary topic from comma-separated topics
        const primaryTopic = (row.topics || '').split(',')[0].trim() || '';

        try {
            await ensureSource(sourceName, slug, sourceCache, args.dryRun);

            hadithBatch.push({
                id,
                title,
                primary_topic: primaryTopic,
                source: sourceName,
                source_slug: slug,
                hadith_no: row.hadith_no,
                text_arabic: row.text_ar,
                text_english: row.text_en,
                isnad_arabic: row.chain,
                chain_text_arabic: row.chain,
                topics: row.topics,
                display_grade: 'THABIT',
                transmission_type: '',
                tradition: '',
                matn_fingerprint: matnFp,
                source_role: 'PRIMARY_COLLECTION',
                shelf_no: row.shelf_no,
            });

            fromSourceBatch.push({ hadith_id: id, source_name: sourceName });
            inSchoolBatch.push(id);

            sourceCounts[slug] = (sourceCounts[slug] ?? 0) + 1;
            processed++;
        } catch (err) {
            console.error(`  [ERROR] id=${id}:`, err);
            errors++;
        }

        if (hadithBatch.length >= args.batchSize) {
            await flushBatch();
        }
    }

    // Flush remaining
    if (hadithBatch.length > 0) {
        await flushBatch();
    }

    // Summary
    const elapsed = Date.now() - startedAt.getTime();
    console.log('\n' + '='.repeat(70));
    console.log('  Import ' + (args.dryRun ? 'Dry-Run ' : '') + 'Complete');
    console.log('='.repeat(70));
    console.log(`  Processed:   ${formatNum(processed)}`);
    console.log(`  Skipped:     ${formatNum(skipped)}`);
    console.log(`  Errors:      ${formatNum(errors)}`);
    console.log(`  Duration:    ${formatDuration(elapsed)}`);
    console.log('\n  Per source:');
    for (const [key, count] of Object.entries(sourceCounts)) {
        if (!key.startsWith('__')) {
            const name = CANONICAL_SOURCES[key]?.displayLabel ?? key;
            console.log(`    ${name}: ${formatNum(count)}`);
        }
    }

    if (args.dryRun) {
        console.log('\n  [DRY-RUN] No writes were issued to Neo4j.');
    }

    console.log('');
}

main()
    .catch((err) => {
        console.error('\nFatal error:', err);
        process.exit(1);
    })
    .finally(() => closeDriver());
