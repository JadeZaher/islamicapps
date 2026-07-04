/**
 * Part 2: drill deeper.
 *   A. For the Tirmidhi hadith, look at the raw chain_indx / sanad_indx_norm
 *      on the Hadith node and on the Chain node (whatever survived after the
 *      v2 regen) so we know what the join was working from.
 *   B. Confirm the regen script's join key (id/scholar_indx -> Narrator).
 *   C. Check whether the Tirmidhi case has multiple chain_indx values being
 *      merged into one Chain node (the "8 narrators from 3 chains" pattern).
 *   D. For Imami sources w/ near-zero narrators, look at what's stored on the
 *      Chain node — is the sanad text English-only? Is chain_indx empty?
 */
import neo4j from 'neo4j-driver';
import 'dotenv/config';

const TARGET = '626a2cb0-2268-4c79-9ffb-d9f6eaf42ec9';

async function main() {
    const uri = process.env.NEO4J_URL!;
    const fullUri = uri.startsWith('bolt') ? uri : `bolt://${uri}`;
    const driver = neo4j.driver(fullUri, neo4j.auth.basic(process.env.NEO4J_USERNAME!, process.env.NEO4J_PASSWORD!));
    const session = driver.session();
    try {
        console.log('=== A. Full Chain node properties for target hadith ===');
        const rA = await session.run(
            `MATCH (h:Hadith {id:$id})-[:HAS_CHAIN]->(c:Chain)
             RETURN c{.*} AS chain, h{.id,.sanad,.chain_indx,.sanad_indx_norm,.source,.hadith_no} AS hadith`,
            { id: TARGET }
        );
        for (const rec of rA.records) {
            console.log('  HADITH:', JSON.stringify(rec.get('hadith'), null, 2));
            console.log('  CHAIN :', JSON.stringify(rec.get('chain'), null, 2));
        }

        console.log('\n=== B. All Hadiths that share this Chain (suspect: chain reuse) ===');
        const rB = await session.run(
            `MATCH (h:Hadith {id:$id})-[:HAS_CHAIN]->(c:Chain)<-[:HAS_CHAIN]-(h2:Hadith)
             RETURN h2.id AS id, h2.source AS source, h2.hadith_no AS no,
                    substring(coalesce(h2.sanad,''),0,140) AS sanad
             LIMIT 25`,
            { id: TARGET }
        );
        console.log(`  ${rB.records.length} sibling hadith share the same Chain`);
        for (const rec of rB.records) {
            console.log('  -', rec.get('source'), '#', rec.get('no'), '|', rec.get('sanad'));
        }

        console.log('\n=== C. Narrators on Chain, with their scholar_indx ===');
        const rC = await session.run(
            `MATCH (h:Hadith {id:$id})-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator)
             RETURN i.position AS pos,
                    n.scholar_indx AS scholar_indx,
                    n.id AS id,
                    n.name_english AS en,
                    n.name_arabic AS ar
             ORDER BY pos`,
            { id: TARGET }
        );
        for (const rec of rC.records) {
            console.log(`  pos=${rec.get('pos')?.toNumber?.() ?? rec.get('pos')} | scholar_indx=${rec.get('scholar_indx')} | ${rec.get('en')} | ${rec.get('ar')}`);
        }

        console.log('\n=== D. For low-narrator Imami sources, sample the actual Chain ===');
        const rD = await session.run(
            `MATCH (h:Hadith)
             WHERE h.source IN ['Al-Kāfi','Man Lā Yaḥḍuruh al-Faqīh','Nahj al-Balāgha','Musnad al-Imam Zayd ibn Ali']
             WITH h.source AS src, collect(h)[0] AS sample
             MATCH (sample)-[:HAS_CHAIN]->(c:Chain)
             RETURN src,
                    sample.id AS hadith_id,
                    sample.hadith_no AS no,
                    substring(coalesce(sample.sanad,''),0,160) AS sanad,
                    c{.*} AS chain`,
        );
        for (const rec of rD.records) {
            console.log(`\n  --- ${rec.get('src')} (sample ${rec.get('hadith_id')}#${rec.get('no')}) ---`);
            console.log('    sanad:', rec.get('sanad'));
            console.log('    chain:', JSON.stringify(rec.get('chain')));
        }

        console.log('\n=== E. Distinct Hadith-level chain_indx values for the target ===');
        const rE = await session.run(
            `MATCH (h:Hadith {id:$id})
             RETURN h.chain_indx AS chain_indx, h.sanad_indx_norm AS sanad_indx_norm`,
            { id: TARGET }
        );
        console.log('   ', JSON.stringify(rE.records[0]?.toObject(), null, 2));

        console.log('\n=== F. Tirmidhi hadiths whose Chain has > expected narrators ===');
        // Find chains where narrator count != tokens-in-sanad-text heuristic
        const rF = await session.run(
            `MATCH (h:Hadith)-[:HAS_CHAIN]->(c:Chain)-[:INCLUDES]->(n:Narrator)
             WHERE h.source = "Jami' al-Tirmidhi"
             WITH h, c, count(DISTINCT n) AS n_count, h.sanad AS sanad
             WITH h, c, n_count, sanad,
                  size(split(coalesce(sanad,''), ',')) AS comma_segments
             WHERE n_count > comma_segments + 2
             RETURN h.id AS id, h.hadith_no AS no, n_count, comma_segments,
                    substring(sanad,0,200) AS sanad
             LIMIT 10`,
        );
        console.log(`  ${rF.records.length} Tirmidhi hadith have many more narrators than sanad commas suggest`);
        for (const rec of rF.records) {
            console.log(`  #${rec.get('no')}: chain has ${rec.get('n_count').toNumber()} narrators, sanad has ${rec.get('comma_segments').toNumber()} segments`);
            console.log('     sanad:', rec.get('sanad'));
        }

        console.log('\n=== G. How many Chain nodes total / shared / orphan ===');
        const rG = await session.run(
            `MATCH (c:Chain)
             OPTIONAL MATCH (h:Hadith)-[:HAS_CHAIN]->(c)
             WITH c, count(h) AS hcount
             RETURN
                count(c) AS total_chains,
                sum(CASE WHEN hcount = 0 THEN 1 ELSE 0 END) AS orphan_chains,
                sum(CASE WHEN hcount = 1 THEN 1 ELSE 0 END) AS unique_chains,
                sum(CASE WHEN hcount > 1 THEN 1 ELSE 0 END) AS shared_chains,
                max(hcount) AS most_reused`
        );
        const g = rG.records[0];
        console.log('  total chains :', g.get('total_chains').toNumber());
        console.log('  orphan       :', g.get('orphan_chains').toNumber());
        console.log('  unique 1:1   :', g.get('unique_chains').toNumber());
        console.log('  shared >1    :', g.get('shared_chains').toNumber());
        console.log('  most reused  :', g.get('most_reused').toNumber());
    } finally {
        await session.close();
        await driver.close();
    }
}

main().catch(e => { console.error(e); process.exit(1); });
