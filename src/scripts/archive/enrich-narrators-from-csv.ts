// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * enrich-narrators-from-csv.ts
 * ============================
 * Enriches existing Narrator nodes in Neo4j with biographical data from
 * datasets/narrator-data/all_rawis.csv.
 *
 * Fields enriched (only where currently NULL/empty):
 *   - name_arabic        (parsed from CSV name field)
 *   - birth_year_hijri   (from birth_date_hijri column)
 *   - death_year_hijri   (from death_date_hijri column)
 *   - geographic_region   (from places_of_stay / birth_place / death_place)
 *   - tradition           (inferred from chain connections in the graph)
 *
 * Usage:
 *   npx tsx src/scripts/enrich-narrators-from-csv.ts
 */

import fs from 'fs';
import path from 'path';
import { loadEnv } from './lib/env';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── CSV Parser (same pattern as import-datasets.ts) ────────────────────────

interface CSVRow {
  [key: string]: string;
}

class CSVParser {
  private headers: string[] = [];
  private isFirstLine = true;

  parseRow(line: string): CSVRow | null {
    if (this.isFirstLine) {
      this.headers = this.parseCSVLine(line);
      this.isFirstLine = false;
      return null;
    }

    const values = this.parseCSVLine(line);
    if (values.length !== this.headers.length) {
      // Skip malformed rows silently
      return null;
    }

    const row: CSVRow = {};
    this.headers.forEach((header, index) => {
      row[header] = values[index] || '';
    });
    return row;
  }

  private parseCSVLine(line: string): string[] {
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
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    result.push(current.trim());
    return result;
  }
}

// ─── Arabic Name Extraction ─────────────────────────────────────────────────

/**
 * Parse the CSV name field to extract the Arabic name.
 * Format: "English Name ( Arabic Name ( honorific"
 * Example: "'Umar ibn al-Khattab ( \u0639\u0645\u0631 \u0628\u0646 \u0627\u0644\u062E\u0637\u0627\u0628 \u0628\u0646 \u0646\u0641\u064A\u0644 ( \u0631\u0636\u064A \u0627\u0644\u0644\u0647 \u0639\u0646\u0647"
 * Returns the Arabic name portion, or empty string if not found.
 */
function extractArabicName(fullName: string): string {
  const parts = fullName.split('(');
  if (parts.length < 2) return '';

  // The second part (index 1) contains the Arabic name
  let arabic = parts[1].trim();

  // Remove common honorifics
  const honorifics = [
    '\u0631\u0636\u064A \u0627\u0644\u0644\u0647 \u0639\u0646\u0647',        // radi Allahu anhu
    '\u0631\u0636\u064A \u0627\u0644\u0644\u0647 \u0639\u0646\u0647\u0627',       // radi Allahu anha
    '\u0631\u0636\u064A \u0627\u0644\u0644\u0647 \u0639\u0646\u0647\u0645',       // radi Allahu anhum
    '\u0635\u0644\u0651\u06CC \u0627\u0644\u0644\u06C1 \u0639\u0644\u06CC\u06C1 \u0648\u0622\u0644\u06C1 \u0648\u0633\u0644\u0651\u0645', // sallallahu alayhi wa sallam
    '\u0639\u0644\u064A\u0647 \u0627\u0644\u0633\u0644\u0627\u0645',        // alayhi al-salam
    '\u0631\u062D\u0645\u0647 \u0627\u0644\u0644\u0647',           // rahimahu Allah
  ];
  for (const hon of honorifics) {
    arabic = arabic.replace(hon, '');
  }

  // Trim whitespace and trailing/leading punctuation
  arabic = arabic.replace(/[()]/g, '').trim();

  // If it doesn't contain Arabic characters, skip
  if (!/[\u0600-\u06FF]/.test(arabic)) return '';

  return arabic;
}

// ─── Geographic Region Normalization ─────────────────────────────────────────

