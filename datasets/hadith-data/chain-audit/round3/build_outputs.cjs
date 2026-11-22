// Builds sample_check.csv, verdicts.tsv, summary.json from v_main.txt / v_pop.txt / v_reg judgments. No DB access.
const fs=require('fs'),path=require('path');
const d=__dirname;
const ids=require('./sample_ids.json'),pops=require('./pop_ids.json');
const parse=f=>fs.readFileSync(path.join(d,f),'utf8').split('\n').filter(l=>/^\d+\|/.test(l)).map(l=>{const p=l.split('|');return{i:+p[0],verdict:p[1],kind:p[2],note:p.slice(3).join('|')};});
const main=parse('v_main.txt'),pop=parse('v_pop.txt');
function wilson(k,n,z=1.96){if(!n)return[0,0];const p=k/n,den=1+z*z/n,c=p+z*z/(2*n),a=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n));return[Math.max(0,(c-a)/den),Math.min(1,(c+a)/den)];}
const fmt=(k,n)=>{const [lo,hi]=wilson(k,n);return `${k}/${n} = ${(100*k/n).toFixed(1)}% (${(100*lo).toFixed(1)}-${(100*hi).toFixed(1)})`;};
// minor kinds counted in "any" (round2: verb/footnote/honorific/date over-extension, truncated letters, non-isnad prose); Imam-not-stored is a convention gap and is NOT counted
const ANY_MINOR=new Set(['surface_gloss','surface_verb','truncated_letters','name_over_extended','honorific_in_surface','surface_prefix','surface_has_an','non_name_from_source','merged_names_from_source','companion_addressed','alternative_lost','surface_clause','unstored_remainder']);
const reportDefect=new Set([60,111,181]); // sampled chain right, another chain of the same report wrong
const lane=i=>ids[i].lane+(ids[i].lane==='sunni'?(ids[i].hadith_id.startsWith('hadith:k6')?'_k6':'_pc'):'');
const rows=main.map(v=>({...v,...ids[v.i],grp:lane(v.i),strict:v.verdict==='defect',any:v.verdict==='defect'||(v.verdict==='ok_minor'&&ANY_MINOR.has(v.kind)),rep:v.verdict==='defect'||reportDefect.has(v.i)}));
const sel=f=>rows.filter(f);const S={};
const add=(name,f)=>{const r=sel(f);S[name]={n:r.length,strict:r.filter(x=>x.strict).length,any:r.filter(x=>x.any).length,report_level:r.filter(x=>x.rep).length};};
add('sunni_all',r=>r.lane==='sunni');add('sunni_k6',r=>r.grp==='sunni_k6');add('sunni_pc',r=>r.grp==='sunni_pc');
add('imami_all',r=>r.lane==='imami');add('imami_kafi',r=>r.lane==='imami'&&r.coll.endsWith('al-kafi'));add('imami_faqih',r=>r.lane==='imami'&&r.coll.endsWith('faqih'));add('imami_thawab',r=>r.lane==='imami'&&r.coll.endsWith('thawab-al-amal'));add('imami_other',r=>r.lane==='imami'&&!/al-kafi|faqih|thawab-al-amal/.test(r.coll));
add('rabi',r=>r.lane==='rabi');add('zayd',r=>r.lane==='zayd');add('rida',r=>r.lane==='rida');
for(const k of Object.keys(S)){const s=S[k];s.strict_ci=fmt(s.strict,s.n);s.any_ci=fmt(s.any,s.n);s.report_ci=fmt(s.report_level,s.n);}
// by-work Sunni
const byWork={};rows.filter(r=>r.lane==='sunni'||r.lane==='imami').forEach(r=>{const w=r.coll.split(':').pop();byWork[w]=byWork[w]||{n:0,strict:0,any:0};byWork[w].n++;if(r.strict)byWork[w].strict++;if(r.any)byWork[w].any++;});
// kinds
const kinds={};rows.filter(r=>r.strict).forEach(r=>r.kind.split('+').forEach(k=>{const g=r.lane+':'+k;kinds[g]=(kinds[g]||0)+1;}));
// populations
const prow=pop.map(v=>({...v,...pops[v.i],strict:v.verdict==='defect',any:v.verdict==='defect'||(v.verdict==='ok_minor'&&ANY_MINOR.has(v.kind))}));
const P={};prow.forEach(r=>{const k=r.lane;P[k]=P[k]||{n:0,defect:0,minor:0,kinds:{}};P[k].n++;if(r.strict){P[k].defect++;r.kind.split('+').forEach(x=>P[k].kinds[x]=(P[k].kinds[x]||0)+1);}if(r.verdict==='ok_minor')P[k].minor++;});
for(const k of Object.keys(P))P[k].ci=fmt(P[k].defect,P[k].n);
fs.writeFileSync(path.join(d,'summary.json'),JSON.stringify({main:S,byWork,kinds,populations:P},null,1));
// sample_check.csv
const q=s=>'"'+String(s==null?'':s).replace(/"/g,'""')+'"';
const head='lane,work,stratum,chain_id,hadith_id,verdict,kind,judged_by,note,online_source,online_url,online_quote';
const lines=[head];
for(const r of rows){const on=/Noor|Turath|turath/.test(r.note);lines.push([r.lane,r.coll.split(':').pop(),'random',r.chain_id||'',r.hadith_id,r.verdict==='ok_minor'?'ok':r.verdict,r.kind,'read',r.note,on?(/Noor/.test(r.note)?'Noor HadithRejalList':'api.turath.io'):'',/Noor/.test(r.note)?'https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=111651':(/Turath|turath/.test(r.note)?'https://api.turath.io/search?q=<public opening words>':''),''].map(q).join(','));}
for(const r of prow){lines.push([r.lane,'', 'population',r.chain_id||'',r.hadith_id,r.verdict==='ok_minor'?'ok':r.verdict,r.kind,'read',(r.note_pop||'')+' '+r.note,'','',''].map(q).join(','));}
fs.writeFileSync(path.join(d,'sample_check.csv'),'﻿'+lines.join('\n')+'\n');
const tsv=['set\tindex\tlane\thadith_id\tchain_id\tverdict\tkind\tnote'];
rows.forEach(r=>tsv.push(['main',r.i,r.lane,r.hadith_id,r.chain_id||'',r.verdict,r.kind,r.note.replace(/\t/g,' ')].join('\t')));
prow.forEach(r=>tsv.push(['population',r.i,r.lane,r.hadith_id,r.chain_id||'',r.verdict,r.kind,r.note.replace(/\t/g,' ')].join('\t')));
fs.writeFileSync(path.join(d,'verdicts.tsv'),tsv.join('\n')+'\n');
// regressions.jsonl: still-wrong rows from the main and population samples
const reg=[];
rows.filter(r=>r.strict||reportDefect.has(r.i)).forEach(r=>reg.push({source:'random sample (round 3)',lane:r.lane,work:r.coll.split(':').pop(),chain_id:r.chain_id||null,hadith_id:r.hadith_id,kind:r.kind||'report_other_chain',evidence:{note:r.note}}));
prow.filter(r=>r.strict).forEach(r=>reg.push({source:'changed population '+r.lane,lane:r.lane,chain_id:r.chain_id||null,hadith_id:r.hadith_id,kind:r.kind,evidence:{note:r.note}}));
fs.writeFileSync(path.join(d,'_reg_main_pop.jsonl'),reg.map(x=>JSON.stringify(x)).join('\n')+'\n');
console.log(JSON.stringify(S,null,1));console.log(JSON.stringify(P,null,1));console.log(JSON.stringify(kinds));console.log(JSON.stringify(byWork));
