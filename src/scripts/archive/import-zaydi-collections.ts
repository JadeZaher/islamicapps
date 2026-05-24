// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * import-zaydi-collections.ts
 * ===========================
 * Import Zaydi Shia hadith collections from parsed_zaydi_hadiths.json into Neo4j.
 *
 * Creates:
 *   - Source node for Musnad Zayd ibn Ali
 *   - Hadith nodes with text, sanad, chapter info
 *   - FROM_SOURCE, IN_SCHOOL, and CANON_OF edges
 *   - Links to SchoolOfThought:Shia Zaydi
 *
 * Usage:
 *   tsx src/scripts/import-zaydi-collections.ts
 *   tsx src/scripts/import-zaydi-collections.ts --dry-run
 *   tsx src/scripts/import-zaydi-collections.ts --sample 50
 */

import fs from 'fs';
import path from 'path';

import { loadEnv } from './lib/env';
import { runWrite, closeDriver } from '../lib/db/neo4j';
import { mergeNodeByKey, mergeEdge } from '../lib/db/neo4j-helpers';

loadEnv();

// ─── Constants ──────────────────────────────────────────────────────────────

const SOURCE_SLUG = 'musnad_zayd';
const SOURCE_NAME = 'Musnad al-Imam Zayd ibn Ali';
const SOURCE_NAME_AR = 'مسند الإمام زيد بن علي';
const SCHOOL_NAME = 'Shia Zaydi';
const COMPILER = 'Abd al-Aziz ibn Ishaq al-Baghdadi';

// ─── Types ──────────────────────────────────────────────────────────────────

interface ParsedHadith {
  hadith_no: number;
  chapter_no: number;
  chapter_name_ar: string;
  text_arabic: string;
  text_english?: string;
  sanad: string;
  matn_ar: string;
  source_line: number;
}

interface ParsedData {
  source: string;
  source_ar: string;
  school: string;
  compiler: string;
  compiler_ar: string;
  total_hadiths: number;
  hadiths: ParsedHadith[];
}

interface CliArgs {
  dryRun: boolean;
  sample: number | null;
  batchSize: number;
}

// ─── CLI ────────────────────────────────────────────────────────────────────

function parseArgs(): CliArgs {
  const argv = process.argv.slice(2);
  const args: CliArgs = { dryRun: false, sample: null, batchSize: 200 };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--sample' && argv[i + 1]) args.sample = parseInt(argv[++i], 10);
    else if (a === '--batch-size' && argv[i + 1]) args.batchSize = parseInt(argv[++i], 10);
  }

  return args;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatNum(n: number): string {
  return n.toLocaleString('en-US');
}

function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem > 0 ? `${m}m${rem}s` : `${m}m`;
}

// ─── Neo4j batch operations ─────────────────────────────────────────────────

