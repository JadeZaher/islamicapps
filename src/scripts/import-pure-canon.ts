/**
 * import-pure-canon.ts
 * ====================
 * Import translated Pure-Canon-Authentica JSONL files into Neo4j.
 *
 * Reads a JSONL file where each line is a JSON object representing either:
 *   - A classical hadith row (from Bukhari, Muslim, etc.)
 *   - An anthology row (from al-Albani, al-Talidi, al-Ghumari, etc.)
 *
 * The row is classified by its `source_book_slug` field. Classical rows are
 * stored directly as Hadith nodes linked to a Source node. Anthology rows
 * attempt to match an existing classical Hadith via matn fingerprint; if
 * matched, a ScholarVerdict node is created; otherwise the row is stored as
 * a standalone Hadith with source_role='ANTHOLOGY_STANDALONE'.
 *
 * Usage:
 *   npm run db:import:pure-canon -- --input <path/to/file.jsonl>
 *   tsx src/scripts/import-pure-canon.ts --input datasets/pure_canon.jsonl
 *   tsx src/scripts/import-pure-canon.ts --input ... --dry-run
 *   tsx src/scripts/import-pure-canon.ts --input ... --resume
 *   tsx src/scripts/import-pure-canon.ts --input ... --sample 500
 *   tsx src/scripts/import-pure-canon.ts --input ... --batch-size 500 --skip-matn-match
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { randomUUID } from 'crypto';

import { loadEnv } from './lib/env';
import { runQuery, runWrite, runTransaction, closeDriver } from '../lib/db/neo4j';
import { mergeNodeByKey, mergeEdge } from '../lib/db/neo4j-helpers';
import { normalizeArabic } from '../lib/import/canon-normalize';
import { getCanonicalName } from '../lib/constants/sources';

// ─── Constants ────────────────────────────────────────────────────────────────

const CHECKPOINT_PATH = path.join(process.cwd(), '.omc', 'state', 'pure-canon-import.json');

/** Classical source slugs → English display name */
const CLASSICAL_SOURCE_NAMES: Record<string, string> = {
    bukhari:   getCanonicalName('bukhari'),
    muslim:    getCanonicalName('muslim'),
    abudawud:  getCanonicalName('abudawud'),
    tirmidhi:  getCanonicalName('tirmidhi'),
    nasai:     getCanonicalName('nasai'),
    ibnmajah:  getCanonicalName('ibnmajah'),
    muwatta:   getCanonicalName('muwatta'),
    darimi:    getCanonicalName('darimi'),
    ahmad:     getCanonicalName('ahmad'),
    shafii:    getCanonicalName('shafii'),
};

// ────────────────────────────────────────────────────────────────────────────
// ANTHOLOGY SOURCE DISPLAY NAMES
// ────────────────────────────────────────────────────────────────────────────
// These names label the Source nodes created for each modern anthology
// compilation. Research notes per slug:
//
// - albani (35,487 rows): aggregate across multiple Albani authentication
//   works (Sahih al-Jami' al-Saghir ~8.2k + Silsilat al-Ahadith al-Sahiha
//   ~4k + others). No single Albani publication contains 35k entries, so
//   this is necessarily a container label, not a single publication.
//
// - talidi (6,507 rows): "Tuhfat al-Qari" (تحفة القاري) is al-Talidi's
//   main hadith compilation per the daralhadith.org.uk biography.
//   NOT "Tuhfat al-Abrar" (that is a different work of his on awrad/adhkar).
//   Medium confidence — user should verify before first real import.
//
// - talidi_khasais (700 rows): "Tahdhib al-Khasa'is al-Nabawiyyah"
//   (تهذيب الخصائص النبوية) — direct match in al-Talidi's biographical
//   publications list. High confidence.
//
// - talidi_tafsir (1,489 rows): al-Talidi has "several tafsir-related
//   manuscripts" per his biography but no single tafsir-hadith publication
//   was located. Container label.
//
// - talidi_shifa (580 rows): could refer to al-Talidi's manuscript "Shifa
//   al-'Ilal..." OR to al-Qadi 'Iyad's "al-Shifa" with al-Talidi's
//   authentication overlays. Ambiguous — container label.
//
// - ghumari_qudsi (489 rows): al-Ghumari family Hadith Qudsi collection.
//   Could be compiled by Abdullah al-Ghumari (d. 1413 AH) or his elder
//   brother Ahmad al-Ghumari (d. 1380 AH). Container label.
//
// CHANGING THESE NAMES AFTER THE FIRST IMPORT requires either:
//   (a) re-running with --clear to rebuild the Source nodes, or
//   (b) a Cypher UPDATE targeting Source nodes by source_slug.
// ────────────────────────────────────────────────────────────────────────────
// All names are deliberate CONTAINER labels — no commitment to any specific
// published title. This keeps the first import safe: everything can be
// renamed in bulk later via src/scripts/rename-anthology-sources.ts when the
// authoritative titles are confirmed. The stable key is `source_slug` on the
// Source node; `name` is mutable display text.
const ANTHOLOGY_SOURCE_NAMES: Record<string, string> = {
    albani:          "al-Albani's Hadith Authentications",
    talidi:          "al-Talidi's Hadith Compilation",
    talidi_tafsir:   "al-Talidi's Tafsir Hadith Selections",
    talidi_khasais:  "al-Talidi's Khasa'is Selections",
    talidi_shifa:    "al-Talidi's Shifa' Hadith Selections",
    ghumari_qudsi:   "al-Ghumari's Hadith Qudsi Collection",
};

