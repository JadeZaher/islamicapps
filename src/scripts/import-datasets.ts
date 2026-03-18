import fs from 'fs';
import path from 'path';
import { randomUUID } from 'crypto';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';
import { initializeSchema, clearDatabase } from '../lib/db/schema';

const uuidv4 = randomUUID;

// CSV parsing utilities for handling quoted fields with commas
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
      console.warn(`⚠️  Row has ${values.length} values but expected ${this.headers.length}`);
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
          // Escaped quote
          current += '"';
          i++;
        } else {
          // Toggle quote state
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

  reset() {
    this.headers = [];
    this.isFirstLine = true;
  }
}

// Parse name: "Abu Bakr As-Siddique ( أبو بكر الصديق ( رضي الله عنه"
function parseName(fullName: string): { english: string; arabic: string } {
  const parts = fullName.split('(');

  let english = parts[0].trim();
  let arabic = '';

  // Extract Arabic name from the middle section
  if (parts.length >= 2) {
    // Join remaining parts and extract Arabic text
    const remaining = parts.slice(1).join('(').trim();
    const arabicMatch = remaining.match(/([^\(\)]+)/);
    if (arabicMatch) {
      arabic = arabicMatch[1].trim();
    }
  }

  return { english, arabic };
}

// Map grade to tabaqah and reliability
function mapGradeToTabaqah(grade: string): { tabaqah: string; reliability: string; is_prophet: boolean } {
  const upperGrade = grade.toUpperCase();

  if (upperGrade.includes('RASOOL')) {
    return { tabaqah: 'PROPHET', reliability: 'THIQA', is_prophet: true };
  } else if (upperGrade.includes('COMP') && upperGrade.includes('RA')) {
    return { tabaqah: 'SAHABA', reliability: 'THIQA', is_prophet: false };
  } else if (upperGrade.includes("FOLLOWER") || upperGrade.includes("TABI")) {
    return { tabaqah: 'TABI_UN', reliability: 'THIQA', is_prophet: false };
  } else if (upperGrade.includes("SUCC") || upperGrade.includes("TABA' TABI")) {
    return { tabaqah: 'TABI_TABI_IN', reliability: 'THIQA', is_prophet: false };
  } else if (upperGrade.includes("CENTURY") || upperGrade.includes("CENTURY AH")) {
    return { tabaqah: 'LATER_SCHOLAR', reliability: 'THIQA', is_prophet: false };
  } else if (upperGrade.includes("PROPHET'S RELATIVE")) {
    return { tabaqah: 'SAHABA', reliability: 'THIQA', is_prophet: false };
  }

  // Default
  return { tabaqah: 'LATER_SCHOLAR', reliability: 'THIQA', is_prophet: false };
}

// Extract locations from text
function extractLocations(text: string | undefined): string[] {
  if (!text) return [];

  const locations: Set<string> = new Set();
  // Simple extraction - comma-separated place names
  const places = text.split(',').map((p) => p.trim()).filter((p) => p.length > 0);

  places.forEach((place) => {
    if (place.length > 0 && place.length < 100) {
      locations.add(place);
    }
  });

  return Array.from(locations);
}

// Parse comma-separated indices
function parseIndices(indicesStr: string): number[] {
  if (!indicesStr) return [];
  return indicesStr
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n));
}

interface NarratorData {
  id: string;
  scholar_indx: number;
  name_english: string;
  name_arabic: string;
  reliability: string;
  tabaqah: string;
  bio: string;
  birth_year_hijri: number | null;
  death_year_hijri: number | null;
  geographic_region: string;
  is_prophet: boolean;
}

interface HadithData {
  id: string;
  title: string;
  primary_topic: string;
  source: string;
  chapter: string;
  chapter_no: string;
  hadith_no: string;
  text_arabic: string;
  text_english: string;
  auto_calculated_grade: string;
  display_grade: string;
  transmission_type: string;
  chain_indx: number[]; // narrator scholar_indx values forming the isnad
}

interface LocationData {
  id: string;
  name: string;
  name_arabic: string;
  modern_country: string;
  description: string;
}

interface SourceData {
  id: string;
  name: string;
  name_arabic: string;
  compiler: string;
  total_hadiths: number;
  description: string;
}

