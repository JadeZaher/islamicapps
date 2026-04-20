/**
 * import-musnad.ts
 * ================
 * Import Musnad al-Rabi' b. Habib data into the Neo4j graph database.
 *
 * Reads from:
 *   - datasets/musnad_rawis.csv   (18 Ibadi narrators, scholar_indx 60001-60020)
 *   - datasets/musnad_hadiths.csv (791 hadiths across 4 parts)
 *
 * Creates:
 *   - 1 Source node for the Musnad collection
 *   - Narrator nodes (MERGE on scholar_indx to avoid duplicates)
 *   - Location nodes from narrator biographical data
 *   - Hadith nodes with MatnVariation + Chain + narrator links
 *   - HEARD_FROM relationships between narrators
 *
 * Usage:
 *   npm run db:import:musnad
 *   tsx src/scripts/import-musnad.ts
 *   tsx src/scripts/import-musnad.ts --clear   # delete existing Musnad data first
 */

import fs from 'fs';
import path from 'path';
import { randomUUID } from 'crypto';
import { loadEnv } from './lib/env';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';
import { initializeSchema } from '../lib/db/schema';
import { CANONICAL_SOURCES } from '../lib/constants/sources';

loadEnv();

const uuidv4 = randomUUID;

const MUSNAD_SOURCE_NAME = CANONICAL_SOURCES.musnad_rabi.canonical;
const MUSNAD_SOURCE_NAME_AR = 'الجامع الصحيح — مسند الإمام الربيع بن حبيب';

// Part ranges for transmission type classification
const PART_RANGES: Array<[number, number, number, string]> = [
  [1, 391, 1, 'CONNECTED'],        // Parts 1-2: connected chains
  [392, 742, 2, 'CONNECTED'],
  [743, 882, 3, 'SUPPLEMENTARY'],   // Part 3: supplementary reports
  [883, 1005, 4, 'MURSAL'],         // Part 4: mursal (disconnected) reports
];

// The golden chain of the Musnad
const GOLDEN_CHAIN_INDX = [60003, 60002, 60001]; // al-Rabi' -> Abu 'Ubayda -> Jabir b. Zayd

// ── CSV Parsing (from import-datasets.ts) ───────────────────────────

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

async function readCSV(filePath: string, callback: (row: CSVRow) => Promise<void>) {
  const content = fs.readFileSync(filePath, 'utf8');
  const parser = new CSVParser();

  const rows: string[] = [];
  let currentRow = '';
  let insideQuotes = false;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    if (char === '"') {
      insideQuotes = !insideQuotes;
    }
    if ((char === '\n' || char === '\r') && !insideQuotes) {
      if (char === '\r' && content[i + 1] === '\n') i++;
      if (currentRow.trim()) {
        rows.push(currentRow);
      }
      currentRow = '';
    } else {
      currentRow += char;
    }
  }
  if (currentRow.trim()) rows.push(currentRow);

  for (let i = 0; i < rows.length; i++) {
    try {
      const row = parser.parseRow(rows[i]);
      if (row) {
        await callback(row);
      }
    } catch (error) {
      console.error(`Error parsing row ${i + 1}:`, error);
    }
  }
}

// ── Utilities ───────────────────────────────────────────────────────

function parseName(fullName: string): { english: string; arabic: string } {
  const parts = fullName.split('(');
  const english = parts[0].trim();
  let arabic = '';
  if (parts.length >= 2) {
    const remaining = parts.slice(1).join('(').trim();
    const arabicMatch = remaining.match(/([^\(\)]+)/);
    if (arabicMatch) {
      arabic = arabicMatch[1].trim();
    }
  }
  return { english, arabic };
}