interface AnthologyScholarInfo {
    name_english: string;
    name_arabic: string;
    death_year_hijri: number;
    authority_rank: string;
}

const ANTHOLOGY_SCHOLARS: Record<string, AnthologyScholarInfo> = {
    albani:          { name_english: 'Muhammad Nasir al-Din al-Albani', name_arabic: 'محمد ناصر الدين الألباني', death_year_hijri: 1420, authority_rank: 'MODERN_MUHADDITH' },
    talidi:          { name_english: 'Abd Allah al-Talidi', name_arabic: 'عبد الله التليدي', death_year_hijri: 1437, authority_rank: 'MODERN_MUHADDITH' },
    talidi_tafsir:   { name_english: 'Abd Allah al-Talidi', name_arabic: 'عبد الله التليدي', death_year_hijri: 1437, authority_rank: 'MODERN_MUHADDITH' },
    talidi_khasais:  { name_english: 'Abd Allah al-Talidi', name_arabic: 'عبد الله التليدي', death_year_hijri: 1437, authority_rank: 'MODERN_MUHADDITH' },
    talidi_shifa:    { name_english: 'Abd Allah al-Talidi', name_arabic: 'عبد الله التليدي', death_year_hijri: 1437, authority_rank: 'MODERN_MUHADDITH' },
    ghumari_qudsi:   { name_english: "Abd Allah ibn al-Siddiq al-Ghumari", name_arabic: 'عبد الله بن الصديق الغماري', death_year_hijri: 1413, authority_rank: 'MODERN_MUHADDITH' },
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface JsonlRow {
    id: string;
    source_book_slug: string;
    hadith_no?: string;
    text_ar?: string;
    text_en?: string;
    isnad_ar?: string;
    topics?: string;
    [key: string]: unknown;
}

interface CliArgs {
    input: string;
    dryRun: boolean;
    sample: number | null;
    resume: boolean;
    batchSize: number;
    skipMatnMatch: boolean;
}

interface Checkpoint {
    input_file: string;
    last_processed_id: string;
    processed_count: number;
    classical_count: number;
    anthology_count: number;
    anthology_matched: number;
    anthology_standalone: number;
    skipped: number;
    errors: number;
    started_at: string;
    updated_at: string;
}

// ─── CLI Parsing ──────────────────────────────────────────────────────────────

function parseArgs(): CliArgs {
    const argv = process.argv.slice(2);
    const args: CliArgs = {
        input: '',
        dryRun: false,
        sample: null,
        resume: false,
        batchSize: 1000,
        skipMatnMatch: false,
    };

    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--input' && argv[i + 1]) {
            args.input = argv[++i];
        } else if (a === '--dry-run') {
            args.dryRun = true;
        } else if (a === '--sample' && argv[i + 1]) {
            args.sample = parseInt(argv[++i], 10);
        } else if (a === '--resume') {
            args.resume = true;
        } else if (a === '--batch-size' && argv[i + 1]) {
            args.batchSize = parseInt(argv[++i], 10);
        } else if (a === '--skip-matn-match') {
            args.skipMatnMatch = true;
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

// ─── Source slug helpers ──────────────────────────────────────────────────────

function isClassicalSlug(slug: string): boolean {
    return slug in CLASSICAL_SOURCE_NAMES;
}

function isAnthologySlug(slug: string): boolean {
    return slug in ANTHOLOGY_SCHOLARS;
}

/**
 * Derive the Scholar pipeline_key slug_root from a source_book_slug.
 * All Talidi sub-volume suffixes (talidi_tafsir, talidi_khasais, talidi_shifa)
 * collapse to "talidi" so they share a single Scholar node.
 */
function scholarSlugRoot(sourceSlug: string): string {
    if (sourceSlug.startsWith('talidi')) return 'talidi';
    return sourceSlug;
}

// ─── Checkpoint ───────────────────────────────────────────────────────────────

function readCheckpoint(): Checkpoint | null {
    if (!fs.existsSync(CHECKPOINT_PATH)) return null;
    try {
        return JSON.parse(fs.readFileSync(CHECKPOINT_PATH, 'utf8')) as Checkpoint;
    } catch {
        return null;
    }
}

function writeCheckpoint(cp: Checkpoint): void {
    const dir = path.dirname(CHECKPOINT_PATH);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(CHECKPOINT_PATH, JSON.stringify(cp, null, 2), 'utf8');
}

// ─── Progress printing ────────────────────────────────────────────────────────

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

function printProgress(
    batchIndex: number,
    totalBatches: number,
    processed: number,
    total: number,
    classical: number,
    anthology: number,
    matched: number,
    standalone: number,
    startedAt: Date
): void {
    const elapsed = Date.now() - startedAt.getTime();
    const rate = processed > 0 ? elapsed / processed : 0;
    const remaining = total - processed;
    const etaMs = rate * remaining;

    const eta = processed > 0 ? formatDuration(etaMs) : '?';
    const batchStr = String(batchIndex).padStart(String(totalBatches).length);
    console.log(
        `[batch ${batchStr}/${totalBatches}] ${formatNum(processed)}/${formatNum(total)} rows` +
        ` — ${formatNum(classical)} classical, ${formatNum(anthology)} anthology` +
        ` (${formatNum(matched)} matched, ${formatNum(standalone)} standalone)` +
        ` — ETA ${eta}`
    );
}

// ─── Count total rows ─────────────────────────────────────────────────────────

async function countLines(filePath: string): Promise<number> {
    return new Promise((resolve, reject) => {
        let count = 0;
        const rl = readline.createInterface({ input: fs.createReadStream(filePath, 'utf8') });
        rl.on('line', (line) => { if (line.trim()) count++; });
        rl.on('close', () => resolve(count));
        rl.on('error', reject);
    });
}

// ─── Neo4j batch helpers ──────────────────────────────────────────────────────

interface HadithBatchRow {
    id: string;
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
    chapter: string;
    chapter_no: string;
}

async function batchMergeHadiths(rows: HadithBatchRow[], dryRun: boolean): Promise<void> {
    if (rows.length === 0) return;
    if (dryRun) return;

    const cypher = `
        UNWIND $rows AS row
        MERGE (h:Hadith {id: row.id})
        ON CREATE SET
            h.source          = row.source,
            h.source_slug     = row.source_slug,
            h.chapter         = row.chapter,
            h.chapter_no      = row.chapter_no,
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
            h.created_at      = datetime()
        ON MATCH SET
            h.text_arabic     = row.text_arabic,
            h.text_english    = row.text_english,
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
    if (rows.length === 0) return;
    if (dryRun) return;

    const cypher = `
        UNWIND $rows AS row
        MATCH (h:Hadith {id: row.hadith_id})
        MATCH (s:Source {name: row.source_name})
        MERGE (h)-[:FROM_SOURCE]->(s)
    `;
    await runWrite(cypher, { rows });
}

async function batchMergeInSchoolEdges(hadithIds: string[], dryRun: boolean): Promise<void> {
    if (hadithIds.length === 0) return;
    if (dryRun) return;

    const cypher = `
        UNWIND $ids AS hadithId
        MATCH (h:Hadith {id: hadithId})
        MATCH (sch:SchoolOfThought {name: 'Sunni'})
        MERGE (h)-[:IN_SCHOOL]->(sch)
    `;
    await runWrite(cypher, { ids: hadithIds });
}

// ─── Ensure singleton nodes ───────────────────────────────────────────────────

async function ensureSunniSchool(dryRun: boolean): Promise<void> {
    if (dryRun) return;
    await mergeNodeByKey({
        label: 'SchoolOfThought',
        keyProp: 'name',
        keyValue: 'Sunni',
        createProps: { tradition: 'Sunni' },
    });
}

// ─── Matn fingerprint lookup ──────────────────────────────────────────────────

async function findClassicalHadithByFingerprint(
    fingerprint: string
): Promise<string | null> {
    if (!fingerprint) return null;

    const rows = await runQuery<{ id: string }>(
        `MATCH (h:Hadith {source_role: 'PRIMARY_COLLECTION'})
         WHERE h.matn_fingerprint = $fp
         RETURN h.id AS id
         LIMIT 1`,
        { fp: fingerprint }
    );

    return rows.length > 0 ? rows[0].id : null;
}

// ─── Scholar + Verdict creation ───────────────────────────────────────────────

async function ensureScholar(
    sourceSlug: string,
    scholarCache: Map<string, string>,
    dryRun: boolean
): Promise<string> {
    const slugRoot = scholarSlugRoot(sourceSlug);
    const cached = scholarCache.get(slugRoot);
    if (cached) return cached;

    const info = ANTHOLOGY_SCHOLARS[sourceSlug] ?? ANTHOLOGY_SCHOLARS[slugRoot];
    if (!info) {
        throw new Error(`Unknown anthology scholar for slug: ${sourceSlug}`);
    }

    const pipelineKey = `${slugRoot}::${info.death_year_hijri}`;

    if (dryRun) {
        // In dry-run we just pretend the id is the pipeline key
        scholarCache.set(slugRoot, pipelineKey);
        return pipelineKey;
    }

    const result = await mergeNodeByKey({
        label: 'Scholar',
        keyProp: 'pipeline_key',
        keyValue: pipelineKey,
        createProps: {
            name_english:       info.name_english,
            name_arabic:        info.name_arabic,
            death_year_hijri:   info.death_year_hijri,
            authority_rank:     info.authority_rank,
            tradition:          'Sunni',
        },
        mutableProps: {
            authority_rank: info.authority_rank,
        },
    });

    scholarCache.set(slugRoot, result.id);
    return result.id;
}

async function ensureSource(
    sourceName: string,
    sourceSlug: string,
    sourceCache: Map<string, string>,
    dryRun: boolean
): Promise<string> {
    const cached = sourceCache.get(sourceSlug);
    if (cached) return cached;

    if (dryRun) {
        sourceCache.set(sourceSlug, sourceName);
        return sourceName;
    }

    const result = await mergeNodeByKey({
        label: 'Source',
        keyProp: 'name',
        keyValue: sourceName,
        createProps: {
            source_slug: sourceSlug,
        },
        mutableProps: {
            source_slug: sourceSlug,
        },
    });

    sourceCache.set(sourceSlug, result.id);
    return result.id;
}

async function createScholarVerdict(
    hadithId: string,
    scholarId: string,
    sourceId: string,
    sourceSlug: string,
    dryRun: boolean
): Promise<void> {
    const pipelineKey = `${scholarId}::${hadithId}::${sourceSlug}`;

    if (dryRun) return;

    const verdictResult = await mergeNodeByKey({
        label: 'ScholarVerdict',
        keyProp: 'pipeline_key',
        keyValue: pipelineKey,
        createProps: {
            ruling: 'THABIT',
            notes: '',
        },
        mutableProps: {
            ruling: 'THABIT',
        },
    });

    // Hadith -[:HAS_VERDICT]-> ScholarVerdict
    await mergeEdge({
        fromLabel: 'Hadith',
        fromKey:   { prop: 'id', value: hadithId },
        toLabel:   'ScholarVerdict',
        toKey:     { prop: 'pipeline_key', value: pipelineKey },
        relType:   'HAS_VERDICT',
    });

    // ScholarVerdict -[:ISSUED_BY]-> Scholar
    await mergeEdge({
        fromLabel: 'ScholarVerdict',
        fromKey:   { prop: 'pipeline_key', value: pipelineKey },
        toLabel:   'Scholar',
        toKey:     { prop: 'id', value: scholarId },
        relType:   'ISSUED_BY',
    });

    // ScholarVerdict -[:PUBLISHED_IN]-> Source
    await mergeEdge({
        fromLabel: 'ScholarVerdict',
        fromKey:   { prop: 'pipeline_key', value: pipelineKey },
        toLabel:   'Source',
        toKey:     { prop: 'id', value: sourceId },
        relType:   'PUBLISHED_IN',
    });

    void verdictResult; // used only for side effect
}

async function linkScholarToSunni(scholarId: string, dryRun: boolean): Promise<void> {
    if (dryRun) return;
    await mergeEdge({
        fromLabel: 'Scholar',
        fromKey:   { prop: 'id', value: scholarId },
        toLabel:   'SchoolOfThought',
        toKey:     { prop: 'name', value: 'Sunni' },
        relType:   'OF_SCHOOL',
    });
}

async function linkSourceToSunni(sourceId: string, dryRun: boolean): Promise<void> {
    if (dryRun) return;
    await mergeEdge({
        fromLabel: 'Source',
        fromKey:   { prop: 'id', value: sourceId },
        toLabel:   'SchoolOfThought',
        toKey:     { prop: 'name', value: 'Sunni' },
        relType:   'CANON_OF',
    });
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
    loadEnv();

    const args = parseArgs();

    console.log('='.repeat(70));
    console.log('  Pure-Canon-Authentica -> Neo4j Import');
    console.log('='.repeat(70));
    console.log(`\nInput file:  ${args.input}`);
    console.log(`Batch size:  ${args.batchSize}`);
    console.log(`Dry run:     ${args.dryRun}`);
    console.log(`Skip matn:   ${args.skipMatnMatch}`);
    console.log(`Resume:      ${args.resume}`);
    if (args.sample !== null) console.log(`Sample:      ${args.sample}`);

    // Count total rows for ETA
    console.log('\nCounting rows...');
    const totalRows = args.sample !== null
        ? args.sample
        : await countLines(args.input);
    console.log(`Total rows:  ${formatNum(totalRows)}`);
    const totalBatches = Math.ceil(totalRows / args.batchSize);

    // Load checkpoint for --resume
    let lastProcessedId = '';
    let skipCount = 0;
    if (args.resume) {
        const cp = readCheckpoint();
        if (cp && cp.input_file === args.input) {
            lastProcessedId = cp.last_processed_id;
            console.log(`\nResuming from id: ${lastProcessedId} (${formatNum(cp.processed_count)} already done)`);
        } else {
            console.log('\nNo matching checkpoint found — starting from beginning.');
        }
    }

    // Ensure SchoolOfThought:Sunni exists up front
    await ensureSunniSchool(args.dryRun);

    // In-memory caches for one-off nodes
    const sourceCache = new Map<string, string>();  // sourceSlug -> node id (or name in dry-run)
    const scholarCache = new Map<string, string>(); // slugRoot   -> node id (or pipeline_key in dry-run)

    // Counters
    let processed = 0;
    let classicalCount = 0;
    let anthologyCount = 0;
    let anthologyMatched = 0;
    let anthologyStandalone = 0;
    let errors = 0;
    let resumeSkipped = 0;
    const startedAt = new Date();

    // Batch buffers
    let hadithBatch: HadithBatchRow[] = [];
    let fromSourceBatch: EdgeBatchRow[] = [];
    let inSchoolBatch: string[] = [];
    let batchIndex = 0;

    const checkpoint: Checkpoint = {
        input_file:           args.input,
        last_processed_id:    lastProcessedId,
        processed_count:      0,
        classical_count:      0,
        anthology_count:      0,
        anthology_matched:    0,
        anthology_standalone: 0,
        skipped:              resumeSkipped,
        errors:               0,
        started_at:           startedAt.toISOString(),
        updated_at:           startedAt.toISOString(),
    };

    const flushBatch = async (): Promise<void> => {
        batchIndex++;

        await batchMergeHadiths(hadithBatch, args.dryRun);
        await batchMergeFromSourceEdges(fromSourceBatch, args.dryRun);
        await batchMergeInSchoolEdges(inSchoolBatch, args.dryRun);

        hadithBatch = [];
        fromSourceBatch = [];
        inSchoolBatch = [];

        // Update + write checkpoint
        checkpoint.processed_count      = processed;
        checkpoint.classical_count      = classicalCount;
        checkpoint.anthology_count      = anthologyCount;
        checkpoint.anthology_matched    = anthologyMatched;
        checkpoint.anthology_standalone = anthologyStandalone;
        checkpoint.skipped              = resumeSkipped + skipCount;
        checkpoint.errors               = errors;
        checkpoint.updated_at           = new Date().toISOString();

        if (!args.dryRun) {
            writeCheckpoint(checkpoint);
        }

        printProgress(
            batchIndex, totalBatches,
            processed, totalRows,
            classicalCount, anthologyCount,
            anthologyMatched, anthologyStandalone,
            startedAt
        );
    };

    // Stream JSONL
    const rl = readline.createInterface({
        input: fs.createReadStream(args.input, 'utf8'),
        crlfDelay: Infinity,
    });

    for await (const line of rl) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (args.sample !== null && (processed + resumeSkipped) >= args.sample) break;

        let row: JsonlRow;
        try {
            row = JSON.parse(trimmed) as JsonlRow;
        } catch (err) {
            console.error(`  JSON parse error on line: ${trimmed.slice(0, 80)}`);
            errors++;
            continue;
        }

        if (!row.id) {
            row.id = randomUUID();
        }

        // --resume: skip rows we've already processed
        if (args.resume && lastProcessedId && row.id <= lastProcessedId) {
            resumeSkipped++;
            skipCount++;
            continue;
        }

        const slug = (row.source_book_slug ?? '').toLowerCase().trim();

        try {
            if (isClassicalSlug(slug)) {
                // ── Classical row ──────────────────────────────────────────
                const sourceName = CLASSICAL_SOURCE_NAMES[slug];
                const matnFp = normalizeArabic(row.text_ar ?? '').slice(0, 120);

                hadithBatch.push({
                    id:                 row.id,
                    source:             sourceName,
                    source_slug:        slug,
                    chapter:            '',
                    chapter_no:         '',
                    hadith_no:          String(row.hadith_no ?? ''),
                    text_arabic:        row.text_ar ?? '',
                    text_english:       row.text_en ?? '',
                    isnad_arabic:       row.isnad_ar ?? '',
                    chain_text_arabic:  row.isnad_ar ?? '',
                    topics:             typeof row.topics === 'string' ? row.topics : '',
                    display_grade:      'THABIT',
                    transmission_type:  '',
                    tradition:          '',
                    matn_fingerprint:   matnFp,
                    source_role:        'PRIMARY_COLLECTION',
                });

                // Ensure Source node is cached
                await ensureSource(sourceName, slug, sourceCache, args.dryRun);

                fromSourceBatch.push({ hadith_id: row.id, source_name: sourceName });
                inSchoolBatch.push(row.id);

                // Source -[:CANON_OF]-> SchoolOfThought:Sunni (only first time)
                if (!sourceCache.has(`__sunni_linked_${slug}`)) {
                    const srcId = sourceCache.get(slug) ?? sourceName;
                    await linkSourceToSunni(srcId, args.dryRun);
                    sourceCache.set(`__sunni_linked_${slug}`, '1');
                }

                classicalCount++;

            } else if (isAnthologySlug(slug)) {
                // ── Anthology row ──────────────────────────────────────────
                anthologyCount++;

                const anthologySourceName = ANTHOLOGY_SOURCE_NAMES[slug];
                const matnFp = normalizeArabic(row.text_ar ?? '').slice(0, 120);

                let targetHadithId: string | null = null;

                if (!args.skipMatnMatch && matnFp.length > 10) {
                    targetHadithId = await findClassicalHadithByFingerprint(matnFp);
                }

                // Ensure Scholar + Source nodes cached
                const scholarId = await ensureScholar(slug, scholarCache, args.dryRun);
                await ensureSource(anthologySourceName, slug, sourceCache, args.dryRun);
                const srcId = sourceCache.get(slug) ?? anthologySourceName;

                // Scholar -[:OF_SCHOOL]-> Sunni (first time per slug root)
                const slugRoot = scholarSlugRoot(slug);
                if (!sourceCache.has(`__scholar_sunni_${slugRoot}`)) {
                    await linkScholarToSunni(scholarId, args.dryRun);
                    sourceCache.set(`__scholar_sunni_${slugRoot}`, '1');
                }

                // Source -[:CANON_OF]-> Sunni (first time per slug)
                if (!sourceCache.has(`__sunni_linked_${slug}`)) {
                    await linkSourceToSunni(srcId, args.dryRun);
                    sourceCache.set(`__sunni_linked_${slug}`, '1');
                }

                if (targetHadithId) {
                    // Matched: only create ScholarVerdict
                    anthologyMatched++;
                    await createScholarVerdict(targetHadithId, scholarId, srcId, slug, args.dryRun);

                } else {
                    // Standalone: create a new Hadith node for the anthology row
                    anthologyStandalone++;

                    hadithBatch.push({
                        id:                 row.id,
                        source:             anthologySourceName,
                        source_slug:        slug,
                        chapter:            '',
                        chapter_no:         '',
                        hadith_no:          String(row.hadith_no ?? ''),
                        text_arabic:        row.text_ar ?? '',
                        text_english:       row.text_en ?? '',
                        isnad_arabic:       row.isnad_ar ?? '',
                        chain_text_arabic:  row.isnad_ar ?? '',
                        topics:             typeof row.topics === 'string' ? row.topics : '',
                        display_grade:      'THABIT',
                        transmission_type:  '',
                        tradition:          '',
                        matn_fingerprint:   matnFp,
                        source_role:        'ANTHOLOGY_STANDALONE',
                    });

                    fromSourceBatch.push({ hadith_id: row.id, source_name: anthologySourceName });
                    inSchoolBatch.push(row.id);

                    // Also create ScholarVerdict pointing at this new standalone hadith
                    // We can't do this in the UNWIND batch since the Hadith node must
                    // exist first. Queue it to run post-flush via deferred list.
                    // For simplicity we flush eagerly when a standalone is encountered
                    // so the Hadith node is available for the verdict link.
                    await batchMergeHadiths(hadithBatch, args.dryRun);
                    await batchMergeFromSourceEdges(fromSourceBatch, args.dryRun);
                    await batchMergeInSchoolEdges(inSchoolBatch, args.dryRun);
                    hadithBatch = [];
                    fromSourceBatch = [];
                    inSchoolBatch = [];

                    await createScholarVerdict(row.id, scholarId, srcId, slug, args.dryRun);
                }

            } else {
                // Unknown slug — log and skip
                console.warn(`  [SKIP] Unknown source_book_slug: "${slug}" (id: ${row.id})`);
                errors++;
                continue;
            }

            processed++;
            checkpoint.last_processed_id = row.id;

        } catch (err) {
            console.error(`  [ERROR] row id=${row.id} slug=${slug}:`, err);
            errors++;
        }

        // Flush batch when full
        if (hadithBatch.length >= args.batchSize) {
            await flushBatch();
        }
    }

    // Flush remaining rows
    if (hadithBatch.length > 0 || fromSourceBatch.length > 0 || inSchoolBatch.length > 0) {
        await flushBatch();
    } else if (processed > 0) {
        // Still print last progress line even if nothing to flush
        printProgress(
            batchIndex, totalBatches,
            processed, totalRows,
            classicalCount, anthologyCount,
            anthologyMatched, anthologyStandalone,
            startedAt
        );
    }

    // Final summary
    console.log('\n' + '='.repeat(70));
    console.log('  Import ' + (args.dryRun ? 'Dry-Run ' : '') + 'Complete');
    console.log('='.repeat(70));
    console.log(`  Processed:           ${formatNum(processed)}`);
    console.log(`  Classical:           ${formatNum(classicalCount)}`);
    console.log(`  Anthology total:     ${formatNum(anthologyCount)}`);
    console.log(`    Matched:           ${formatNum(anthologyMatched)}`);
    console.log(`    Standalone:        ${formatNum(anthologyStandalone)}`);
    console.log(`  Skipped (resume):    ${formatNum(resumeSkipped)}`);
    console.log(`  Errors:              ${formatNum(errors)}`);
    console.log(`  Duration:            ${formatDuration(Date.now() - startedAt.getTime())}`);

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