const REGION_MAP: Record<string, string> = {
  'makkah': 'Makkah',
  'mecca': 'Makkah',
  'medina': 'Medina',
  'medinah': 'Medina',
  'medianh': 'Medina',
  'madinah': 'Medina',
  'kufa': 'Kufa',
  'basra': 'Basra',
  'basrah': 'Basra',
  'damascus': 'Damascus',
  'sham': 'Damascus',
  'syria': 'Damascus',
  'egypt': 'Egypt',
  'misr': 'Egypt',
  'baghdad': 'Baghdad',
  'yemen': 'Yemen',
  'persia': 'Persia',
  'iran': 'Persia',
  'ta\'if': 'Taif',
  'taif': 'Taif',
  'abyssinia': 'Abyssinia',
  'homs': 'Homs',
  'jerusalem': 'Jerusalem',
  'sanaa': 'Yemen',
  'rayy': 'Persia',
  'nishapur': 'Persia',
  'bukhara': 'Bukhara',
  'samarqand': 'Samarqand',
};

function normalizeRegion(place: string): string | null {
  const lower = place.toLowerCase().trim();
  for (const [key, value] of Object.entries(REGION_MAP)) {
    if (lower.includes(key)) {
      return value;
    }
  }
  return null;
}

/**
 * Extract the primary geographic region from places_of_stay, birth_place, or death_place.
 * Returns the first recognized region, or null.
 */
function extractRegion(placesOfStay: string, birthPlace: string, deathPlace: string): string | null {
  // Primary: places_of_stay (first listed place)
  if (placesOfStay) {
    const places = placesOfStay.split(',');
    for (const place of places) {
      const region = normalizeRegion(place);
      if (region) return region;
    }
  }

  // Fallback: birth_place
  if (birthPlace) {
    const region = normalizeRegion(birthPlace);
    if (region) return region;
  }

  // Fallback: death_place
  if (deathPlace) {
    const region = normalizeRegion(deathPlace);
    if (region) return region;
  }

  return null;
}

// ─── Tradition Inference ─────────────────────────────────────────────────────

async function inferTraditions(): Promise<Map<number, string>> {
  console.log('  Inferring traditions from chain connections...');

  const results = await runQuery<{
    idx: number;
    traditions: string[];
    hadithCount: number;
  }>(`
    MATCH (n:Narrator)<-[:INCLUDES]-(c:Chain)<-[:TRANSMITTED_VIA]-(:MatnVariation)<-[:HAS_VARIATION]-(h:Hadith)
    WHERE n.tradition IS NULL AND n.scholar_indx IS NOT NULL
    WITH n.scholar_indx AS idx, collect(DISTINCT h.tradition) AS traditions, count(h) AS hadithCount
    RETURN idx, traditions, hadithCount
  `);

  const tradMap = new Map<number, string>();

  for (const row of results) {
    const traditions = (row.traditions || []).filter((t: string) => t && t.length > 0);
    if (traditions.length === 0) continue;

    if (traditions.length === 1) {
      // Only appears in one tradition
      tradMap.set(row.idx, traditions[0]);
    } else {
      // Mixed: get the dominant one via a more detailed query
      // For simplicity, just pick the first tradition (most common by collection ordering)
      // A more accurate approach would count per-tradition, but this is sufficient
      tradMap.set(row.idx, traditions[0]);
    }
  }

  console.log(`  Found tradition inference for ${tradMap.size} narrators`);
  return tradMap;
}

