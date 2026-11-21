/**
 * diagnose-db.ts
 * Read-only diagnostic: counts nodes/rels, checks the key migration indicators.
 * Usage: tsx src/scripts/diagnose-db.ts
 */

import { loadEnv } from './lib/env';
import { runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
  try {
    console.log('\n=== NODE COUNTS BY LABEL ===');
    const nodeRows = await runQuery<{ label: string; count: unknown }>(
      `CALL db.labels() YIELD label
       CALL {
         WITH label
         MATCH (n) WHERE label IN labels(n)
         RETURN count(n) AS count
       }
       RETURN label, count
       ORDER BY count DESC`
    );
    for (const r of nodeRows) {
      console.log(`  ${r.label.padEnd(28)} ${Number(r.count)}`);
    }

    console.log('\n=== RELATIONSHIP COUNTS BY TYPE ===');
    const relRows = await runQuery<{ type: string; count: unknown }>(
      `CALL db.relationshipTypes() YIELD relationshipType AS type
       CALL {
         WITH type
         MATCH ()-[r]->() WHERE type(r) = type
         RETURN count(r) AS count
       }
       RETURN type, count
       ORDER BY count DESC`
    );
    for (const r of relRows) {
      console.log(`  ${r.type.padEnd(28)} ${Number(r.count)}`);
    }

    console.log('\n=== HADITH LANGUAGE COVERAGE ===');
    const lang = await runQuery<{ total: unknown; with_en: unknown; with_ar: unknown }>(
      `MATCH (h:Hadith)
       RETURN count(h) AS total,
              count(CASE WHEN h.text_english IS NOT NULL AND h.text_english <> '' THEN 1 END) AS with_en,
              count(CASE WHEN h.text_arabic  IS NOT NULL AND h.text_arabic  <> '' THEN 1 END) AS with_ar`
    );
    if (lang[0]) {
      console.log(`  Total Hadiths       : ${Number(lang[0].total)}`);
      console.log(`  With text_english   : ${Number(lang[0].with_en)}`);
      console.log(`  With text_arabic    : ${Number(lang[0].with_ar)}`);
    }

    console.log('\n=== HADITH ID SHAPES ===');
    const idShapes = await runQuery<{ shape: string; count: unknown }>(
      `MATCH (h:Hadith)
       WITH h, h.id AS hid
       WITH CASE
              WHEN hid STARTS WITH 'musnad_' THEN 'musnad_*'
              WHEN hid =~ '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' THEN 'uuid_v4'
              ELSE 'other'
            END AS shape
       RETURN shape, count(*) AS count
       ORDER BY count DESC`
    );
    for (const r of idShapes) {
      console.log(`  ${r.shape.padEnd(20)} ${Number(r.count)}`);
    }

    console.log('\n=== TRADITION STRING PROPERTY USAGE ===');
    const tradH = await runQuery<{ tradition: string | null; count: unknown }>(
      `MATCH (h:Hadith) RETURN h.tradition AS tradition, count(*) AS count ORDER BY count DESC`
    );
    console.log('  Hadith.tradition:');
    for (const r of tradH) console.log(`    ${String(r.tradition).padEnd(28)} ${Number(r.count)}`);

    const tradN = await runQuery<{ tradition: string | null; count: unknown }>(
      `MATCH (n:Narrator) RETURN n.tradition AS tradition, count(*) AS count ORDER BY count DESC`
    );
    console.log('  Narrator.tradition:');
    for (const r of tradN) console.log(`    ${String(r.tradition).padEnd(28)} ${Number(r.count)}`);

    const tradS = await runQuery<{ tradition: string | null; count: unknown }>(
      `MATCH (s:Source) RETURN s.tradition AS tradition, count(*) AS count ORDER BY count DESC`
    );
    console.log('  Source.tradition:');
    for (const r of tradS) console.log(`    ${String(r.tradition).padEnd(28)} ${Number(r.count)}`);

    console.log('\n=== EXISTING CROSS-CULTURAL PARALLELS ===');
    const parallels = await runQuery<{ count: unknown }>(
      `MATCH (p:CrossCulturalParallel) RETURN count(p) AS count`
    );
    console.log(`  CrossCulturalParallel count: ${Number(parallels[0]?.count ?? 0)}`);

    const parallelsByTradition = await runQuery<{ tradition: string; count: unknown }>(
      `MATCH (p:CrossCulturalParallel)-[:FROM_TRADITION]->(t:ReligiousTradition)
       RETURN t.name AS tradition, count(p) AS count
       ORDER BY count DESC`
    );
    for (const r of parallelsByTradition) {
      console.log(`    ${r.tradition.padEnd(28)} ${Number(r.count)}`);
    }

    console.log('\n=== SCHEMA CONSTRAINTS ===');
    const constraints = await runQuery<{ name: string; labelsOrTypes: unknown; properties: unknown }>(
      `SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties`
    );
    console.log(`  Total constraints: ${constraints.length}`);
    for (const c of constraints) {
      console.log(`    ${c.name}  ${JSON.stringify(c.labelsOrTypes)}.${JSON.stringify(c.properties)}`);
    }

    console.log('\n=== DB SIZE ESTIMATE ===');
    const totals = await runQuery<{ nodes: unknown; rels: unknown }>(
      `MATCH (n) WITH count(n) AS nodes
       MATCH ()-[r]->() RETURN nodes, count(r) AS rels`
    );
    if (totals[0]) {
      console.log(`  Total nodes        : ${Number(totals[0].nodes)}`);
      console.log(`  Total relationships: ${Number(totals[0].rels)}`);
    }

    console.log('\n✅ Diagnosis complete.\n');
  } catch (err) {
    console.error('❌ Diagnosis failed:', err);
    process.exit(1);
  } finally {
    await closeDriver();
  }
}

main();
