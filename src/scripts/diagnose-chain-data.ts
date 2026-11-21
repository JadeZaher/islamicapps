/**
 * Diagnose chain data integrity issues.
 *
 * Specifically investigates:
 *   1. The exact chain for hadith 626a2cb0-2268-4c79-9ffb-d9f6eaf42ec9
 *      (user reported the visual chain shows 8 narrators but the sanad text
 *       only describes 3: Qutayba → Abu Awana → Smak)
 *   2. Whether imami hadith have any chains at all
 *   3. Per-source coverage of (h)-[:HAS_CHAIN]->(:Chain)-[:INCLUDES]
 *
 * Run with:
 *   npx tsx src/scripts/diagnose-chain-data.ts
 */
import neo4j from 'neo4j-driver';
import 'dotenv/config';

const TARGET_HADITH = '626a2cb0-2268-4c79-9ffb-d9f6eaf42ec9';

function numericValue(value: unknown): number {
    if (typeof value === 'number') return value;
    if (neo4j.isInt(value)) return value.toNumber();
    return 0;
}

async function main() {
    const uri = process.env.NEO4J_URL!;
    const fullUri = uri.startsWith('bolt://') || uri.startsWith('neo4j://') ? uri : `bolt://${uri}`;
    const driver = neo4j.driver(fullUri, neo4j.auth.basic(process.env.NEO4J_USERNAME!, process.env.NEO4J_PASSWORD!));
    const session = driver.session();

    try {
        console.log('=== 1. TARGET HADITH:', TARGET_HADITH, '===\n');

        const hadith = await session.run(
            `MATCH (h:Hadith {id: $id})
             RETURN h.id AS id, h.source AS source, h.tradition AS tradition,
                    h.chapter AS chapter, h.category AS category,
                    h.hadith_no AS hadith_no, h.sanad AS sanad,
                    substring(coalesce(h.matn_ar, h.text_ar, ''), 0, 200) AS matn_preview`,
            { id: TARGET_HADITH }
        );
        if (hadith.records.length === 0) {
            console.log('  NOT FOUND in DB');
        } else {
            const r = hadith.records[0];
            console.log('  source     :', r.get('source'));
            console.log('  tradition  :', r.get('tradition'));
            console.log('  chapter    :', r.get('chapter'));
            console.log('  hadith_no  :', r.get('hadith_no'));
            console.log('  sanad text :', r.get('sanad'));
            console.log('  matn (200) :', r.get('matn_preview'));
        }

        console.log('\n=== 2. Chains for this hadith ===\n');
        const chains = await session.run(
            `MATCH (h:Hadith {id: $id})-[:HAS_CHAIN]->(c:Chain)
             OPTIONAL MATCH (c)-[i:INCLUDES]->(n:Narrator)
             RETURN c.id AS chain_id, c.extraction_method AS method,
                    c.source AS chain_source,
                    count(n) AS narrator_count,
                    collect({pos: i.position, id: n.id, name_en: n.name_english, name_ar: n.name_arabic}) AS narrators
             ORDER BY chain_id`,
            { id: TARGET_HADITH }
        );
        console.log(`  Found ${chains.records.length} Chain node(s) attached to this hadith`);
        for (const rec of chains.records) {
            console.log('\n  Chain:', rec.get('chain_id'));
            console.log('    method      :', rec.get('method'));
            console.log('    chain.source:', rec.get('chain_source'));
            console.log('    narrators   :', rec.get('narrator_count').toNumber());
            const narrators = rec.get('narrators') as Array<{ pos: unknown; id: string; name_en: string; name_ar: string }>;
            narrators
                .filter(n => n.id)
                .sort((a, b) => {
                    const pa = numericValue(a.pos);
                    const pb = numericValue(b.pos);
                    return pa - pb;
                })
                .forEach(n => {
                    const pos = numericValue(n.pos);
                    console.log(`      [pos=${pos}] ${n.name_en} / ${n.name_ar} (${n.id})`);
                });
        }

        console.log('\n=== 3. Per-source / per-tradition chain coverage ===\n');
        const coverage = await session.run(
            `MATCH (h:Hadith)
             OPTIONAL MATCH (h)-[:HAS_CHAIN]->(c:Chain)
             OPTIONAL MATCH (c)-[:INCLUDES]->(n:Narrator)
             WITH h.source AS source, h.tradition AS tradition,
                  h.id AS hid,
                  count(DISTINCT c) AS chains,
                  count(DISTINCT n) AS narrators
             RETURN source, tradition,
                    count(hid) AS total_hadith,
                    sum(CASE WHEN chains > 0 THEN 1 ELSE 0 END) AS with_chain,
                    sum(CASE WHEN narrators > 0 THEN 1 ELSE 0 END) AS with_narrators,
                    avg(narrators) AS avg_narrators_per_hadith,
                    max(narrators) AS max_narrators_per_hadith
             ORDER BY source, tradition`
        );
        console.log('  source | tradition | total | with_chain | with_narrators | avg_n | max_n');
        console.log('  ' + '-'.repeat(95));
        for (const rec of coverage.records) {
            const src = rec.get('source') ?? '(null)';
            const trad = rec.get('tradition') ?? '(null)';
            const tot = rec.get('total_hadith').toNumber();
            const wc = rec.get('with_chain').toNumber();
            const wn = rec.get('with_narrators').toNumber();
            const avg = rec.get('avg_narrators_per_hadith');
            const max = rec.get('max_narrators_per_hadith');
            const avgN = typeof avg === 'number' ? avg : avg?.toNumber?.() ?? 0;
            const maxN = typeof max === 'number' ? max : max?.toNumber?.() ?? 0;
            console.log(`  ${String(src).padEnd(28)} | ${String(trad).padEnd(10)} | ${String(tot).padStart(5)} | ${String(wc).padStart(10)} | ${String(wn).padStart(14)} | ${avgN.toFixed(1).padStart(5)} | ${String(maxN).padStart(5)}`);
        }

        console.log('\n=== 4. Sample 3 imami hadith (check what they look like) ===\n');
        const imamiSample = await session.run(
            `MATCH (h:Hadith)
             WHERE toLower(coalesce(h.tradition,'')) CONTAINS 'imami'
                OR toLower(coalesce(h.tradition,'')) CONTAINS 'shia'
                OR toLower(coalesce(h.tradition,'')) CONTAINS 'jafari'
                OR toLower(coalesce(h.source,'')) CONTAINS 'kafi'
                OR toLower(coalesce(h.source,'')) CONTAINS 'man-la'
                OR toLower(coalesce(h.source,'')) CONTAINS 'tahdhib'
                OR toLower(coalesce(h.source,'')) CONTAINS 'istibsar'
             OPTIONAL MATCH (h)-[:HAS_CHAIN]->(c:Chain)
             OPTIONAL MATCH (c)-[:INCLUDES]->(n:Narrator)
             RETURN h.id AS id, h.source AS source, h.tradition AS tradition,
                    substring(coalesce(h.sanad,''),0,200) AS sanad,
                    count(DISTINCT c) AS chains, count(DISTINCT n) AS narrators
             LIMIT 5`
        );
        for (const rec of imamiSample.records) {
            console.log('  -', rec.get('id'), '/', rec.get('source'), '/', rec.get('tradition'));
            console.log('    chains:', rec.get('chains').toNumber(), 'narrators:', rec.get('narrators').toNumber());
            console.log('    sanad :', rec.get('sanad'));
        }

        console.log('\n=== 5. Chain.source breakdown (what extractor / pipeline made each chain?) ===\n');
        const chainSrc = await session.run(
            `MATCH (c:Chain)
             RETURN coalesce(c.source,'(null)') AS chain_source,
                    coalesce(c.extraction_method,'(null)') AS method,
                    count(c) AS n
             ORDER BY n DESC`
        );
        for (const rec of chainSrc.records) {
            console.log(`  ${String(rec.get('chain_source')).padEnd(30)} | ${String(rec.get('method')).padEnd(30)} | ${rec.get('n').toNumber()}`);
        }

        console.log('\n=== 6. Position gaps & duplicates in :INCLUDES edges ===\n');
        const posIntegrity = await session.run(
            `MATCH (h:Hadith)-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator)
             WITH c, collect(i.position) AS positions, count(i) AS edge_count, count(DISTINCT n) AS distinct_n
             WITH c, positions, edge_count, distinct_n,
                  [p IN positions WHERE p IS NULL] AS null_pos,
                  size(positions) - size(apoc.coll.toSet(positions)) AS dup_positions
             WHERE size(null_pos) > 0 OR dup_positions > 0 OR edge_count <> distinct_n
             RETURN count(c) AS bad_chains,
                    sum(size(null_pos)) AS total_null_positions,
                    sum(dup_positions) AS total_duplicate_positions,
                    sum(CASE WHEN edge_count <> distinct_n THEN 1 ELSE 0 END) AS chains_with_dup_narrators`
        );
        if (posIntegrity.records.length > 0) {
            const r = posIntegrity.records[0];
            console.log('  bad chains              :', r.get('bad_chains').toNumber());
            console.log('  total null positions    :', r.get('total_null_positions')?.toNumber?.() ?? 0);
            console.log('  total dup positions     :', r.get('total_duplicate_positions')?.toNumber?.() ?? 0);
            console.log('  chains w/ dup narrators :', r.get('chains_with_dup_narrators')?.toNumber?.() ?? 0);
        }
    } finally {
        await session.close();
        await driver.close();
    }
}

main().catch(e => { console.error(e); process.exit(1); });
