/** Peek at the raw CSV rows for Tirmidhi #1/2/3/9 to see chain_indx. */
import { readUnifiedCsv } from './lib/regen/io';

async function main() {
    const wanted = new Set(['1','2','3','9','10','11']);
    let printed = 0;
    for await (const row of readUnifiedCsv('datasets/hadith-data/all_hadiths_unified.csv')) {
        if (row.source === "Jami' al-Tirmidhi" && wanted.has(String(row.hadith_no))) {
            console.log(`\n--- ${row.source} #${row.hadith_no} (dataset_row_id=${row.dataset_row_id}) ---`);
            console.log('  chain_indx:', JSON.stringify(row.chain_indx));
            console.log('  sanad     :', String(row.sanad ?? '').substring(0, 240));
            console.log('  text_ar   :', String(row.text_ar ?? '').substring(0, 180).replace(/\n/g, ' '));
            printed++;
            if (printed >= 6) break;
        }
    }
    console.log('\n--- also peek Imami row ---');
    let imamiCount = 0;
    for await (const row of readUnifiedCsv('datasets/hadith-data/all_hadiths_unified.csv')) {
        if (row.tradition === 'Imami' && row.source === 'Al-Kāfi' && imamiCount < 3) {
            console.log(`\n[Imami #${row.hadith_no}] chain_indx=${JSON.stringify(row.chain_indx)} sanad="${String(row.sanad).substring(0,120)}" text_en="${String(row.text_en).substring(0,140)}"`);
            imamiCount++;
        }
        if (imamiCount >= 3) break;
    }
}

main().catch(e => { console.error(e); process.exit(1); });
