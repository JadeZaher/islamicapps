/**
 * import-shia-collections.ts
 * ==========================
 * Import Shia hadith collections from all_hadiths_shia.csv into Neo4j.
 *
 * Creates:
 *   - SchoolOfThought:Shia node
 *   - Source nodes for each Shia collection
 *   - Hadith nodes with text, grading, sanad, etc.
 *   - FROM_SOURCE and IN_SCHOOL edges
 *
 * Usage:
 *   tsx src/scripts/import-shia-collections.ts
 *   tsx src/scripts/import-shia-collections.ts --dry-run
 *   tsx src/scripts/import-shia-collections.ts --sample 500
 *   tsx src/scripts/import-shia-collections.ts --batch-size 500
 */

import fs from 'fs';
import path from 'path';
import { randomUUID } from 'crypto';

import { loadEnv } from './lib/env';
import { runWrite, closeDriver } from '../lib/db/neo4j';
import { mergeNodeByKey, mergeEdge } from '../lib/db/neo4j-helpers';

loadEnv();

// ─── Source mapping: CSV "source" field -> slug ─────────────────────────────

const SOURCE_NAME_TO_SLUG: Record<string, string> = {
  'Al-Kāfi': 'kafi',
  'Man Lā Yaḥḍuruh al-Faqīh': 'faqih',
  'Nahj al-Balāgha': 'nahj_balagha',
  'Al-Amālī': 'amali_saduq', // Saduq's Amali (1082) vs Mufid's (387) — disambiguated by count
  'Al-Khiṣāl': 'khisal',
  'Kitāb al-Ghayba': 'ghayba_tusi', // disambiguation handled below
  'Thawāb al-Aʿmāl wa ʿiqāb al-Aʿmāl': 'thawab_amal',
  'ʿUyūn akhbār al-Riḍā': 'uyun_rida',
  'Maʿānī al-ʾAkhbār': 'maani_akhbar',
  'Kāmil al-Ziyārāt': 'kamil_ziyarat',
  'Kamāl al-Dīn wa Tamām al-Niʿma': 'kamal_din',
  'Al-Tawḥīd': 'tawhid_saduq',
  'Muʿjam al-Aḥādīth al-Muʿtabara': 'mujam_mutabara',
  'Kitāb al-Zuhd': 'zuhd_ahwazi',
  'Kitāb al-Ḍuʿafāʾ': 'duafa_ghadairi',
  'Kitāb al-Muʾmin': 'mumin_ahwazi',
  'Ṣifāt al-Shīʿa': 'sifat_shia',
  'Faḍaʾil al-Shīʿa': 'fadail_shia',
  'Risālat al-Ḥuqūq': 'huquq_abidin',
};

// Slug -> canonical name (from CANONICAL_SOURCES)
const SLUG_TO_CANONICAL: Record<string, string> = {
  kafi: 'Al-Kafi',
  faqih: 'Man La Yahduruhu al-Faqih',
  nahj_balagha: 'Nahj al-Balagha',
  amali_saduq: 'Al-Amali (Saduq)',
  amali_mufid: 'Al-Amali (Mufid)',
  khisal: 'Al-Khisal',
  ghayba_tusi: 'Kitab al-Ghayba (Tusi)',
  ghayba_numani: 'Kitab al-Ghayba (Nu\'mani)',
  thawab_amal: 'Thawab al-A\'mal',
  uyun_rida: '\'Uyun Akhbar al-Rida',
  maani_akhbar: 'Ma\'ani al-Akhbar',
  kamil_ziyarat: 'Kamil al-Ziyarat',
  kamal_din: 'Kamal al-Din',
  tawhid_saduq: 'Al-Tawhid (Saduq)',
  mujam_mutabara: 'Mu\'jam al-Ahadith al-Mu\'tabara',
  zuhd_ahwazi: 'Kitab al-Zuhd',
  duafa_ghadairi: 'Kitab al-Du\'afa',
  mumin_ahwazi: 'Kitab al-Mu\'min',
  sifat_shia: 'Sifat al-Shi\'a',
  fadail_shia: 'Fada\'il al-Shi\'a',
  huquq_abidin: 'Risalat al-Huquq',
};

// ─── Disambiguation: bookId-based slug resolution ───────────────────────────