// Read CSV file handling multiline quoted fields
async function readCSV(filePath: string, callback: (row: CSVRow) => Promise<void>) {
  const content = fs.readFileSync(filePath, 'utf8');
  const parser = new CSVParser();

  // Split into logical rows handling multiline quoted fields
  const rows: string[] = [];
  let currentRow = '';
  let insideQuotes = false;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    if (char === '"') {
      insideQuotes = !insideQuotes;
    }
    if ((char === '\n' || char === '\r') && !insideQuotes) {
      if (char === '\r' && content[i + 1] === '\n') i++; // skip \r\n
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

// Create Source nodes for hadith collections
async function createSources() {
  console.log('\n📚 Creating hadith collection sources...');

  const sources: SourceData[] = [
    {
      id: uuidv4(),
      name: 'Sahih Bukhari',
      name_arabic: 'صحيح البخاري',
      compiler: 'Muhammad ibn Ismail al-Bukhari',
      total_hadiths: 7563,
      description: 'One of the most authentic hadith collections in Islam',
    },
    {
      id: uuidv4(),
      name: 'Sahih Muslim',
      name_arabic: 'صحيح مسلم',
      compiler: 'Muslim ibn al-Hajjaj',
      total_hadiths: 7275,
      description: 'Second most authentic hadith collection',
    },
    {
      id: uuidv4(),
      name: 'Sunan an-Nasa\'i',
      name_arabic: 'سنن النسائي',
      compiler: 'Ahmad ibn Shuaib an-Nasa\'i',
      total_hadiths: 5761,
      description: 'Collection of Sunan hadiths',
    },
    {
      id: uuidv4(),
      name: 'Sunan Ibn Majah',
      name_arabic: 'سنن ابن ماجه',
      compiler: 'Muhammad ibn Yazid Ibn Majah',
      total_hadiths: 4341,
      description: 'Collection of Sunan hadiths',
    },
    {
      id: uuidv4(),
      name: 'Sunan Abi Da\'ud',
      name_arabic: 'سنن أبي داود',
      compiler: 'Sulaiman ibn al-Ash\'ath as-Sijistani',
      total_hadiths: 5274,
      description: 'Collection of Sunan hadiths',
    },
    {
      id: uuidv4(),
      name: 'Jami\' al-Tirmidhi',
      name_arabic: 'جامع الترمذي',
      compiler: 'Muhammad ibn Isa at-Tirmidhi',
      total_hadiths: 3956,
      description: 'Comprehensive hadith collection',
    },
  ];

  for (const source of sources) {
    const cypher = `
      MERGE (s:Source {id: $id})
      ON CREATE SET
        s.name = $name,
        s.name_arabic = $name_arabic,
        s.compiler = $compiler,
        s.total_hadiths = $total_hadiths,
        s.description = $description,
        s.created_at = datetime()
      RETURN s.id
    `;

    try {
      await runWrite(cypher, source);
      console.log(`  ✅ ${source.name}`);
    } catch (error) {
      console.error(`  ❌ Failed to create source ${source.name}:`, error);
    }
  }
}

// Import narrators from CSV
async function importNarrators(filePath: string) {
  console.log('\n👥 Importing narrators...');

  const narrators: Map<number, NarratorData> = new Map();
  const locations: Map<string, LocationData> = new Map();
  let processedCount = 0;
  let batch: NarratorData[] = [];
  const BATCH_SIZE = 500;

  await readCSV(filePath, async (row) => {
    const scholarIndx = parseInt(row.scholar_indx, 10);
    if (isNaN(scholarIndx)) return;

    const { english, arabic } = parseName(row.name);
    const { tabaqah, reliability, is_prophet } = mapGradeToTabaqah(row.grade);

    // Extract locations
    const birthPlace = row.birth_place || '';
    const deathPlace = row.death_place || '';
    const placesOfStay = row.places_of_stay || '';

    [birthPlace, deathPlace, ...placesOfStay.split(',')].forEach((place) => {
      const cleanPlace = place.trim();
      if (cleanPlace && cleanPlace.length > 0 && cleanPlace.length < 100) {
        if (!locations.has(cleanPlace)) {
          locations.set(cleanPlace, {
            id: uuidv4(),
            name: cleanPlace,
            name_arabic: '', // Would need more data to populate this
            modern_country: '',
            description: '',
          });
        }
      }
    });

    const narrator: NarratorData = {
      id: uuidv4(),
      scholar_indx: scholarIndx,
      name_english: english,
      name_arabic: arabic,
      reliability,
      tabaqah,
      bio: `${row.area_of_interest || ''} ${row.tags || ''}`.trim(),
      birth_year_hijri: parseInt(row.birth_date_hijri, 10) || null,
      death_year_hijri: parseInt(row.death_date_hijri, 10) || null,
      geographic_region: row.geographic_region || '',
      is_prophet,
    };

    narrators.set(scholarIndx, narrator);
    batch.push(narrator);

    if (batch.length >= BATCH_SIZE) {
      await importNarratorBatch(batch);
      processedCount += batch.length;
      console.log(`  ✓ Processed ${processedCount} narrators...`);
      batch = [];
    }
  });

  // Import remaining batch
  if (batch.length > 0) {
    await importNarratorBatch(batch);
    processedCount += batch.length;
  }

  console.log(`  ✅ Imported ${processedCount} narrators`);

  // Import locations
  console.log('\n🗺️  Creating location nodes...');
  let locationCount = 0;
  const locationBatch: LocationData[] = [];
  const LOC_BATCH_SIZE = 200;

  for (const location of locations.values()) {
    locationBatch.push(location);

    if (locationBatch.length >= LOC_BATCH_SIZE) {
      await importLocationBatch(locationBatch);
      locationCount += locationBatch.length;
      console.log(`  ✓ Created ${locationCount} locations...`);
      locationBatch.length = 0;
    }
  }

  if (locationBatch.length > 0) {
    await importLocationBatch(locationBatch);
    locationCount += locationBatch.length;
  }

  console.log(`  ✅ Created ${locationCount} location nodes`);

  return narrators;
}

async function importNarratorBatch(narrators: NarratorData[]) {
  const queries = narrators.map((narrator) => ({
    query: `
      MERGE (n:Narrator {id: $id})
      ON CREATE SET
        n.scholar_indx = $scholar_indx,
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
    params: narrator,
  }));

  // Execute in smaller batches to avoid overwhelming the DB
  for (let i = 0; i < queries.length; i += 50) {
    const batch = queries.slice(i, i + 50);
    try {
      for (const { query, params } of batch) {
        await runWrite(query, params);
      }
    } catch (error) {
      console.error('Error importing narrator batch:', error);
    }
  }
}

async function importLocationBatch(locations: LocationData[]) {
  for (const location of locations) {
    try {
      await runWrite(
        `
        MERGE (l:Location {id: $id})
        ON CREATE SET
          l.name = $name,
          l.name_arabic = $name_arabic,
          l.modern_country = $modern_country,
          l.description = $description,
          l.created_at = datetime()
        RETURN l.id
      `,
        location
      );
    } catch (error) {
      console.error(`Error creating location ${location.name}:`, error);
    }
  }
}

// Create teacher-student relationships from indices
async function createTeacherStudentRelationships(filePath: string, narrators: Map<number, NarratorData>) {
  console.log('\n🔗 Creating teacher-student HEARD_FROM relationships...');

  let relationshipCount = 0;
  let processedNarrators = 0;
  const relationships: Array<{ studentIndx: number; teacherIndx: number }> = [];

  await readCSV(filePath, async (row) => {
    const scholarIndx = parseInt(row.scholar_indx, 10);
    if (isNaN(scholarIndx) || !narrators.has(scholarIndx)) return;

    // Parse teachers_inds
    const teacherIndices = parseIndices(row.teachers_inds);
    teacherIndices.forEach((teacherIndx) => {
      if (narrators.has(teacherIndx)) {
        relationships.push({ studentIndx: scholarIndx, teacherIndx });
      }
    });

    processedNarrators++;
  });

  console.log(`  Found ${relationships.length} teacher-student relationships`);

  // Create relationships in batches
  for (let i = 0; i < relationships.length; i += 100) {
    const batch = relationships.slice(i, i + 100);

    for (const { studentIndx, teacherIndx } of batch) {
      try {
        await runWrite(
          `
          MATCH (student:Narrator {scholar_indx: $studentIndx})
          MATCH (teacher:Narrator {scholar_indx: $teacherIndx})
          MERGE (student)-[:HEARD_FROM]->(teacher)
          RETURN 1
        `,
          { studentIndx, teacherIndx }
        );
        relationshipCount++;
      } catch (error) {
        console.error(`Failed to create relationship ${studentIndx} -> ${teacherIndx}:`, error);
      }
    }

    if ((i + 100) % 500 === 0) {
      console.log(`  ✓ Created ${relationshipCount} relationships...`);
    }
  }

  console.log(`  ✅ Created ${relationshipCount} teacher-student relationships`);
}

// Import hadiths from CSV
async function importHadiths(filePath: string, narrators: Map<number, NarratorData>) {
  console.log('\n📖 Importing hadiths...');

  let processedCount = 0;
  let batch: HadithData[] = [];
  const BATCH_SIZE = 500;

  await readCSV(filePath, async (row) => {
    const chainIndices = parseIndices(row.chain_indx);
    const hadith: HadithData = {
      id: uuidv4(),
      title: `${row.source || 'Unknown'} ${row.hadith_no || ''}`.trim(),
      primary_topic: row.chapter || 'General',
      source: row.source?.trim() || 'Unknown',
      chapter: row.chapter || '',
      chapter_no: row.chapter_no || '',
      hadith_no: row.hadith_no?.trim() || '',
      text_arabic: row.text_ar || '',
      text_english: row.text_en || '',
      auto_calculated_grade: '',
      display_grade: '',
      transmission_type: '',
      chain_indx: chainIndices,
    };

    batch.push(hadith);

    if (batch.length >= BATCH_SIZE) {
      await importHadithBatch(batch, row.source?.trim() || 'Unknown', narrators);
      processedCount += batch.length;
      console.log(`  ✓ Processed ${processedCount} hadiths...`);
      batch = [];
    }
  });

  // Import remaining batch
  if (batch.length > 0) {
    const lastSource = batch[0].source;
    await importHadithBatch(batch, lastSource, narrators);
    processedCount += batch.length;
  }

  console.log(`  ✅ Imported ${processedCount} hadiths`);
}

async function importHadithBatch(
  hadiths: HadithData[],
  source: string,
  narrators: Map<number, NarratorData>
) {
  for (const hadith of hadiths) {
    try {
      // Create hadith node (exclude chain_indx from Neo4j properties)
      const { chain_indx, ...hadithProps } = hadith;
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
          h.auto_calculated_grade = $auto_calculated_grade,
          h.display_grade = $display_grade,
          h.transmission_type = $transmission_type,
          h.created_at = datetime()
        RETURN h.id
      `,
        hadithProps
      );

      // Link to source
      if (source) {
        await runWrite(
          `
          MATCH (h:Hadith {id: $hadith_id})
          MATCH (s:Source {name: $source_name})
          MERGE (h)-[:FROM_SOURCE]->(s)
        `,
          { hadith_id: hadith.id, source_name: source }
        );
      }

      // Create MatnVariation + Chain + link narrators if chain_indx exists
      if (chain_indx.length > 0) {
        const variationId = uuidv4();
        const chainId = uuidv4();

        // Create MatnVariation with the hadith text
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
            source_book: source,
            text_arabic: hadith.text_arabic,
            text_english: hadith.text_english,
          }
        );

        // Link Hadith -> MatnVariation
        await runWrite(
          `
          MATCH (h:Hadith {id: $hadithId})
          MATCH (m:MatnVariation {id: $variationId})
          CREATE (h)-[:HAS_VARIATION]->(m)
        `,
          { hadithId: hadith.id, variationId }
        );

        // Create Chain node
        await runWrite(
          `
          CREATE (c:Chain {
            id: $id,
            is_golden_chain: false,
            created_at: datetime()
          })
        `,
          { id: chainId }
        );

        // Link MatnVariation -> Chain
        await runWrite(
          `
          MATCH (m:MatnVariation {id: $variationId})
          MATCH (c:Chain {id: $chainId})
          CREATE (m)-[:TRANSMITTED_VIA]->(c)
        `,
          { variationId, chainId }
        );

        // Link Chain -> each Narrator via INCLUDES
        for (const scholarIndx of chain_indx) {
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

        // Create HEARD_FROM relationships between consecutive narrators in the chain
        for (let i = 0; i < chain_indx.length - 1; i++) {
          const studentIndx = chain_indx[i];
          const teacherIndx = chain_indx[i + 1];
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
      }
    } catch (error) {
      console.error(`Error importing hadith ${hadith.id}:`, error);
    }
  }
}

// Main import function
async function main() {
  const args = process.argv.slice(2);
  const shouldClear = args.includes('--clear');

  // Look for datasets in multiple possible locations
  const possiblePaths = [
    path.join(process.cwd(), 'datasets'),
    path.join(process.cwd(), '..', 'datasets'),
    '/sessions/focused-nifty-pascal/datasets',
    path.join(process.cwd(), 'data'),
  ];

  let basePath = '';
  for (const p of possiblePaths) {
    if (fs.existsSync(path.join(p, 'narrator-data/all_rawis.csv'))) {
      basePath = p;
      break;
    }
  }

  // Also check for flat structure
  if (!basePath) {
    for (const p of possiblePaths) {
      if (fs.existsSync(path.join(p, 'all_rawis.csv'))) {
        basePath = p;
        break;
      }
    }
  }

  if (!basePath) {
    console.log('Looking in these paths:', possiblePaths);
    throw new Error('Could not find dataset files. Place all_rawis.csv and all_hadiths_clean.csv in a datasets/ directory.');
  }

  const narratorPath = fs.existsSync(path.join(basePath, 'narrator-data/all_rawis.csv'))
    ? path.join(basePath, 'narrator-data/all_rawis.csv')
    : path.join(basePath, 'all_rawis.csv');
  const hadithPath = fs.existsSync(path.join(basePath, 'hadith-data/all_hadiths_clean.csv'))
    ? path.join(basePath, 'hadith-data/all_hadiths_clean.csv')
    : path.join(basePath, 'all_hadiths_clean.csv');

  try {
    console.log('🚀 Starting Neo4j dataset import...\n');
    console.log(`📁 Narrator data: ${narratorPath}`);
    console.log(`📁 Hadith data: ${hadithPath}`);

    // Verify files exist
    if (!fs.existsSync(narratorPath)) {
      throw new Error(`Narrator CSV not found at ${narratorPath}`);
    }
    if (!fs.existsSync(hadithPath)) {
      throw new Error(`Hadith CSV not found at ${hadithPath}`);
    }

    // Initialize schema
    console.log('\n🔧 Initializing database schema...');
    await initializeSchema();

    // Clear database if requested
    if (shouldClear) {
      console.log('\n🗑️  Clearing database as requested...');
      await clearDatabase();
    }

    // Create sources
    await createSources();

    // Import narrators and locations
    const narrators = await importNarrators(narratorPath);

    // Create teacher-student relationships
    await createTeacherStudentRelationships(narratorPath, narrators);

    // Import hadiths
    await importHadiths(hadithPath, narrators);

    // Print summary with live DB counts
    console.log('\n' + '='.repeat(60));
    console.log('✅ Import completed successfully!');
    console.log('='.repeat(60));
    console.log(`Narrators parsed from CSV: ${narrators.size}`);

    try {
      const stats = await runQuery(`
        MATCH (n:Narrator) WITH count(n) as narrators
        MATCH (h:Hadith) WITH narrators, count(h) as hadiths
        MATCH ()-[r:HEARD_FROM]->() WITH narrators, hadiths, count(r) as heardFromRels
        MATCH (c:Chain) WITH narrators, hadiths, heardFromRels, count(c) as chains
        MATCH (m:MatnVariation) WITH narrators, hadiths, heardFromRels, chains, count(m) as variations
        MATCH (l:Location) WITH narrators, hadiths, heardFromRels, chains, variations, count(l) as locations
        MATCH (s:Source) WITH narrators, hadiths, heardFromRels, chains, variations, locations, count(s) as sources
        RETURN narrators, hadiths, heardFromRels, chains, variations, locations, sources
      `);

      if (stats.length > 0) {
        const s = stats[0];
        console.log('\n📊 Database Statistics:');
        console.log(`  Narrators:           ${s.narrators}`);
        console.log(`  Hadiths:             ${s.hadiths}`);
        console.log(`  Chains:              ${s.chains}`);
        console.log(`  Matn Variations:     ${s.variations}`);
        console.log(`  HEARD_FROM rels:     ${s.heardFromRels}`);
        console.log(`  Locations:           ${s.locations}`);
        console.log(`  Sources:             ${s.sources}`);
      }
    } catch (error) {
      console.log('(Could not fetch DB stats)');
    }
    console.log('');
  } catch (error) {
    console.error('\n❌ Import failed:', error);
    process.exit(1);
  } finally {
    await closeDriver();
  }
}

main();
