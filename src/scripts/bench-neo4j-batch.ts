/**
 * Probe a realistic-shape Hadith MERGE batch to see if the timeout is in
 * loadHadithsBatch (large text fields), loadChainsBatch, or somewhere else.
 */
import 'dotenv/config';
import { runWrite } from '@/lib/db/neo4j';

async function main() {
    console.log('=== Realistic batch probe ===\n');

    // Stage 1: 100 hadith MERGE with full-size text fields
    const fakeHadiths = Array.from({ length: 100 }, (_, i) => ({
        dataset_row_id: 999000 + i,
        source: 'Probe',
        tradition: 'Sunni',
        hadith_no: String(i),
        chapter: 'probe chapter',
        chapter_no: '1',
        text_ar: 'حدثنا قتيبة بن سعيد، حدثنا أبو عوانة، عن سماك بن حرب '.repeat(20),
        text_en: 'Narrated lorem ipsum dolor sit amet '.repeat(40),
        matn_ar: 'النبي صلى الله عليه وسلم قال '.repeat(30),
        matn_en: 'lorem ipsum '.repeat(50),
        sanad: 'qutayba, abu awana, smak',
        pipeline_key: 'probe-pk-' + i,
    }));
    const t1 = Date.now();
    try {
        await runWrite(
            `UNWIND $rows AS r
             MERGE (h:Hadith { dataset_row_id: r.dataset_row_id })
             ON CREATE SET h.id = randomUUID(), h.source = r.source, h.tradition = r.tradition,
                           h.hadith_no = r.hadith_no, h.text_ar = r.text_ar, h.text_en = r.text_en,
                           h.matn_ar = r.matn_ar, h.matn_en = r.matn_en, h.sanad = r.sanad,
                           h.pipeline_key = r.pipeline_key, h.created_at = datetime()
             ON MATCH SET h.text_ar = r.text_ar, h.text_en = r.text_en,
                          h.matn_ar = r.matn_ar, h.matn_en = r.matn_en, h.sanad = r.sanad,
                          h.updated_at = datetime()`,
            { rows: fakeHadiths },
        );
        console.log(`Stage 1: UNWIND 100 Hadith MERGE (with text) — ${Date.now() - t1} ms`);
    } catch (err) {
        console.log(`Stage 1 FAILED in ${Date.now() - t1} ms: ${(err as Error).message?.slice(0, 200)}`);
    }

    // Stage 2: 100 Chain MERGE
    const fakeChains = Array.from({ length: 100 }, (_, i) => ({
        chain_key: 'probe-chain-' + i,
        chain_id: 'probe-chain-uuid-' + i,
        chain_index: 0,
        confidence: 1,
        method: 'probe',
        dataset_row_id: 999000 + i,
    }));
    const t2 = Date.now();
    try {
        await runWrite(
            `UNWIND $chains AS c
             MERGE (ch:Chain { pipeline_key: c.chain_key })
             ON CREATE SET ch.id = c.chain_id, ch.created_at = datetime(),
                           ch.chain_index = c.chain_index, ch.confidence = c.confidence,
                           ch.extraction_method = c.method
             ON MATCH SET ch.updated_at = datetime()`,
            { chains: fakeChains },
        );
        console.log(`Stage 2: UNWIND 100 Chain MERGE — ${Date.now() - t2} ms`);
    } catch (err) {
        console.log(`Stage 2 FAILED in ${Date.now() - t2} ms: ${(err as Error).message?.slice(0, 200)}`);
    }

    // Stage 3: 100 HAS_CHAIN MERGE
    const t3 = Date.now();
    try {
        await runWrite(
            `UNWIND $chains AS c
             MATCH (h:Hadith { dataset_row_id: c.dataset_row_id })
             MATCH (ch:Chain { pipeline_key: c.chain_key })
             MERGE (h)-[r:HAS_CHAIN]->(ch)
             ON CREATE SET r.confidence = 1.0, r.extraction_method = c.method`,
            { chains: fakeChains },
        );
        console.log(`Stage 3: UNWIND 100 HAS_CHAIN MERGE — ${Date.now() - t3} ms`);
    } catch (err) {
        console.log(`Stage 3 FAILED in ${Date.now() - t3} ms: ${(err as Error).message?.slice(0, 200)}`);
    }

    // Stage 4: 500 INCLUDES CREATE (simulating fresh-mode loader)
    const fakeIncludes: Array<{
        chain_key: string;
        scholar_indx: number;
        position: number;
        confidence: number;
        method: string;
    }> = [];
    for (let i = 0; i < 100; i++) {
        for (let p = 0; p < 5; p++) {
            fakeIncludes.push({
                chain_key: 'probe-chain-' + i,
                scholar_indx: 5 + p,
                position: p,
                confidence: 1,
                method: 'probe',
            });
        }
    }
    const t4 = Date.now();
    try {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (ch:Chain { pipeline_key: e.chain_key })
             MATCH (n:Narrator { scholar_indx: e.scholar_indx })
             CREATE (ch)-[:INCLUDES { position: e.position, confidence: e.confidence,
                                      extraction_method: e.method, source: 'probe' }]->(n)`,
            { edges: fakeIncludes },
        );
        console.log(`Stage 4: UNWIND 500 INCLUDES CREATE — ${Date.now() - t4} ms`);
    } catch (err) {
        console.log(`Stage 4 FAILED in ${Date.now() - t4} ms: ${(err as Error).message?.slice(0, 200)}`);
    }

    // Stage 5: try K=50 buffer (250 INCLUDES) to see if throughput is per-edge or per-batch
    const halfIncludes = fakeIncludes.slice(0, 250);
    const t5 = Date.now();
    try {
        await runWrite(
            `UNWIND $edges AS e
             MATCH (ch:Chain { pipeline_key: e.chain_key })
             MATCH (n:Narrator { scholar_indx: e.scholar_indx })
             CREATE (ch)-[:INCLUDES { position: e.position, confidence: e.confidence,
                                      extraction_method: e.method, source: 'probe2' }]->(n)`,
            { edges: halfIncludes },
        );
        console.log(`Stage 5: UNWIND 250 INCLUDES CREATE — ${Date.now() - t5} ms (per-edge: ${((Date.now() - t5)/250).toFixed(1)} ms)`);
    } catch {
        console.log(`Stage 5 FAILED in ${Date.now() - t5} ms`);
    }

    // Cleanup
    console.log('\nCleaning up probe nodes...');
    await runWrite(
        `MATCH (h:Hadith) WHERE h.dataset_row_id >= 999000 AND h.dataset_row_id < 1000000 DETACH DELETE h`,
    );
    await runWrite(
        `MATCH (c:Chain) WHERE c.pipeline_key STARTS WITH 'probe-chain-' DETACH DELETE c`,
    );
    console.log('Cleanup done.');

    process.exit(0);
}

main().catch((e) => {
    console.error('FATAL:', e);
    process.exit(1);
});