const BOOKID_TO_SLUG: Record<string, string> = {
  'Al-Kafi-Volume-1-Kulayni': 'kafi',
  'Al-Kafi-Volume-2-Kulayni': 'kafi',
  'Al-Kafi-Volume-3-Kulayni': 'kafi',
  'Al-Kafi-Volume-4-Kulayni': 'kafi',
  'Al-Kafi-Volume-5-Kulayni': 'kafi',
  'Al-Kafi-Volume-6-Kulayni': 'kafi',
  'Al-Kafi-Volume-7-Kulayni': 'kafi',
  'Al-Kafi-Volume-8-Kulayni': 'kafi',
  'Mujam-al-Ahadith-al-Mutabara-Muhsini': 'mujam_mutabara',
  'Al-Khisal-Saduq': 'khisal',
  'Uyun-akhbar-al-Rida-Volume-1-Saduq': 'uyun_rida',
  'Uyun-akhbar-al-Rida-Volume-2-Saduq': 'uyun_rida',
  'Al-Amali-Mufid': 'amali_mufid',
  'Al-Amali-Saduq': 'amali_saduq',
  'Al-Tawhid-Saduq': 'tawhid_saduq',
  'Kitab-al-Duafa-Ghadairi': 'duafa_ghadairi',
  'Kitab-al-Ghayba-Numani': 'ghayba_numani',
  'Kitab-al-Ghayba-Tusi': 'ghayba_tusi',
  'Thawab-al-Amal-wa-iqab-al-Amal-Saduq': 'thawab_amal',
  'Kamil-al-Ziyarat-Qummi': 'kamil_ziyarat',
  'Fadail-al-Shia-Saduq': 'fadail_shia',
  'Sifat-al-Shia-Saduq': 'sifat_shia',
  'Nahj-al-Balagha-Radi': 'nahj_balagha',
  'Risalat-al-Huquq-Abidin': 'huquq_abidin',
  'Man-La-Yahduruh-al-Faqih-Volume-1-Saduq': 'faqih',
  'Man-La-Yahduruh-al-Faqih-Volume-2-Saduq': 'faqih',
  'Man-La-Yahduruh-al-Faqih-Volume-3-Saduq': 'faqih',
  'Man-La-Yahduruh-al-Faqih-Volume-4-Saduq': 'faqih',
  'Man-La-Yahduruh-al-Faqih-Volume-5-Saduq': 'faqih',
  'Kamal-al-Din-wa-Tamam-al-Nima-Saduq': 'kamal_din',
  'Maani-al-Akhbar-Saduq': 'maani_akhbar',
  'Kitab-al-Mumin-Ahwazi': 'mumin_ahwazi',
  'Kitab-al-Zuhd-Ahwazi': 'zuhd_ahwazi',
};

// ─── Types ───────────────────────────────────────────────────────────────────

interface CSVRow {
  id: string;
  hadith_id: string;
  source: string;
  volume: string;
  chapter_no: string;
  hadith_no: string;
  chapter: string;
  category: string;
  chain_indx: string;
  text_ar: string;
  text_en: string;
  sanad: string;
  matn_en: string;
  grading_majlisi: string;
  grading_mohseni: string;
  grading_behbudi: string;
  gradings_full: string;
  url: string;
}

interface CliArgs {
  dryRun: boolean;
  sample: number | null;
  batchSize: number;
}

// ─── CLI Parsing ─────────────────────────────────────────────────────────────

function parseArgs(): CliArgs {
  const argv = process.argv.slice(2);
  const args: CliArgs = { dryRun: false, sample: null, batchSize: 500 };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--sample' && argv[i + 1]) args.sample = parseInt(argv[++i], 10);
    else if (a === '--batch-size' && argv[i + 1]) args.batchSize = parseInt(argv[++i], 10);
  }

  return args;
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

