// list hadith ids of Imami chains judged defect (sample + pops) for the before/after comparison
const fs=require('fs');const ids=new Set();
const ch=new Map();for(const f of ['sample_ids.json','pop_imami_jamian.json','pop_imami_susp.json','pop_imami_anon.json','pop_imami_filled.json'])for(const s of JSON.parse(fs.readFileSync(f,'utf8')))ch.set(s.chain_id,s.hadith_id);
for(const f of ['verdicts.tsv','pop_verdicts.tsv'])for(const l of fs.readFileSync(f,'utf8').split('\n').slice(1)){const c=l.split('\t');if(c[2]==='defect'&&c[1].startsWith('chain:thaqalayn:'))ids.add(ch.get(c[1])||'');}
ids.delete('');fs.writeFileSync('imami_defect_hadiths.txt',[...ids].join(' '));console.log(ids.size);