function mapGradeToTabaqah(grade: string): { tabaqah: string; reliability: string; is_prophet: boolean } {
  const upper = grade.toUpperCase();
  if (upper.includes('RASOOL')) {
    return { tabaqah: 'PROPHET', reliability: 'THIQA', is_prophet: true };
  } else if (upper.includes('COMP') || upper.includes('SAHABI')) {
    return { tabaqah: 'SAHABA', reliability: 'THIQA', is_prophet: false };
  } else if (upper.includes('FOLLOWER') || upper.includes("TABI'") || upper.includes('TABI')) {
    return { tabaqah: 'TABI_UN', reliability: 'THIQA', is_prophet: false };
  } else if (upper.includes('3RD') || upper.includes('THIRD') || upper.includes("TABA' TABI")) {
    return { tabaqah: 'TABI_TABI_IN', reliability: 'THIQA', is_prophet: false };
  } else if (upper.includes('4TH') || upper.includes('FOURTH') || upper.includes('GENERATION')) {
    return { tabaqah: 'LATER_SCHOLAR', reliability: 'THIQA', is_prophet: false };
  } else if (upper.includes('CENTURY')) {
    return { tabaqah: 'LATER_SCHOLAR', reliability: 'THIQA', is_prophet: false };
  }
  return { tabaqah: 'LATER_SCHOLAR', reliability: 'THIQA', is_prophet: false };
}

function parseIndices(indicesStr: string): number[] {
  if (!indicesStr) return [];
  return indicesStr
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n));
}

function classifyTransmission(hadithNo: number): { part: number; transmissionType: string } {
  for (const [start, end, part, type] of PART_RANGES) {
    if (hadithNo >= start && hadithNo <= end) {
      return { part, transmissionType: type };
    }
  }
  return { part: 0, transmissionType: 'UNKNOWN' };
}

function isGoldenChain(chainIndices: number[]): boolean {
  if (chainIndices.length < 3) return false;
  return (
    chainIndices[0] === GOLDEN_CHAIN_INDX[0] &&
    chainIndices[1] === GOLDEN_CHAIN_INDX[1] &&
    chainIndices[2] === GOLDEN_CHAIN_INDX[2]
  );
}

// ── Source ───────────────────────────────────────────────────────────

async function createMusnadSource(): Promise<string> {
  console.log('\nCreating Musnad source node...');

  const sourceId = uuidv4();
  await runWrite(
    `
    MERGE (s:Source {name: $name})
    ON CREATE SET
      s.id = $id,
      s.name_arabic = $name_arabic,
      s.compiler = $compiler,
      s.total_hadiths = $total_hadiths,
      s.description = $description,
      s.created_at = datetime()
    ON MATCH SET
      s.total_hadiths = $total_hadiths
    RETURN s.id
    `,
    {
      id: sourceId,
      name: MUSNAD_SOURCE_NAME,
      name_arabic: MUSNAD_SOURCE_NAME_AR,
      compiler: "al-Rabi' b. Habib b. 'Amr al-Farahidi al-Azdi",
      total_hadiths: 1005,
      description:
        'The primary hadith collection of the Ibadi school. Compiled by al-Rabi\' b. Habib (d. 175-180 AH) ' +
        'in Basra, arranged by Abu Ya\'qub al-Warjlani (6th century AH). Contains 1005 hadiths in 4 parts. ' +
        'Parts 1-2: connected chains via Abu \'Ubayda and Jabir b. Zayd. ' +
        'Part 3: supplementary reports with diverse chains. Part 4: mursal (disconnected) reports.',
    }
  );

  await runWrite(
    `MATCH (s:Source {name: $name})
     MATCH (school:SchoolOfThought {name: 'Ibadi'})
     MERGE (s)-[:CANON_OF]->(school)`,
    { name: MUSNAD_SOURCE_NAME }
  );
  console.log('  Linked Source -[:CANON_OF]-> Ibadi school');

  console.log(`  Created: ${MUSNAD_SOURCE_NAME}`);
  return MUSNAD_SOURCE_NAME;
}

// ── Narrators ───────────────────────────────────────────────────────

interface NarratorRecord {
  scholar_indx: number;
  name_english: string;
  name_arabic: string;
}