async function* streamCSV(filePath: string): AsyncGenerator<CSVRow> {
  const content = fs.readFileSync(filePath, 'utf8');
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

  const headers = parseCSVLine(lines[0]).map(h => h.trim());

  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    const row: Record<string, string> = {};
    for (let j = 0; j < headers.length; j++) {
      row[headers[j]] = (values[j] ?? '').trim();
    }
    yield row as unknown as CSVRow;
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

// ─── Resolve slug from CSV row ──────────────────────────────────────────────

function resolveSlug(sourceName: string, url: string): string | null {
  // Try URL-based bookId extraction for disambiguation
  // URL pattern: https://thaqalayn.net/hadith/{bookNum}/{vol}/{cat}/{hadith}
  // We embedded bookId info into the CSV via the source field, but for
  // ambiguous cases (Al-Amali, Kitab al-Ghayba) we need the URL booknum
  const urlMatch = url.match(/thaqalayn\.net\/hadith\/(\d+)\//);
  if (urlMatch) {
    const bookNum = parseInt(urlMatch[1], 10);
    // Map book numbers to known bookIds for disambiguation
    if (bookNum === 13) return 'amali_mufid';
    if (bookNum === 29) return 'amali_saduq';
    if (bookNum === 22) return 'ghayba_numani';
    if (bookNum === 27) return 'ghayba_tusi';
  }

  // Direct name lookup
  const slug = SOURCE_NAME_TO_SLUG[sourceName];
  if (slug) return slug;

  // Fuzzy fallback
  for (const [name, s] of Object.entries(SOURCE_NAME_TO_SLUG)) {
    if (sourceName.includes(name) || name.includes(sourceName)) return s;
  }

  return null;
}

// ─── Grading resolution ─────────────────────────────────────────────────────

function resolveGrading(row: CSVRow): { display_grade: string; grading_detail: string } {
  // Priority: Majlisi > Mohseni > Behbudi
  const majlisi = row.grading_majlisi?.trim() || '';
  const mohseni = row.grading_mohseni?.trim() || '';
  const behbudi = row.grading_behbudi?.trim() || '';

  const display_grade = majlisi || mohseni || behbudi || '';
  const grading_detail = row.gradings_full?.trim() || '';

  return { display_grade, grading_detail };
}

// ─── Neo4j batch merge ───────────────────────────────────────────────────────

interface HadithBatchRow {
  id: string;
  title: string;
  primary_topic: string;
  source: string;
  source_slug: string;
  volume: number | null;
  chapter: string;
  chapter_no: string;
  hadith_no: string;
  text_arabic: string;
  text_english: string;
  sanad_text: string;
  matn_english: string;
  display_grade: string;
  grading_detail: string;
  tradition: string;
  source_role: string;
  url: string;
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
      h.matn_english    = row.matn_english,
      h.display_grade   = row.display_grade,
      h.grading_detail  = row.grading_detail,
      h.tradition       = row.tradition,
      h.source_role     = row.source_role,
      h.url             = row.url,
      h.created_at      = datetime()
    ON MATCH SET
      h.text_arabic     = row.text_arabic,
      h.text_english    = row.text_english,
      h.sanad_text      = row.sanad_text,
      h.matn_english    = row.matn_english,
      h.display_grade   = row.display_grade,
      h.grading_detail  = row.grading_detail,
      h.updated_at      = datetime()
  `;
  await runWrite(cypher, { rows });
}

async function batchMergeFromSourceEdges(
  rows: Array<{ hadith_id: string; source_name: string }>,
  dryRun: boolean
): Promise<void> {
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
    MATCH (sch:SchoolOfThought {name: 'Shia Imami'})
    MERGE (h)-[:IN_SCHOOL]->(sch)
  `;
  await runWrite(cypher, { ids: hadithIds });
}

// ─── Ensure singleton nodes ──────────────────────────────────────────────────

async function ensureShiaSchool(dryRun: boolean): Promise<void> {
  if (dryRun) return;
  // Use Shia Imami (Twelver) as the specific school for these collections
  await mergeNodeByKey({
    label: 'SchoolOfThought',
    keyProp: 'name',
    keyValue: 'Shia Imami',
    createProps: { tradition: 'Shia Imami', name_arabic: 'الشيعة الإمامية' },
  });
  console.log('  Ensured SchoolOfThought:Shia Imami (Twelver)');
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

  // Source -> Shia Imami (Twelver) school
  await mergeEdge({
    fromLabel: 'Source',
    fromKey: { prop: 'id', value: result.id },
    toLabel: 'SchoolOfThought',
    toKey: { prop: 'name', value: 'Shia Imami' },
    relType: 'CANON_OF',
  });

  console.log(`  Source: ${sourceName} (${sourceSlug})`);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs();

  const csvPath = path.join(process.cwd(), 'datasets/hadith-data/all_hadiths_shia.csv');
  if (!fs.existsSync(csvPath)) {
    console.error(`ERROR: CSV not found at ${csvPath}`);
    console.error('Run the download + build_csv pipeline first.');
    process.exit(1);
  }

  console.log('='.repeat(70));
  console.log('  Shia Collections -> Neo4j Import');
  console.log('='.repeat(70));
  console.log(`\nInput:       ${csvPath}`);
  console.log(`Batch size:  ${args.batchSize}`);
  console.log(`Dry run:     ${args.dryRun}`);
  if (args.sample !== null) console.log(`Sample:      ${args.sample}`);

  // Ensure SchoolOfThought:Shia
  await ensureShiaSchool(args.dryRun);

  const sourceCache = new Map<string, string>();
  const sourceCounts: Record<string, number> = {};
  const unknownSources = new Set<string>();

  let processed = 0;
  let skipped = 0;
  let errors = 0;
  const startedAt = Date.now();

  // Batch buffers
  let hadithBatch: HadithBatchRow[] = [];
  let fromSourceBatch: Array<{ hadith_id: string; source_name: string }> = [];
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

    const elapsed = Date.now() - startedAt;
    const rate = processed > 0 ? elapsed / processed : 0;
    const etaStr = args.sample
      ? formatDuration(rate * (args.sample - processed))
      : '';
    console.log(
      `  [batch ${batchIndex}] ${formatNum(processed)} rows` +
      (etaStr ? ` — ETA ${etaStr}` : '') +
      ` — ${formatDuration(elapsed)} elapsed`
    );
  };

  for await (const row of streamCSV(csvPath)) {
    if (args.sample !== null && processed >= args.sample) break;

    const slug = resolveSlug(row.source, row.url);
    if (!slug) {
      if (!unknownSources.has(row.source)) {
        console.warn(`  [SKIP] Unknown source: "${row.source}"`);
        unknownSources.add(row.source);
      }
      skipped++;
      continue;
    }

    const sourceName = SLUG_TO_CANONICAL[slug];
    if (!sourceName) {
      skipped++;
      continue;
    }

    try {
      await ensureSource(sourceName, slug, sourceCache, args.dryRun);

      const id = `shia_${slug}_${row.hadith_id}_v${row.volume || '1'}`;
      const { display_grade, grading_detail } = resolveGrading(row);
      const vol = row.volume ? parseInt(row.volume, 10) : null;

      const title = vol
        ? `${sourceName} Vol.${vol} #${row.hadith_no || row.hadith_id}`
        : `${sourceName} #${row.hadith_no || row.hadith_id}`;

      hadithBatch.push({
        id,
        title,
        primary_topic: row.category || row.chapter || 'General',
        source: sourceName,
        source_slug: slug,
        volume: vol,
        chapter: row.chapter || '',
        chapter_no: row.chapter_no || '',
        hadith_no: row.hadith_no || '',
        text_arabic: row.text_ar || '',
        text_english: row.text_en || '',
        sanad_text: row.sanad || '',
        matn_english: row.matn_en || '',
        display_grade,
        grading_detail,
        tradition: 'Shia Imami',
        source_role: 'PRIMARY_COLLECTION',
        url: row.url || '',
      });

      fromSourceBatch.push({ hadith_id: id, source_name: sourceName });
      inSchoolBatch.push(id);

      sourceCounts[slug] = (sourceCounts[slug] ?? 0) + 1;
      processed++;
    } catch (err) {
      console.error(`  [ERROR] row ${row.id}:`, err);
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
  console.log(`  Skipped:     ${formatNum(skipped)}`);
  console.log(`  Errors:      ${formatNum(errors)}`);
  console.log(`  Duration:    ${formatDuration(elapsed)}`);
  console.log('\n  Per source:');
  for (const [slug, count] of Object.entries(sourceCounts).sort((a, b) => b[1] - a[1])) {
    const name = SLUG_TO_CANONICAL[slug] ?? slug;
    console.log(`    ${name}: ${formatNum(count)}`);
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
