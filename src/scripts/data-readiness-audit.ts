/**
 * data-readiness-audit.ts
 * ========================
 * Comprehensive audit of data readiness for Neo4j GDS graph analytics
 * and vector embedding pipelines.
 *
 * Checks:
 *   1. Narrator node completeness for centrality/community detection
 *   2. HEARD_FROM relationship coverage for chain analysis
 *   3. Hadith text quality for embedding
 *   4. ScholarVerdict and scholarly metadata population
 *   5. Data quality issues (orphans, broken chains, OCR artifacts)
 *   6. Graph connectivity for meaningful GDS analysis
 *
 * Usage: npx tsx src/scripts/data-readiness-audit.ts
 */

import { loadEnv } from './lib/env';
import { runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

interface AuditResult {
    category: string;
    check: string;
    status: 'PASS' | 'WARN' | 'FAIL' | 'INFO';
    detail: string;
}

const results: AuditResult[] = [];

function log(r: AuditResult) {
    const icon = r.status === 'PASS' ? '[PASS]' : r.status === 'WARN' ? '[WARN]' : r.status === 'FAIL' ? '[FAIL]' : '[INFO]';
    console.log(`  ${icon} ${r.check}: ${r.detail}`);
    results.push(r);
}

async function auditNarratorCompleteness() {
    console.log('\n========================================');
    console.log('  1. NARRATOR NODE COMPLETENESS');
    console.log('========================================');

    const total = await runQuery<{ count: number }>(
        `MATCH (n:Narrator) RETURN count(n) AS count`
    );
    const narratorCount = Number(total[0]?.count ?? 0);
    log({ category: 'narrator', check: 'Total Narrator nodes', status: 'INFO', detail: `${narratorCount}` });

    // Field coverage
    const fields = ['reliability', 'tabaqah', 'death_year_hijri', 'geographic_region',
                     'name_arabic', 'name_english', 'birth_year_hijri', 'scholar_indx'];

    for (const field of fields) {
        const r = await runQuery<{ populated: number }>(
            `MATCH (n:Narrator) WHERE n.${field} IS NOT NULL AND n.${field} <> '' RETURN count(n) AS populated`
        );
        const populated = Number(r[0]?.populated ?? 0);
        const pct = narratorCount > 0 ? ((populated / narratorCount) * 100).toFixed(1) : '0';
        const status = parseFloat(pct) >= 80 ? 'PASS' : parseFloat(pct) >= 50 ? 'WARN' : 'FAIL';
        log({ category: 'narrator', check: `Narrator.${field}`, status, detail: `${populated}/${narratorCount} (${pct}%)` });
    }

    // Tradition breakdown
    const traditions = await runQuery<{ tradition: string | null; count: number }>(
        `MATCH (n:Narrator) RETURN n.tradition AS tradition, count(n) AS count ORDER BY count DESC`
    );
    for (const t of traditions) {
        log({ category: 'narrator', check: `Narrators in tradition`, status: 'INFO', detail: `${t.tradition ?? 'NULL'}: ${Number(t.count)}` });
    }
}

async function auditChainConnectivity() {
    console.log('\n========================================');
    console.log('  2. HEARD_FROM / CHAIN CONNECTIVITY');
    console.log('========================================');

    // HEARD_FROM relationships
    const heardFrom = await runQuery<{ count: number }>(
        `MATCH ()-[r:HEARD_FROM]->() RETURN count(r) AS count`
    );
    const hfCount = Number(heardFrom[0]?.count ?? 0);
    log({ category: 'chain', check: 'HEARD_FROM relationships', status: hfCount > 100 ? 'PASS' : hfCount > 0 ? 'WARN' : 'FAIL', detail: `${hfCount}` });

    // Chain nodes
    const chains = await runQuery<{ count: number }>(
        `MATCH (c:Chain) RETURN count(c) AS count`
    );
    const chainCount = Number(chains[0]?.count ?? 0);
    log({ category: 'chain', check: 'Chain nodes', status: chainCount > 0 ? 'PASS' : 'FAIL', detail: `${chainCount}` });

    // MatnVariation nodes
    const matns = await runQuery<{ count: number }>(
        `MATCH (m:MatnVariation) RETURN count(m) AS count`
    );
    log({ category: 'chain', check: 'MatnVariation nodes', status: Number(matns[0]?.count ?? 0) > 0 ? 'PASS' : 'WARN', detail: `${Number(matns[0]?.count ?? 0)}` });

    // INCLUDES relationships (Chain → Narrator)
    const includes = await runQuery<{ count: number }>(
        `MATCH ()-[r:INCLUDES]->() RETURN count(r) AS count`
    );
    log({ category: 'chain', check: 'INCLUDES (Chain->Narrator)', status: Number(includes[0]?.count ?? 0) > 0 ? 'PASS' : 'WARN', detail: `${Number(includes[0]?.count ?? 0)}` });

    // Narrators with HEARD_FROM connections
    const narratorsConnected = await runQuery<{ connected: number; total: number }>(
        `MATCH (n:Narrator)
         OPTIONAL MATCH (n)-[:HEARD_FROM]-()
         WITH n, count(*) > 0 AS hasHF
         RETURN count(CASE WHEN hasHF THEN 1 END) AS connected, count(n) AS total`
    );
    if (narratorsConnected[0]) {
        const c = Number(narratorsConnected[0].connected);
        const t = Number(narratorsConnected[0].total);
        const pct = t > 0 ? ((c / t) * 100).toFixed(1) : '0';
        log({ category: 'chain', check: 'Narrators with HEARD_FROM edges', status: parseFloat(pct) >= 30 ? 'PASS' : 'WARN', detail: `${c}/${t} (${pct}%)` });
    }

    // Avg chain length
    if (chainCount > 0) {
        const avgLen = await runQuery<{ avg_len: number }>(
            `MATCH (c:Chain)-[:INCLUDES]->(n:Narrator)
             WITH c, count(n) AS len
             RETURN avg(len) AS avg_len`
        );
        log({ category: 'chain', check: 'Average chain length (narrators)', status: 'INFO', detail: `${Number(avgLen[0]?.avg_len ?? 0).toFixed(1)}` });
    }

    // Hadith → Chain path completeness
    const hadithWithChain = await runQuery<{ linked: number; total: number }>(
        `MATCH (h:Hadith)
         OPTIONAL MATCH (h)-[:HAS_VARIATION]->(:MatnVariation)-[:TRANSMITTED_VIA]->(c:Chain)
         WITH h, count(c) > 0 AS hasChain
         RETURN count(CASE WHEN hasChain THEN 1 END) AS linked, count(h) AS total`
    );
    if (hadithWithChain[0]) {
        const l = Number(hadithWithChain[0].linked);
        const t = Number(hadithWithChain[0].total);
        const pct = t > 0 ? ((l / t) * 100).toFixed(1) : '0';
        log({ category: 'chain', check: 'Hadiths with linked chains', status: parseFloat(pct) >= 50 ? 'PASS' : 'WARN', detail: `${l}/${t} (${pct}%)` });
    }
}

async function auditTextQuality() {
    console.log('\n========================================');
    console.log('  3. TEXT DATA QUALITY (EMBEDDING READINESS)');
    console.log('========================================');

    const total = await runQuery<{ count: number }>(
        `MATCH (h:Hadith) RETURN count(h) AS count`
    );
    const hadithCount = Number(total[0]?.count ?? 0);
    log({ category: 'text', check: 'Total Hadith nodes', status: 'INFO', detail: `${hadithCount}` });

    // Arabic text presence
    const arPresent = await runQuery<{ count: number }>(
        `MATCH (h:Hadith) WHERE h.text_arabic IS NOT NULL AND size(h.text_arabic) > 10 RETURN count(h) AS count`
    );
    const arPct = hadithCount > 0 ? ((Number(arPresent[0]?.count ?? 0) / hadithCount) * 100).toFixed(1) : '0';
    log({ category: 'text', check: 'Arabic text (>10 chars)', status: parseFloat(arPct) >= 80 ? 'PASS' : 'WARN', detail: `${Number(arPresent[0]?.count ?? 0)}/${hadithCount} (${arPct}%)` });

    // English text presence
    const enPresent = await runQuery<{ count: number }>(
        `MATCH (h:Hadith) WHERE h.text_english IS NOT NULL AND size(h.text_english) > 10 RETURN count(h) AS count`
    );
    const enPct = hadithCount > 0 ? ((Number(enPresent[0]?.count ?? 0) / hadithCount) * 100).toFixed(1) : '0';
    log({ category: 'text', check: 'English text (>10 chars)', status: parseFloat(enPct) >= 70 ? 'PASS' : 'WARN', detail: `${Number(enPresent[0]?.count ?? 0)}/${hadithCount} (${enPct}%)` });

    // Text length stats
    const lenStats = await runQuery<{ min_ar: number; avg_ar: number; max_ar: number; min_en: number; avg_en: number; max_en: number }>(
        `MATCH (h:Hadith)
         WHERE h.text_arabic IS NOT NULL AND h.text_english IS NOT NULL
         RETURN min(size(h.text_arabic)) AS min_ar, avg(size(h.text_arabic)) AS avg_ar, max(size(h.text_arabic)) AS max_ar,
                min(size(h.text_english)) AS min_en, avg(size(h.text_english)) AS avg_en, max(size(h.text_english)) AS max_en`
    );
    if (lenStats[0]) {
        log({ category: 'text', check: 'Arabic text length (min/avg/max)', status: 'INFO',
              detail: `${Number(lenStats[0].min_ar)}/${Number(lenStats[0].avg_ar).toFixed(0)}/${Number(lenStats[0].max_ar)}` });
        log({ category: 'text', check: 'English text length (min/avg/max)', status: 'INFO',
              detail: `${Number(lenStats[0].min_en)}/${Number(lenStats[0].avg_en).toFixed(0)}/${Number(lenStats[0].max_en)}` });
    }

    // Very short texts (likely fragments or errors)
    const shortAr = await runQuery<{ count: number }>(
        `MATCH (h:Hadith) WHERE h.text_arabic IS NOT NULL AND size(h.text_arabic) < 20 AND size(h.text_arabic) > 0 RETURN count(h) AS count`
    );
    log({ category: 'text', check: 'Very short Arabic texts (<20 chars)', status: Number(shortAr[0]?.count ?? 0) > 50 ? 'WARN' : 'PASS',
          detail: `${Number(shortAr[0]?.count ?? 0)}` });

    // Texts with potential OCR artifacts (non-Arabic characters mixed in)
    const ocrArtifacts = await runQuery<{ count: number }>(
        `MATCH (h:Hadith)
         WHERE h.text_arabic IS NOT NULL
           AND h.text_arabic =~ '.*[0-9]{3,}.*'
         RETURN count(h) AS count`
    );
    log({ category: 'text', check: 'Arabic texts with numeric sequences (OCR?)', status: Number(ocrArtifacts[0]?.count ?? 0) > 100 ? 'WARN' : 'PASS',
          detail: `${Number(ocrArtifacts[0]?.count ?? 0)}` });

    // Texts with refusal artifacts from AI translation
    const refusals = await runQuery<{ count: number }>(
        `MATCH (h:Hadith)
         WHERE h.text_english IS NOT NULL
           AND (h.text_english CONTAINS 'I cannot' OR h.text_english CONTAINS 'I can\\'t' OR h.text_english CONTAINS 'I\\'m unable')
         RETURN count(h) AS count`
    );
    log({ category: 'text', check: 'English texts with AI refusal artifacts', status: Number(refusals[0]?.count ?? 0) > 0 ? 'WARN' : 'PASS',
          detail: `${Number(refusals[0]?.count ?? 0)}` });

    // Tradition breakdown for text coverage
    const tradCoverage = await runQuery<{ tradition: string | null; total: number; with_ar: number; with_en: number }>(
        `MATCH (h:Hadith)
         WITH h.tradition AS tradition, count(h) AS total,
              count(CASE WHEN h.text_arabic IS NOT NULL AND size(h.text_arabic) > 10 THEN 1 END) AS with_ar,
              count(CASE WHEN h.text_english IS NOT NULL AND size(h.text_english) > 10 THEN 1 END) AS with_en
         RETURN tradition, total, with_ar, with_en
         ORDER BY total DESC`
    );
    for (const t of tradCoverage) {
        log({ category: 'text', check: `Text coverage [${t.tradition ?? 'NULL'}]`, status: 'INFO',
              detail: `total=${Number(t.total)} ar=${Number(t.with_ar)} en=${Number(t.with_en)}` });
    }
}

async function auditScholarlyMetadata() {
    console.log('\n========================================');
    console.log('  4. SCHOLARLY METADATA POPULATION');
    console.log('========================================');

    const nodeTypes = ['Scholar', 'ScholarVerdict', 'Commentary', 'SchoolOfThought', 'Practice'];
    for (const label of nodeTypes) {
        const r = await runQuery<{ count: number }>(
            `MATCH (n:${label}) RETURN count(n) AS count`
        );
        const count = Number(r[0]?.count ?? 0);
        log({ category: 'scholarly', check: `${label} nodes`, status: count > 0 ? 'PASS' : 'WARN', detail: `${count}` });
    }

    // Hadith grade coverage
    const graded = await runQuery<{ grade: string | null; count: number }>(
        `MATCH (h:Hadith)
         RETURN h.display_grade AS grade, count(h) AS count
         ORDER BY count DESC`
    );
    console.log('  Grade distribution:');
    for (const g of graded) {
        log({ category: 'scholarly', check: `Hadith grade [${g.grade ?? 'NULL'}]`, status: 'INFO', detail: `${Number(g.count)}` });
    }

    // Source coverage
    const sources = await runQuery<{ count: number }>(
        `MATCH (s:Source) RETURN count(s) AS count`
    );
    log({ category: 'scholarly', check: 'Source nodes', status: Number(sources[0]?.count ?? 0) > 0 ? 'PASS' : 'WARN', detail: `${Number(sources[0]?.count ?? 0)}` });

    // HistoricalEvent / Location
    for (const label of ['HistoricalEvent', 'Location']) {
        const r = await runQuery<{ count: number }>(
            `MATCH (n:${label}) RETURN count(n) AS count`
        );
        log({ category: 'scholarly', check: `${label} nodes`, status: 'INFO', detail: `${Number(r[0]?.count ?? 0)}` });
    }

    // CrossCulturalParallel + MotifTag
    for (const label of ['CrossCulturalParallel', 'MotifTag', 'ReligiousTradition', 'SourceText']) {
        const r = await runQuery<{ count: number }>(
            `MATCH (n:${label}) RETURN count(n) AS count`
        );
        log({ category: 'scholarly', check: `${label} nodes`, status: 'INFO', detail: `${Number(r[0]?.count ?? 0)}` });
    }
}

async function auditDataQuality() {
    console.log('\n========================================');
    console.log('  5. DATA QUALITY ISSUES');
    console.log('========================================');

    // Orphan narrators (no relationships at all)
    const orphanNarrators = await runQuery<{ count: number }>(
        `MATCH (n:Narrator) WHERE NOT (n)--() RETURN count(n) AS count`
    );
    const orphanCount = Number(orphanNarrators[0]?.count ?? 0);
    log({ category: 'quality', check: 'Orphan Narrators (no relationships)', status: orphanCount > 100 ? 'WARN' : 'PASS', detail: `${orphanCount}` });

    // Orphan hadiths (no relationships)
    const orphanHadiths = await runQuery<{ count: number }>(
        `MATCH (h:Hadith) WHERE NOT (h)--() RETURN count(h) AS count`
    );
    log({ category: 'quality', check: 'Orphan Hadiths (no relationships)', status: Number(orphanHadiths[0]?.count ?? 0) > 50 ? 'WARN' : 'PASS',
          detail: `${Number(orphanHadiths[0]?.count ?? 0)}` });

    // Duplicate narrator names
    const dupes = await runQuery<{ name: string; count: number }>(
        `MATCH (n:Narrator) WHERE n.name_arabic IS NOT NULL
         WITH n.name_arabic AS name, count(*) AS count
         WHERE count > 1
         RETURN name, count ORDER BY count DESC LIMIT 10`
    );
    log({ category: 'quality', check: 'Duplicate Arabic narrator names', status: dupes.length > 5 ? 'WARN' : 'PASS',
          detail: `${dupes.length} names with duplicates. Top: ${dupes.slice(0, 3).map(d => `"${d.name}"(${Number(d.count)})`).join(', ')}` });

    // Missing hadith IDs
    const missingIds = await runQuery<{ count: number }>(
        `MATCH (h:Hadith) WHERE h.id IS NULL OR h.id = '' RETURN count(h) AS count`
    );
    log({ category: 'quality', check: 'Hadiths with missing/empty ID', status: Number(missingIds[0]?.count ?? 0) > 0 ? 'FAIL' : 'PASS',
          detail: `${Number(missingIds[0]?.count ?? 0)}` });

    // Hadith source breakdown
    const sourceDist = await runQuery<{ source: string | null; count: number }>(
        `MATCH (h:Hadith) RETURN h.source AS source, count(h) AS count ORDER BY count DESC`
    );
    console.log('  Hadith by source:');
    for (const s of sourceDist) {
        log({ category: 'quality', check: `Source: ${s.source ?? 'NULL'}`, status: 'INFO', detail: `${Number(s.count)}` });
    }
}

async function auditGraphConnectivity() {
    console.log('\n========================================');
    console.log('  6. GRAPH CONNECTIVITY (GDS READINESS)');
    console.log('========================================');

    // Total nodes and relationships
    const totals = await runQuery<{ nodes: number; rels: number }>(
        `MATCH (n) WITH count(n) AS nodes
         MATCH ()-[r]->() RETURN nodes, count(r) AS rels`
    );
    if (totals[0]) {
        log({ category: 'connectivity', check: 'Total nodes', status: 'INFO', detail: `${Number(totals[0].nodes)}` });
        log({ category: 'connectivity', check: 'Total relationships', status: 'INFO', detail: `${Number(totals[0].rels)}` });
    }

    // All relationship types and counts
    const relTypes = await runQuery<{ type: string; count: number }>(
        `CALL db.relationshipTypes() YIELD relationshipType AS type
         CALL { WITH type MATCH ()-[r]->() WHERE type(r) = type RETURN count(r) AS count }
         RETURN type, count ORDER BY count DESC`
    );
    for (const r of relTypes) {
        log({ category: 'connectivity', check: `Rel: ${r.type}`, status: 'INFO', detail: `${Number(r.count)}` });
    }

    // Narrator network density (for GDS)
    const narratorNetwork = await runQuery<{ narrators: number; heardFrom: number }>(
        `MATCH (n:Narrator) WITH count(n) AS narrators
         MATCH (:Narrator)-[r:HEARD_FROM]->(:Narrator) RETURN narrators, count(r) AS heardFrom`
    );
    if (narratorNetwork[0]) {
        const n = Number(narratorNetwork[0].narrators);
        const hf = Number(narratorNetwork[0].heardFrom);
        const density = n > 1 ? (hf / (n * (n - 1))).toFixed(6) : '0';
        log({ category: 'connectivity', check: 'Narrator network density', status: 'INFO', detail: `${hf} edges among ${n} narrators (density=${density})` });
        log({ category: 'connectivity', check: 'GDS minimum viability (>100 nodes, >200 edges)', status: n > 100 && hf > 200 ? 'PASS' : 'FAIL',
              detail: `${n} nodes, ${hf} edges` });
    }

    // Weakly connected components estimate (sample-based)
    const isolates = await runQuery<{ isolated: number; total: number }>(
        `MATCH (n:Narrator)
         OPTIONAL MATCH (n)-[:HEARD_FROM]-()
         WITH n, count(*) > 0 AS connected
         RETURN count(CASE WHEN NOT connected THEN 1 END) AS isolated, count(n) AS total`
    );
    if (isolates[0]) {
        const iso = Number(isolates[0].isolated);
        const tot = Number(isolates[0].total);
        log({ category: 'connectivity', check: 'Isolated narrators (no HEARD_FROM)', status: 'INFO', detail: `${iso}/${tot}` });
    }

    // Check if GDS library is available
    try {
        await runQuery(`RETURN gds.version() AS version`);
        log({ category: 'connectivity', check: 'Neo4j GDS library', status: 'PASS', detail: 'Available' });
    } catch {
        log({ category: 'connectivity', check: 'Neo4j GDS library', status: 'WARN', detail: 'NOT INSTALLED - required for centrality/community detection' });
    }

    // Check existing indexes
    const indexes = await runQuery<{ name: string; type: string; labelsOrTypes: any }>(
        `SHOW INDEXES YIELD name, type, labelsOrTypes WHERE type <> 'LOOKUP' RETURN name, type, labelsOrTypes`
    );
    log({ category: 'connectivity', check: 'Existing indexes (non-lookup)', status: 'INFO', detail: `${indexes.length} indexes` });

    // Check for vector indexes
    const vectorIndexes = indexes.filter(i => i.type === 'VECTOR');
    log({ category: 'connectivity', check: 'Vector indexes', status: vectorIndexes.length > 0 ? 'PASS' : 'INFO',
          detail: vectorIndexes.length > 0 ? `${vectorIndexes.length} found` : 'None yet (expected - will be created in embedding phase)' });
}

async function main() {
    console.log('='.repeat(50));
    console.log('  DATA READINESS AUDIT');
    console.log('  Neo4j GDS + Vector Embedding Pipeline');
    console.log('='.repeat(50));

    try {
        await auditNarratorCompleteness();
        await auditChainConnectivity();
        await auditTextQuality();
        await auditScholarlyMetadata();
        await auditDataQuality();
        await auditGraphConnectivity();

        // Summary
        console.log('\n' + '='.repeat(50));
        console.log('  SUMMARY');
        console.log('='.repeat(50));

        const passes = results.filter(r => r.status === 'PASS').length;
        const warns = results.filter(r => r.status === 'WARN').length;
        const fails = results.filter(r => r.status === 'FAIL').length;
        const infos = results.filter(r => r.status === 'INFO').length;

        console.log(`\n  PASS: ${passes}  |  WARN: ${warns}  |  FAIL: ${fails}  |  INFO: ${infos}`);

        if (fails > 0) {
            console.log('\n  FAILURES:');
            for (const r of results.filter(r => r.status === 'FAIL')) {
                console.log(`    [FAIL] ${r.check}: ${r.detail}`);
            }
        }

        if (warns > 0) {
            console.log('\n  WARNINGS:');
            for (const r of results.filter(r => r.status === 'WARN')) {
                console.log(`    [WARN] ${r.check}: ${r.detail}`);
            }
        }

        console.log('\n  READINESS ASSESSMENT:');
        if (fails === 0 && warns <= 3) {
            console.log('    READY - Data is suitable for GDS analytics and embedding pipeline');
        } else if (fails <= 2 && warns <= 6) {
            console.log('    PARTIAL - Can proceed with GDS analytics; address warnings before embedding');
        } else {
            console.log('    NOT READY - Address failures and critical warnings before proceeding');
        }

        console.log('');
    } catch (err) {
        console.error('\nAudit failed:', err);
        process.exit(1);
    } finally {
        await closeDriver();
    }
}

main();