async function importMusnadNarrators(filePath: string): Promise<Map<number, NarratorRecord>> {
  console.log('\nImporting Musnad narrators...');

  const narrators = new Map<number, NarratorRecord>();
  const locations = new Set<string>();
  let count = 0;

  await readCSV(filePath, async (row) => {
    const scholarIndx = parseInt(row.scholar_indx, 10);
    if (isNaN(scholarIndx)) return;

    const { english, arabic } = parseName(row.name);
    const { tabaqah, reliability, is_prophet } = mapGradeToTabaqah(row.grade || '');

    // Extract locations
    const birthPlace = row.birth_place || '';
    const deathPlace = row.death_place || '';
    const placesOfStay = row.places_of_stay || '';

    [birthPlace, deathPlace, ...placesOfStay.split(';').flatMap((s) => s.split(','))].forEach(
      (place) => {
        const clean = place.trim();
        if (clean && clean.length > 1 && clean.length < 100) {
          locations.add(clean);
        }
      }
    );

    // Parse death year from string like "93 AH (some say 96, 103, 104)"
    let deathYearHijri: number | null = null;
    const deathHijriStr = row.death_date_hijri || '';
    const deathMatch = deathHijriStr.match(/(\d+)/);
    if (deathMatch) {
      deathYearHijri = parseInt(deathMatch[1], 10);
    }

    const bio = [row.area_of_interest, row.tags].filter(Boolean).join('. ').trim();

    try {
      await runWrite(
        `
        MERGE (n:Narrator {scholar_indx: $scholar_indx})
        ON CREATE SET
          n.id = $id,
          n.name_english = $name_english,
          n.name_arabic = $name_arabic,
          n.reliability = $reliability,
          n.tabaqah = $tabaqah,
          n.bio = $bio,
          n.birth_year_hijri = $birth_year_hijri,
          n.death_year_hijri = $death_year_hijri,
          n.geographic_region = $geographic_region,
          n.is_prophet = $is_prophet,
          n.created_at = datetime()
        RETURN n.id
        `,
        {
          id: uuidv4(),
          scholar_indx: scholarIndx,
          name_english: english,
          name_arabic: arabic,
          reliability,
          tabaqah,
          bio,
          birth_year_hijri: null,
          death_year_hijri: deathYearHijri,
          geographic_region: birthPlace || deathPlace || '',
          is_prophet,
        }
      );

      await runWrite(
        `MATCH (n:Narrator {scholar_indx: $scholar_indx})
         MATCH (school:SchoolOfThought {name: 'Ibadi'})
         MERGE (n)-[r:ACCEPTED_IN]->(school)
         ON CREATE SET r.status = 'THIQA', r.source = 'musnad_import'`,
        { scholar_indx: scholarIndx }
      );

      narrators.set(scholarIndx, { scholar_indx: scholarIndx, name_english: english, name_arabic: arabic });
      count++;
      console.log(`  [${count}] ${english} (${scholarIndx})`);
    } catch (error) {
      console.error(`  Failed: ${english} (${scholarIndx}):`, error);
    }
  });

  // Create location nodes
  console.log(`\nCreating ${locations.size} location nodes...`);
  let locCount = 0;
  for (const locName of locations) {
    try {
      await runWrite(
        `
        MERGE (l:Location {name: $name})
        ON CREATE SET
          l.id = $id,
          l.created_at = datetime()
        RETURN l.id
        `,
        { id: uuidv4(), name: locName }
      );
      locCount++;
    } catch (error) {
      // Ignore duplicate location errors
    }
  }
  console.log(`  Created ${locCount} location nodes`);

  console.log(`\nImported ${count} narrators`);
  return narrators;
}

// ── Narrator Relationships ──────────────────────────────────────────

async function createNarratorRelationships(
  filePath: string,
  narrators: Map<number, NarratorRecord>
) {
  console.log('\nCreating teacher-student HEARD_FROM relationships...');
  let relCount = 0;

  await readCSV(filePath, async (row) => {
    const scholarIndx = parseInt(row.scholar_indx, 10);
    if (isNaN(scholarIndx) || !narrators.has(scholarIndx)) return;

    const teacherIndices = parseIndices(row.teachers_inds);
    for (const teacherIndx of teacherIndices) {
      if (narrators.has(teacherIndx)) {
        try {
          await runWrite(
            `
            MATCH (student:Narrator {scholar_indx: $studentIndx})
            MATCH (teacher:Narrator {scholar_indx: $teacherIndx})
            MERGE (student)-[:HEARD_FROM]->(teacher)
            RETURN 1
            `,
            { studentIndx: scholarIndx, teacherIndx }
          );
          relCount++;
        } catch (error) {
          // Ignore if relationship exists
        }
      }
    }
  });

  console.log(`  Created ${relCount} HEARD_FROM relationships`);
}

// ── Hadiths ─────────────────────────────────────────────────────────

