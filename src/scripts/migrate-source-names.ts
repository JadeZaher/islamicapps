/**
 * migrate-source-names.ts
 * =======================
 * One-time idempotent migration to fix hadith data integrity issues:
 *   1. Normalize source names on Hadith nodes to canonical values
 *   2. Fix titles for hadiths with hadith_no = '0' or empty
 *   3. Backfill dataset_row_id from all_hadiths_clean.csv
 *   4. Fix Musnad al-Rabi source name (Unicode → ASCII canonical)
 *   5. Merge duplicate Source nodes if any exist
 *
 * Usage:
 *   npx tsx src/scripts/migrate-source-names.ts
 *   npx tsx src/scripts/migrate-source-names.ts --dry-run
 */

import fs from 'fs';
import path from 'path';
import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';
import { CANONICAL_SOURCES } from '../lib/constants/sources';

loadEnv();

const DRY_RUN = process.argv.includes('--dry-run');

// Known non-canonical name variants → canonical name
const SOURCE_NAME_FIXES: Record<string, string> = {
  // import-pure-canon.ts variants
  'Sahih al-Bukhari': CANONICAL_SOURCES.bukhari.canonical,
  'Sunan Abi Dawud': CANONICAL_SOURCES.abudawud.canonical,
  "Sunan al-Nasa'i": CANONICAL_SOURCES.nasai.canonical,
  // Musnad al-Rabi Unicode variant (from CSV)
  "al-Jāmiʿ al-Ṣaḥīḥ \u2014 Musnad al-Imām al-Rabīʿ b. Ḥabīb":
    CANONICAL_SOURCES.musnad_rabi.canonical,
};

// ── CSV Parsing (minimal, from import-datasets.ts) ─────────────────

interface CSVRow { [key: string]: string; }

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

async function readCSV(filePath: string): Promise<CSVRow[]> {
  const content = fs.readFileSync(filePath, 'utf8');
  const parser = new CSVParser();
  const rows: CSVRow[] = [];
  let currentRow = '';
  let insideQuotes = false;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    if (char === '"') insideQuotes = !insideQuotes;
    if ((char === '\n' || char === '\r') && !insideQuotes) {
      if (char === '\r' && content[i + 1] === '\n') i++;
      if (currentRow.trim()) {
        const parsed = parser.parseRow(currentRow);
        if (parsed) rows.push(parsed);
      }
      currentRow = '';
    } else {
      currentRow += char;
    }
  }
  if (currentRow.trim()) {
    const parsed = parser.parseRow(currentRow);
    if (parsed) rows.push(parsed);
  }
  return rows;
}

// ── Migration Steps ────────────────────────────────────────────────

async function step1_fixSourceNames() {
  console.log('\n═══ Step 1: Fix source names on Hadith nodes ═══');

  for (const [oldName, newName] of Object.entries(SOURCE_NAME_FIXES)) {
    const countResult = await runQuery<{ count: number }>(
      `MATCH (h:Hadith) WHERE h.source = $oldName RETURN count(h) as count`,
      { oldName }
    );
    const count = countResult[0]?.count ?? 0;

    if (count > 0) {
      console.log(`  Found ${count} hadiths with source "${oldName}" → "${newName}"`);
      if (!DRY_RUN) {
        await runWrite(
          `MATCH (h:Hadith) WHERE h.source = $oldName SET h.source = $newName`,
          { oldName, newName }
        );
        console.log(`    ✅ Updated`);
      } else {
        console.log(`    [DRY RUN] Would update`);
      }
    } else {
      console.log(`  No hadiths found with source "${oldName}" — skipping`);
    }
  }

  // Also fix Source nodes
  for (const [oldName, newName] of Object.entries(SOURCE_NAME_FIXES)) {
    const countResult = await runQuery<{ count: number }>(
      `MATCH (s:Source) WHERE s.name = $oldName RETURN count(s) as count`,
      { oldName }
    );
    const count = countResult[0]?.count ?? 0;

    if (count > 0) {
      console.log(`  Found Source node "${oldName}" — merging into "${newName}"`);
      if (!DRY_RUN) {
        // Transfer FROM_SOURCE relationships to canonical Source node
        await runWrite(
          `MATCH (h:Hadith)-[r:FROM_SOURCE]->(old:Source {name: $oldName})
           MATCH (canonical:Source {name: $newName})
           MERGE (h)-[:FROM_SOURCE]->(canonical)
           DELETE r`,
          { oldName, newName }
        );
        // Delete the old Source node if it has no remaining relationships
        await runWrite(
          `MATCH (s:Source {name: $oldName})
           WHERE NOT EXISTS { (s)<-[:FROM_SOURCE]-() }
           DETACH DELETE s`,
          { oldName }
        );
        console.log(`    ✅ Merged`);
      }
    }
  }
}