interface HadithBatchRow {
  id: string;
  title: string;
  primary_topic: string;
  source: string;
  source_slug: string;
  volume: number;
  chapter: string;
  chapter_no: number;
  hadith_no: number;
  text_arabic: string;
  text_english: string;
  sanad_text: string;
  matn_arabic: string;
  tradition: string;
  source_role: string;
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
      h.volume          = row.volume,
      h.chapter         = row.chapter,
      h.chapter_no      = row.chapter_no,
      h.hadith_no       = row.hadith_no,
      h.text_arabic     = row.text_arabic,
      h.text_english    = row.text_english,
      h.sanad_text      = row.sanad_text,
      h.matn_arabic     = row.matn_arabic,
      h.tradition       = row.tradition,
      h.source_role     = row.source_role,
      h.created_at      = datetime()
    ON MATCH SET
      h.text_arabic     = row.text_arabic,
      h.sanad_text      = row.sanad_text,
      h.matn_arabic     = row.matn_arabic,
      h.updated_at      = datetime()
  `;
  await runWrite(cypher, { rows });
}

async function batchMergeFromSourceEdges(
  ids: string[],
  dryRun: boolean
): Promise<void> {
  if (ids.length === 0 || dryRun) return;

  const cypher = `
    UNWIND $ids AS hadithId
    MATCH (h:Hadith {id: hadithId})
    MATCH (s:Source {name: $sourceName})
    MERGE (h)-[:FROM_SOURCE]->(s)
  `;
  await runWrite(cypher, { ids, sourceName: SOURCE_NAME });
}

async function batchMergeInSchoolEdges(ids: string[], dryRun: boolean): Promise<void> {
  if (ids.length === 0 || dryRun) return;

  const cypher = `
    UNWIND $ids AS hadithId
    MATCH (h:Hadith {id: hadithId})
    MATCH (sch:SchoolOfThought {name: $schoolName})
    MERGE (h)-[:IN_SCHOOL]->(sch)
  `;
  await runWrite(cypher, { ids, schoolName: SCHOOL_NAME });
}

// ─── Ensure singleton nodes ─────────────────────────────────────────────────

async function ensureSchool(dryRun: boolean): Promise<void> {
  if (dryRun) return;

  await mergeNodeByKey({
    label: 'SchoolOfThought',
    keyProp: 'name',
    keyValue: SCHOOL_NAME,
    createProps: { tradition: 'Shia Zaydi', name_arabic: 'الشيعة الزيدية' },
  });
  console.log(`  Ensured SchoolOfThought: ${SCHOOL_NAME}`);
}

async function ensureSource(dryRun: boolean): Promise<void> {
  if (dryRun) return;

  const result = await mergeNodeByKey({
    label: 'Source',
    keyProp: 'name',
    keyValue: SOURCE_NAME,
    createProps: {
      source_slug: SOURCE_SLUG,
      name_arabic: SOURCE_NAME_AR,
      compiler: COMPILER,
    },
  });

  // Source -> Shia Zaydi school
  await mergeEdge({
    fromLabel: 'Source',
    fromKey: { prop: 'id', value: result.id },
    toLabel: 'SchoolOfThought',
    toKey: { prop: 'name', value: SCHOOL_NAME },
    relType: 'CANON_OF',
  });

  console.log(`  Source: ${SOURCE_NAME} (${SOURCE_SLUG})`);
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs();

  const jsonPath = path.join(
    process.cwd(),
    'datasets/hadith-data/zaydi-hadith/parsed_zaydi_hadiths.json'
  );

  if (!fs.existsSync(jsonPath)) {
    console.error(`ERROR: JSON not found at ${jsonPath}`);
    console.error('Run parse_musnad_zayd.py first.');
    process.exit(1);
  }

  const data: ParsedData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));

  console.log('='.repeat(70));
  console.log('  Zaydi Collections -> Neo4j Import');
  console.log('='.repeat(70));
  console.log(`\nInput:       ${jsonPath}`);
  console.log(`Total:       ${data.total_hadiths} hadiths`);
  console.log(`Batch size:  ${args.batchSize}`);
  console.log(`Dry run:     ${args.dryRun}`);
  if (args.sample !== null) console.log(`Sample:      ${args.sample}`);

  // Ensure school and source
  await ensureSchool(args.dryRun);
  await ensureSource(args.dryRun);

  let processed = 0;
  let errors = 0;
  const startedAt = Date.now();

  let hadithBatch: HadithBatchRow[] = [];
  let idBatch: string[] = [];
  let batchIndex = 0;

  const hadiths = args.sample !== null
    ? data.hadiths.slice(0, args.sample)
    : data.hadiths;

  const flushBatch = async (): Promise<void> => {
    batchIndex++;
    await batchMergeHadiths(hadithBatch, args.dryRun);
    await batchMergeFromSourceEdges(idBatch, args.dryRun);
    await batchMergeInSchoolEdges(idBatch, args.dryRun);

    const elapsed = Date.now() - startedAt;
    console.log(
      `  [batch ${batchIndex}] ${formatNum(processed)} rows — ${formatDuration(elapsed)} elapsed`
    );

    hadithBatch = [];
    idBatch = [];
  };

  for (const h of hadiths) {
    try {
      const id = `zaydi_${SOURCE_SLUG}_${h.hadith_no}`;
      const title = `${SOURCE_NAME} #${h.hadith_no}`;

      hadithBatch.push({
        id,
        title,
        primary_topic: h.chapter_name_ar || 'General',
        source: SOURCE_NAME,
        source_slug: SOURCE_SLUG,
        volume: 1,
        chapter: h.chapter_name_ar,
        chapter_no: h.chapter_no,
        hadith_no: h.hadith_no,
        text_arabic: h.text_arabic,
        text_english: h.text_english || '',
        sanad_text: h.sanad,
        matn_arabic: h.matn_ar,
        tradition: 'Shia Zaydi',
        source_role: 'PRIMARY_COLLECTION',
      });

      idBatch.push(id);
      processed++;
    } catch (err) {
      console.error(`  [ERROR] hadith #${h.hadith_no}:`, err);
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
  const elapsed = Date.now() - startedAt;
  console.log('\n' + '='.repeat(70));
  console.log('  Import ' + (args.dryRun ? 'Dry-Run ' : '') + 'Complete');
  console.log('='.repeat(70));
  console.log(`  Processed:   ${formatNum(processed)}`);
  console.log(`  Errors:      ${formatNum(errors)}`);
  console.log(`  Duration:    ${formatDuration(elapsed)}`);

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