async function importMusnadHadiths(
  filePath: string,
  sourceName: string,
  narrators: Map<number, NarratorRecord>
) {
  console.log('\nImporting Musnad hadiths...');

  let processedCount = 0;
  let chainCount = 0;

  await readCSV(filePath, async (row) => {
    const hadithNo = parseInt(row.hadith_no, 10);
    if (isNaN(hadithNo)) return;

    const chainIndices = parseIndices(row.chain_indx);
    const { part, transmissionType } = classifyTransmission(hadithNo);
    const goldenChain = isGoldenChain(chainIndices);

    const hadithId = row.id || `musnad_${String(hadithNo).padStart(4, '0')}`;

    try {
      // Create Hadith node
      await runWrite(
        `
        MERGE (h:Hadith {id: $id})
        ON CREATE SET
          h.title = $title,
          h.primary_topic = $primary_topic,
          h.source = $source,
          h.chapter = $chapter,
          h.chapter_no = $chapter_no,
          h.hadith_no = $hadith_no,
          h.text_arabic = $text_arabic,
          h.text_english = $text_english,
          h.transmission_type = $transmission_type,
          h.part = $part,
          h.display_grade = '',
          h.auto_calculated_grade = '',
          h.created_at = datetime()
        RETURN h.id
        `,
        {
          id: hadithId,
          title: `Musnad al-Rabi ${hadithNo}`,
          primary_topic: row.chapter || 'General',
          source: sourceName,
          chapter: row.chapter || '',
          chapter_no: row.chapter_no || '',
          hadith_no: String(hadithNo),
          text_arabic: row.text_ar || '',
          text_english: row.text_en || '',
          transmission_type: transmissionType,
          part,
        }
      );

      await runWrite(
        `MATCH (h:Hadith {id: $hadithId})
         MATCH (school:SchoolOfThought {name: 'Ibadi'})
         MERGE (h)-[:IN_SCHOOL]->(school)`,
        { hadithId }
      );

      // Link to Source
      await runWrite(
        `
        MATCH (h:Hadith {id: $hadithId})
        MATCH (s:Source {name: $sourceName})
        MERGE (h)-[:FROM_SOURCE]->(s)
        `,
        { hadithId, sourceName }
      );

      // Create MatnVariation + Chain + narrator links
      if (chainIndices.length > 0) {
        const variationId = uuidv4();
        const chainId = uuidv4();

        // MatnVariation
        await runWrite(
          `
          CREATE (m:MatnVariation {
            id: $id,
            source_book: $source_book,
            text_arabic: $text_arabic,
            text_english: $text_english
          })
          `,
          {
            id: variationId,
            source_book: sourceName,
            text_arabic: row.text_ar || '',
            text_english: row.text_en || '',
          }
        );

        // Hadith -> MatnVariation
        await runWrite(
          `
          MATCH (h:Hadith {id: $hadithId})
          MATCH (m:MatnVariation {id: $variationId})
          CREATE (h)-[:HAS_VARIATION]->(m)
          `,
          { hadithId, variationId }
        );

        // Chain node
        await runWrite(
          `
          CREATE (c:Chain {
            id: $id,
            is_golden_chain: $is_golden_chain,
            created_at: datetime()
          })
          `,
          { id: chainId, is_golden_chain: goldenChain }
        );

        // MatnVariation -> Chain
        await runWrite(
          `
          MATCH (m:MatnVariation {id: $variationId})
          MATCH (c:Chain {id: $chainId})
          CREATE (m)-[:TRANSMITTED_VIA]->(c)
          `,
          { variationId, chainId }
        );

        // Chain -> Narrator (INCLUDES)
        for (const scholarIndx of chainIndices) {
          if (narrators.has(scholarIndx)) {
            await runWrite(
              `
              MATCH (c:Chain {id: $chainId})
              MATCH (n:Narrator {scholar_indx: $scholarIndx})
              MERGE (c)-[:INCLUDES]->(n)
              `,
              { chainId, scholarIndx }
            );
          }
        }

        // HEARD_FROM between consecutive narrators in the chain
        for (let i = 0; i < chainIndices.length - 1; i++) {
          const studentIndx = chainIndices[i];
          const teacherIndx = chainIndices[i + 1];
          if (narrators.has(studentIndx) && narrators.has(teacherIndx)) {
            await runWrite(
              `
              MATCH (student:Narrator {scholar_indx: $studentIndx})
              MATCH (teacher:Narrator {scholar_indx: $teacherIndx})
              MERGE (student)-[:HEARD_FROM]->(teacher)
              `,
              { studentIndx, teacherIndx }
            );
          }
        }

        chainCount++;
      }

      processedCount++;
      if (processedCount % 100 === 0) {
        console.log(`  Processed ${processedCount} hadiths...`);
      }
    } catch (error) {
      console.error(`  Error importing hadith ${hadithNo}:`, error);
    }
  });

  console.log(`  Imported ${processedCount} hadiths with ${chainCount} chains`);
}