async function step2_fixTitles() {
  console.log('\n═══ Step 2: Fix titles for hadith_no=0 ═══');

  const result = await runQuery<{ source: string; count: number }>(
    `MATCH (h:Hadith) WHERE h.hadith_no = '0' OR h.hadith_no = '' OR h.hadith_no IS NULL
     RETURN h.source as source, count(h) as count`
  );

  if (result.length === 0) {
    console.log('  No hadiths with hadith_no=0 found');
    return;
  }

  for (const r of result) {
    console.log(`  ${r.source}: ${r.count} hadiths with bad titles`);
  }

  if (!DRY_RUN) {
    await runWrite(
      `MATCH (h:Hadith)
       WHERE h.hadith_no = '0' OR h.hadith_no = '' OR h.hadith_no IS NULL
       SET h.title = h.source + ' - ' + COALESCE(h.chapter, 'Introduction')`
    );
    console.log('  ✅ Titles updated');
  } else {
    console.log('  [DRY RUN] Would update titles');
  }
}

async function step3_backfillDatasetRowId() {
  console.log('\n═══ Step 3: Backfill dataset_row_id from CSV ═══');

  const csvPath = path.join(process.cwd(), 'datasets', 'hadith-data', 'all_hadiths_clean.csv');
  if (!fs.existsSync(csvPath)) {
    console.log(`  ⚠️  CSV not found at ${csvPath} — skipping backfill`);
    return;
  }

  const rows = await readCSV(csvPath);
  console.log(`  Read ${rows.length} rows from CSV`);

  let matched = 0;
  let unmatched = 0;
  const BATCH_SIZE = 500;

  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE);

    for (const row of batch) {
      const source = row.source?.trim() || '';
      const hadithNo = row.hadith_no?.trim() || '';
      const chapterNo = row.chapter_no?.trim() || '';
      const datasetRowId = parseInt(row.hadith_id?.trim() || '0', 10);

      if (!datasetRowId) continue;

      if (!DRY_RUN) {
        const result = await runQuery<{ count: number }>(
          `MATCH (h:Hadith)
           WHERE h.source = $source AND h.hadith_no = $hadithNo AND h.chapter_no = $chapterNo
           SET h.dataset_row_id = $datasetRowId
           RETURN count(h) as count`,
          { source, hadithNo, chapterNo, datasetRowId }
        );
        if ((result[0]?.count ?? 0) > 0) {
          matched++;
        } else {
          unmatched++;
        }
      } else {
        matched++; // Assume match in dry run
      }
    }

    if ((i + BATCH_SIZE) % 5000 === 0) {
      console.log(`  Processed ${i + BATCH_SIZE}/${rows.length} rows (matched: ${matched}, unmatched: ${unmatched})`);
    }
  }

  console.log(`  ${DRY_RUN ? '[DRY RUN] ' : '✅ '}Backfill complete: ${matched} matched, ${unmatched} unmatched`);
}

async function step4_verifyIntegrity() {
  console.log('\n═══ Step 4: Verification ═══');

  // Check source distribution
  const sources = await runQuery<{ source: string; count: number }>(
    `MATCH (h:Hadith) RETURN h.source as source, count(h) as count ORDER BY count DESC`
  );
  console.log('\n  Hadith counts by source:');
  for (const s of sources) {
    console.log(`    ${s.source}: ${s.count}`);
  }

  // Check Source nodes
  const sourceNodes = await runQuery<{ name: string; count: number }>(
    `MATCH (s:Source)
     OPTIONAL MATCH (h:Hadith)-[:FROM_SOURCE]->(s)
     RETURN s.name as name, count(h) as count
     ORDER BY name`
  );
  console.log('\n  Source nodes (with FROM_SOURCE relationship counts):');
  for (const s of sourceNodes) {
    console.log(`    ${s.name}: ${s.count}`);
  }

  // Check remaining bad titles
  const badTitles = await runQuery<{ count: number }>(
    `MATCH (h:Hadith) WHERE h.title ENDS WITH ' 0' RETURN count(h) as count`
  );
  console.log(`\n  Hadiths with title ending in " 0": ${badTitles[0]?.count ?? 0}`);

  // Check dataset_row_id coverage
  const rowIdCount = await runQuery<{ count: number }>(
    `MATCH (h:Hadith) WHERE h.dataset_row_id IS NOT NULL RETURN count(h) as count`
  );
  const totalCount = await runQuery<{ count: number }>(
    `MATCH (h:Hadith) RETURN count(h) as count`
  );
  console.log(`  Hadiths with dataset_row_id: ${rowIdCount[0]?.count ?? 0} / ${totalCount[0]?.count ?? 0}`);
}

// ── Main ──────────────────────────────────────────────────────────

async function main() {
  console.log(`\n🔧 Hadith Data Integrity Migration ${DRY_RUN ? '(DRY RUN)' : ''}`);
  console.log('='.repeat(50));

  try {
    await step1_fixSourceNames();
    await step2_fixTitles();
    await step3_backfillDatasetRowId();
    await step4_verifyIntegrity();

    console.log(`\n${'='.repeat(50)}`);
    console.log(`✅ Migration ${DRY_RUN ? '(dry run) ' : ''}complete`);
  } catch (error) {
    console.error('\n❌ Migration failed:', error);
    process.exit(1);
  } finally {
    await closeDriver();
  }
}

main();