// For mixed-tradition narrators, do a proper majority vote
async function inferTraditionsMajorityVote(): Promise<Map<number, string>> {
  console.log('  Inferring traditions (majority vote) from chain connections...');

  const results = await runQuery<{
    idx: number;
    tradition: string;
    cnt: number;
  }>(`
    MATCH (n:Narrator)<-[:INCLUDES]-(c:Chain)<-[:TRANSMITTED_VIA]-(:MatnVariation)<-[:HAS_VARIATION]-(h:Hadith)
    WHERE n.tradition IS NULL AND n.scholar_indx IS NOT NULL AND h.tradition IS NOT NULL
    WITH n.scholar_indx AS idx, h.tradition AS tradition, count(h) AS cnt
    RETURN idx, tradition, cnt
    ORDER BY idx, cnt DESC
  `);

  const tradMap = new Map<number, string>();
  // Group by idx and pick the tradition with highest count
  let currentIdx: number | null = null;
  let bestTradition = '';
  let bestCount = 0;

  for (const row of results) {
    if (row.idx !== currentIdx) {
      // Save previous
      if (currentIdx !== null && bestTradition) {
        tradMap.set(currentIdx, bestTradition);
      }
      currentIdx = row.idx;
      bestTradition = row.tradition;
      bestCount = row.cnt;
    } else {
      if (row.cnt > bestCount) {
        bestTradition = row.tradition;
        bestCount = row.cnt;
      }
    }
  }
  // Don't forget the last group
  if (currentIdx !== null && bestTradition) {
    tradMap.set(currentIdx, bestTradition);
  }

  console.log(`  Found tradition inference for ${tradMap.size} narrators (majority vote)`);
  return tradMap;
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(60));
  console.log('  Narrator Biographical Enrichment');
  console.log('='.repeat(60));

  const csvPath = path.resolve(process.cwd(), 'datasets/narrator-data/all_rawis.csv');
  console.log(`\nCSV source: ${csvPath}`);

  if (!fs.existsSync(csvPath)) {
    console.error(`ERROR: CSV file not found at ${csvPath}`);
    process.exit(1);
  }

  // Step 1: Infer traditions from graph (before we start the CSV loop)
  const tradMap = await inferTraditionsMajorityVote();

  // Step 2: Parse CSV and prepare enrichment rows
  console.log('\n  Parsing CSV...');
  const parser = new CSVParser();
  const fileContent = fs.readFileSync(csvPath, 'utf-8');
  const lines = fileContent.split('\n');

  interface EnrichmentRow {
    idx: number;
    name_arabic: string;
    birth_year: number | null;
    death_year: number | null;
    region: string | null;
    tradition: string | null;
  }

  const rows: EnrichmentRow[] = [];
  let parseErrors = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const csvRow = parser.parseRow(trimmed);
    if (!csvRow) continue;

    const scholarIdx = parseInt(csvRow['scholar_indx'], 10);
    if (isNaN(scholarIdx)) {
      parseErrors++;
      continue;
    }

    // Extract Arabic name
    const nameArabic = extractArabicName(csvRow['name'] || '');

    // Extract temporal data
    const birthYearRaw = parseInt(csvRow['birth_date_hijri'], 10);
    const deathYearRaw = parseInt(csvRow['death_date_hijri'], 10);
    const birthYear = isNaN(birthYearRaw) ? null : birthYearRaw;
    const deathYear = isNaN(deathYearRaw) ? null : deathYearRaw;

    // Extract geographic region
    const region = extractRegion(
      csvRow['places_of_stay'] || '',
      csvRow['birth_place'] || '',
      csvRow['death_place'] || ''
    );

    // Tradition from graph inference
    const tradition = tradMap.get(scholarIdx) || null;

    rows.push({
      idx: scholarIdx,
      name_arabic: nameArabic,
      birth_year: birthYear,
      death_year: deathYear,
      region,
      tradition,
    });
  }

  console.log(`  Parsed ${rows.length} rows (${parseErrors} parse errors)`);

  // Step 3: Batch update Neo4j
  console.log('\n  Updating Neo4j in batches...');
  const BATCH_SIZE = 500;
  const stats = {
    totalProcessed: 0,
    nameArabicUpdated: 0,
    birthYearUpdated: 0,
    deathYearUpdated: 0,
    regionUpdated: 0,
    traditionUpdated: 0,
    batchCount: 0,
  };

  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE);

    // Prepare batch data — filter out entirely null rows to avoid wasted work
    const batchData = batch.map((r) => ({
      idx: r.idx,
      name_arabic: r.name_arabic || null,
      birth_year: r.birth_year,
      death_year: r.death_year,
      region: r.region || null,
      tradition: r.tradition || null,
    }));

    const results = await runWrite<{
      updated_name: number;
      updated_birth: number;
      updated_death: number;
      updated_region: number;
      updated_tradition: number;
    }>(`
      UNWIND $rows AS row
      MATCH (n:Narrator {scholar_indx: row.idx})
      WITH n, row,
        CASE WHEN (n.name_arabic IS NULL OR n.name_arabic = '') AND row.name_arabic IS NOT NULL THEN 1 ELSE 0 END AS do_name,
        CASE WHEN n.birth_year_hijri IS NULL AND row.birth_year IS NOT NULL THEN 1 ELSE 0 END AS do_birth,
        CASE WHEN n.death_year_hijri IS NULL AND row.death_year IS NOT NULL THEN 1 ELSE 0 END AS do_death,
        CASE WHEN (n.geographic_region IS NULL OR n.geographic_region = '') AND row.region IS NOT NULL THEN 1 ELSE 0 END AS do_region,
        CASE WHEN (n.tradition IS NULL OR n.tradition = '') AND row.tradition IS NOT NULL THEN 1 ELSE 0 END AS do_tradition
      SET n.name_arabic = CASE WHEN do_name = 1 THEN row.name_arabic ELSE n.name_arabic END,
          n.birth_year_hijri = CASE WHEN do_birth = 1 THEN row.birth_year ELSE n.birth_year_hijri END,
          n.death_year_hijri = CASE WHEN do_death = 1 THEN row.death_year ELSE n.death_year_hijri END,
          n.geographic_region = CASE WHEN do_region = 1 THEN row.region ELSE n.geographic_region END,
          n.tradition = CASE WHEN do_tradition = 1 THEN row.tradition ELSE n.tradition END
      RETURN sum(do_name) AS updated_name,
             sum(do_birth) AS updated_birth,
             sum(do_death) AS updated_death,
             sum(do_region) AS updated_region,
             sum(do_tradition) AS updated_tradition
    `, { rows: batchData });

    if (results.length > 0) {
      const r = results[0];
      stats.nameArabicUpdated += (r.updated_name || 0);
      stats.birthYearUpdated += (r.updated_birth || 0);
      stats.deathYearUpdated += (r.updated_death || 0);
      stats.regionUpdated += (r.updated_region || 0);
      stats.traditionUpdated += (r.updated_tradition || 0);
    }

    stats.totalProcessed += batch.length;
    stats.batchCount++;

    if (stats.batchCount % 10 === 0 || i + BATCH_SIZE >= rows.length) {
      console.log(`    Batch ${stats.batchCount}: ${stats.totalProcessed}/${rows.length} rows processed`);
    }
  }

  // Step 4: Report
  console.log('\n' + '='.repeat(60));
  console.log('  Enrichment Complete');
  console.log('='.repeat(60));
  console.log(`  Total CSV rows:       ${rows.length}`);
  console.log(`  Batches:              ${stats.batchCount}`);
  console.log(`  name_arabic updated:  ${stats.nameArabicUpdated}`);
  console.log(`  birth_year updated:   ${stats.birthYearUpdated}`);
  console.log(`  death_year updated:   ${stats.deathYearUpdated}`);
  console.log(`  region updated:       ${stats.regionUpdated}`);
  console.log(`  tradition updated:    ${stats.traditionUpdated}`);
}

main()
  .catch((err) => {
    console.error('\nFatal error:', err);
    process.exit(1);
  })
  .finally(() => closeDriver());