// ── Clear existing Musnad data ──────────────────────────────────────

async function clearMusnadData() {
  console.log('\nClearing existing Musnad data...');

  // Delete hadiths and their chains/variations
  const hadithResult = await runWrite(`
    MATCH (h:Hadith) WHERE h.source CONTAINS 'Musnad' OR EXISTS { MATCH (h)-[:IN_SCHOOL]->(:SchoolOfThought {name: 'Ibadi'}) }
    OPTIONAL MATCH (h)-[:HAS_VARIATION]->(m:MatnVariation)-[:TRANSMITTED_VIA]->(c:Chain)
    DETACH DELETE h, m, c
    RETURN count(DISTINCT h) as deleted
  `);
  const deletedHadiths = hadithResult[0]?.deleted || 0;
  console.log(`  Deleted ${deletedHadiths} Musnad hadiths (and their chains/variations)`);

  // Delete Source
  await runWrite(`
    MATCH (s:Source) WHERE s.name CONTAINS 'Musnad'
    DETACH DELETE s
  `);
  console.log('  Deleted Musnad source node');
}

// ── Main ────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const shouldClear = args.includes('--clear');

  const basePath = path.join(process.cwd(), 'datasets');
  const narratorPath = path.join(basePath, 'musnad_rawis.csv');
  const hadithPath = path.join(basePath, 'musnad_hadiths.csv');

  if (!fs.existsSync(narratorPath)) {
    console.error(`Narrator CSV not found: ${narratorPath}`);
    console.error('Run the parsing pipeline first: python datasets/02_parse_hadiths.py && python datasets/04_generate_csvs.py');
    process.exit(1);
  }
  if (!fs.existsSync(hadithPath)) {
    console.error(`Hadith CSV not found: ${hadithPath}`);
    process.exit(1);
  }

  try {
    console.log('='.repeat(60));
    console.log('  Musnad al-Rabi\' b. Habib -> Neo4j Import');
    console.log('='.repeat(60));
    console.log(`\nNarrator data: ${narratorPath}`);
    console.log(`Hadith data:   ${hadithPath}`);

    // Initialize schema (creates constraints/indexes if missing)
    console.log('\nInitializing schema...');
    await initializeSchema();

    // Clear if requested
    if (shouldClear) {
      await clearMusnadData();
    }

    // Create Source
    const sourceName = await createMusnadSource();

    // Import narrators
    const narrators = await importMusnadNarrators(narratorPath);

    // Create narrator relationships
    await createNarratorRelationships(narratorPath, narrators);

    // Import hadiths
    await importMusnadHadiths(hadithPath, sourceName, narrators);

    // Summary
    console.log('\n' + '='.repeat(60));
    console.log('  Import Complete');
    console.log('='.repeat(60));

    try {
      const stats = await runQuery(`
        MATCH (h:Hadith) WHERE h.source CONTAINS 'Musnad' OR EXISTS { MATCH (h)-[:IN_SCHOOL]->(:SchoolOfThought {name: 'Ibadi'}) }
        WITH count(h) as musnadHadiths
        MATCH (n:Narrator) WHERE n.scholar_indx >= 60000
        WITH musnadHadiths, count(n) as ibadiNarrators
        MATCH (c:Chain) WHERE c.is_golden_chain = true
        WITH musnadHadiths, ibadiNarrators, count(c) as goldenChains
        RETURN musnadHadiths, ibadiNarrators, goldenChains
      `);

      if (stats.length > 0) {
        const s = stats[0];
        console.log('\nDatabase counts:');
        console.log(`  Musnad hadiths:    ${s.musnadHadiths}`);
        console.log(`  Ibadi narrators:   ${s.ibadiNarrators}`);
        console.log(`  Golden chains:     ${s.goldenChains}`);
      }
    } catch {
      console.log('(Could not fetch stats)');
    }

    console.log('');
  } catch (error) {
    console.error('\nImport failed:', error);
    process.exit(1);
  } finally {
    await closeDriver();
  }
}

main();
