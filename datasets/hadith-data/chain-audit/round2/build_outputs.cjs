// Builds sample_check.csv, regressions.jsonl and summary.json from verdicts.tsv, pop_verdicts.tsv, thaq_compare.json, regress_classified.json, lost_names.json.
const fs=require('fs');
const wilson=(k,n)=>{if(!n)return[0,0];const z=1.96,p=k/n,d=1+z*z/n,c=p+z*z/(2*n),a=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n));return[(c-a)/d,(c+a)/d];};
const pct=x=>(100*Math.max(0,x)).toFixed(1)+'%';
const fmt=(k,n)=>{const [lo,hi]=wilson(k,n);return `${k}/${n} = ${pct(k/n)} (${pct(lo)}-${pct(hi)})`;};
const STRICT=new Set(['missing_link','branch_seam','wrong_split','false_seam','merged_names','concatenated_isnads','not_a_narrator','truncated_route','inherited_chain_wrong','duplicated_narrator']);
const rd=f=>fs.readFileSync(f,'utf8').split('\n').slice(1).filter(Boolean).map(l=>{const c=l.split('\t');return{lane:c[0],chain_id:c[1],verdict:c[2],kind:c[3]||'',note:c[4]||''};});
const V=rd('verdicts.tsv'),P=rd('pop_verdicts.tsv');
const ids=new Map();for(const f of fs.readdirSync('.').filter(x=>/^(sample_ids|pop_[a-z_]+)\.json$/.test(x)))for(const s of JSON.parse(fs.readFileSync(f,'utf8')))ids.set(s.chain_id,s);
const th=JSON.parse(fs.readFileSync('thaq_compare.json','utf8'));
const stat={};
const groups={sunni_k6:V.filter(v=>v.lane==='sunni'&&v.chain_id.includes(':k6:')),sunni_pure_canon:V.filter(v=>v.lane==='sunni'&&v.chain_id.includes('pure-canon')),sunni_all:V.filter(v=>v.lane==='sunni'),imami:V.filter(v=>v.lane==='imami'),rabi:V.filter(v=>v.lane==='rabi'),zayd:V.filter(v=>v.lane==='zayd'),rida:V.filter(v=>v.lane==='rida')};
for(const [g,rows] of Object.entries(groups)){const j=rows.filter(r=>r.verdict!=='unverifiable');const d=j.filter(r=>r.verdict==='defect');const s=d.filter(r=>STRICT.has(r.kind));
 const kinds={};d.forEach(r=>kinds[r.kind]=(kinds[r.kind]||0)+1);stat[g]={read:rows.length,judged:j.length,unverifiable:rows.length-j.length,defects:d.length,strict:s.length,any_defect:fmt(d.length,j.length),strict_defect:fmt(s.length,j.length),kinds};}
