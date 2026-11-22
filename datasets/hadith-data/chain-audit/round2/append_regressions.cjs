// Appends hadith-level rows: OpenITI reports that had a chain before the fix, open with a written chain, and have none now.
const fs=require('fs');const d=JSON.parse(fs.readFileSync('d5a_hadiths.json','utf8')).filter(x=>x.lost_in_fix);
const det=JSON.parse(fs.readFileSync('C:/Users/atooz/AppData/Local/Temp/claude/8b9ecadf913d98e6/95b7dde3-527e-49ce-8f56-83c964db48b2/scratchpad/det/iz_det.json','utf8'));
const head=new Map(det.map(x=>[x.hadith_id,(x.hits.find(h=>h.det==='D5a')||{}).head]));
const rows=d.map(x=>JSON.stringify({source:'openiti hadith that lost every chain (projection-v6 -> now)',lane:x.work,chain_id:null,hadith_id:x.hadith_id,kind:'chain_lost_written_chain_present',confidence:'high',evidence:{quote_arabic_start:head.get(x.hadith_id),note:'Arabic opens with a written chain (detector D5a of the ibadi-zaydi lane, rerun on production); chain_status extraction_failed; no live chain; the earlier projection had one',before_file:'development/openiti-fix-2026-11-21/projection-v6'}}));
fs.appendFileSync('regressions.jsonl','\n'+rows.join('\n'));console.log(rows.length);