const pops={};for(const r of P){(pops[r.lane]=pops[r.lane]||[]).push(r);}
const popstat={};for(const [k,rows] of Object.entries(pops)){const j=rows.filter(r=>r.verdict!=='unverifiable'),d=j.filter(r=>r.verdict==='defect');const kinds={};d.forEach(r=>kinds[r.kind]=(kinds[r.kind]||0)+1);popstat[k]={n:rows.length,judged:j.length,defects:d.length,rate:fmt(d.length,j.length),kinds};}
const q=s=>'"'+String(s==null?'':s).replace(/"/g,'""')+'"';
const online={
 'chain:k6:4489:0001':['api.turath.io search','https://api.turath.io/search (query: opening words of the report; saved in fetched/turath_3e4ca6bf21.json)','٤٦٧٤ - حدثنا مؤمل هو ابن هشام، حدثنا إسماعيل بن إبراهيم، حدثنا عوف، حدثنا أبو رجاء، حدثنا سمرة بن جندب'],
 'chain:k6:7805:0000':['api.turath.io search','https://api.turath.io/search (query: opening words; saved in fetched/turath_109223d629.json)','[١٦٥] حدثني محمد بن المثنى، وابن بشار، قال ابن المثنى: حدثنا محمد بن جعفر، حدثنا شعبة عن قتادة قال: سمعت أبا العالية'],
 'chain:k6:4794:0000':['api.turath.io search','https://api.turath.io/search (query: opening words; saved in fetched/turath_541c231731.json)','٤٩٧٥ - حدثنا إسحاق بن منصور قال: وحدثنا عبد الرزاق: أخبرنا معمر، عن همام، عن أبي هريرة'],
 'chain:thaqalayn:1adbb3bc592355214cdb0be0:0001':['Noor HadithRejalList','https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=118532','محمد بن يعقوب الكليني > علي بن إبراهيم > أبيه > ابن محبوب ... || الكليني > عدة من أصحابنا > سهل بن زياد > ابن محبوب ...']};
const hdr=['lane','work','stratum','chain_id','hadith_id','verdict','kind','judged_by','note','online_source','online_url','online_quote'];
const lines=[hdr.join(',')];const seen=new Set();
const add=(r,stratum,by)=>{const s=ids.get(r.chain_id)||{};const w=(s.coll||'').replace('collection:','')||(s.pop||'');let o=(online[r.chain_id]||[]).slice();const t=th[r.chain_id];
 if(!o.length&&t&&t.status!=='no_english'&&r.lane==='imami'){o=['thaqalayn-api.net English sanad',t.url||'',t.status+': '+(t.en||'').slice(0,140)];}
 lines.push([r.lane,w,stratum,r.chain_id,s.hadith_id||'',r.verdict,r.kind,by,r.note,o[0]||'',o[1]||'',o[2]||''].map(q).join(','));seen.add(r.chain_id);};
for(const r of V)add(r,'random','read');
const sample=JSON.parse(fs.readFileSync('sample_ids.json','utf8'));
for(const s of sample)if(!seen.has(s.chain_id)){add({lane:s.lane,chain_id:s.chain_id,verdict:'ok_unread',kind:'',note:'pre-judge alignment found no gap, tail or unmatched surface; not read by eye'},'random','auto');}
for(const r of P)add(r,'population:'+r.lane,'read');
fs.writeFileSync('sample_check.csv','﻿'+lines.join('\n'));
const R=[];
const cl=JSON.parse(fs.readFileSync('regress_classified.json','utf8'));
const KIND=new Set(['missing_link','wrong_split','false_seam','truncated_route']);
for(const c of cl.filter(c=>c.change==='worse_lost_names'&&KIND.has(c.kind))){const row={source:'judged sample/population chain whose names were lost',lane:c.lane,chain_id:c.chain_id,hadith_id:c.hadith_id,kind:c.kind,confidence:'medium',evidence:{note:c.note,before:c.before_best,after:c.after,before_file:c.side==='sunni'?'development/chain-builder-r2-2026-11-22/projection-m2c':'development/chain-builder-r2-2026-11-22/projection-m1'}};
 if(online[c.chain_id]){row.evidence.url=online[c.chain_id][1];row.evidence.quote=online[c.chain_id][2];row.confidence='high';}R.push(row);}
const lost=JSON.parse(fs.readFileSync('lost_names.json','utf8'));
for(const l of lost)R.push({source:'sunni trim, whole-population scan',lane:'sunni',chain_id:l.chain,hadith_id:l.h,kind:'name_lost_by_trim',confidence:'medium',evidence:{quote_before:l.old,after:l.new,lost_words:l.lost,before_file:'development/chain-builder-r2-2026-11-22/projection-m2c',note:'the old surface held a named narrator after a report verb; the new surface keeps only the first name and no mention of the hadith carries the second'}});
for(const h of JSON.parse(fs.readFileSync('hadiths_lost_all_chains.json','utf8')).filter(h=>/pc_20809|k6:21409/.test(h)))R.push({source:'sunni hadith that lost every chain',lane:'sunni',chain_id:null,hadith_id:h,kind:'chain_lost',confidence:'high',evidence:{note:h.includes('pc_20809')?'source sanad field «قرأت على أبي قرة الزبيدي موسى ابن طارق, موسى يعني ابن عقبة, أبي صالح السمان, أحدهما, أبي هريرة» had a chain before; none now':'source sanad field «يعقوب بن إبراهيم الدورقي, هشيم, يعلى بن عطاء, عمارة بن حديد, صخر الغامدي» had a chain before; none now'}});
fs.writeFileSync('regressions.jsonl',R.map(r=>JSON.stringify(r)).join('\n'));
const sm={groups:stat,populations:popstat,regression_rows:R.length,regression_by_kind:R.reduce((a,r)=>(a[r.kind]=(a[r.kind]||0)+1,a),{}),trim_lost_rows:lost.length,trim_lost_hadiths:new Set(lost.map(l=>l.h)).size,classified:cl.reduce((a,c)=>{const k=c.lane.split('_')[0]+':'+c.change;a[k]=(a[k]||0)+1;return a;},{})};
fs.writeFileSync('summary.json',JSON.stringify(sm,null,1));
console.log(JSON.stringify(sm,null,1));
