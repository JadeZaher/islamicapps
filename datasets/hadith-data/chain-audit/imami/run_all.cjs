// Runs every detector over all active Imami chains; writes imami_findings.json (internal, beside the cache) and prints counts.
const fs=require('fs'),path=require('path');
const {load}=require('./lib.cjs');const D=require('./detectors.cjs');const {fold,cat,isImamId,collectionOf}=D;
const L=load();
const CACHE=process.env.IMAMI_CACHE||'C:/Users/atooz/AppData/Local/Temp/claude/8b9ecadf913d98e6/95b7dde3-527e-49ce-8f56-83c964db48b2/scratchpad/imami_cache.json';
const OUT=process.env.FINDINGS||path.join(path.dirname(CACHE),'imami_findings.json');
const F=[];const stats={};
const add=(f)=>F.push(f);
const bump=(a,b)=>{stats[a]??={};stats[a][b]=(stats[a][b]||0)+1;};
const surfaceOf=m=>fold(m.surface_ar);
const imamMention=m=>isImamId(m.narrator_id)||cat(m.surface_ar)==='imam_surface';
const hadithText=new Map();for(const [id,h] of L.hid)hadithText.set(id,fold(h.text_ar||''));

// ---------- D1/D2/D5: order, ta'liq ----------
const shaykhList=[...D.KULAYNI_SHAYKH];
const isShaykh=f=>shaykhList.some(s=>f===s||f.startsWith(s+' '));
const posCounts={};
for(const c of L.chains.values()){if(!c.mentions.length)continue;if(collectionOf(L,c.hadith_id)!=='al-kafi')continue;
  c.mentions.forEach((m,i)=>{const f=surfaceOf(m);const o=(posCounts[f]??={p0:0,mid:0});if(i===0)o.p0++;else o.mid++;});}
for(const c of L.chains.values()){
  const ms=c.mentions;if(!ms.length)continue;const col=collectionOf(L,c.hadith_id);
  bump('chains_by_collection',col);
  const last=ms[ms.length-1],first=ms[0];
  bump('ends_imam',col+'|'+(imamMention(last)?'imam':'other'));
  ms.forEach((m,i)=>{if(i<ms.length-1&&(isImamId(m.narrator_id)||cat(m.surface_ar)==='imam_surface')&&!/^(ابائه|ابيه|جده|احدهما|ابائي)/.test(surfaceOf(m))){const nx=surfaceOf(ms[i+1]);if(!D.IMAM_FINAL_CONT.test(nx)&&!imamMention(ms[i+1])){
     const nsurf=surfaceOf(ms[i+1]);const matnLike=/^(الرجل|رجل|المراة|امراة|الميت|ما |هل |في |ان |لو |اذا )/.test(nsurf)||(nsurf.split(' ').length>=4&&!/ بن /.test(nsurf));add({detector:'D05_imam_nonfinal',kind:matnLike?'not_a_narrator':'branch_seam',mention_id:m.id,chain_id:c.id,hadith_id:c.hadith_id,col,evidence:{rule:'Imam register row at non-final position, next mention is not an Imam, a prophet, or a «عن أبيه عن آبائه» link',values:{position:m.position,length:ms.length,surface:m.surface_ar,next_surface:ms[i+1].surface_ar,narrator_id:m.narrator_id}},proposed_action:matnLike?'mark_suspended':'split_chain_at',confidence:matnLike?'high':'medium'});}}});
  if(ms.length>=2&&isImamId(first.narrator_id)&&!imamMention(ms[1])){add({detector:'D01_imam_first',kind:'order_reversed',mention_id:first.id,chain_id:c.id,hadith_id:c.hadith_id,col,evidence:{rule:'Imam register row at position 0 (nearest the compiler) of a multi-link chain',values:{surface:first.surface_ar,next:ms[1].surface_ar,length:ms.length}},proposed_action:'reorder',confidence:'medium'});}
  const f0=surfaceOf(first);
  if(col==='al-kafi'){
    if(isShaykh(f0))bump('kafi_pos0','shaykh_set');
    else if(D.TALIQ.test(f0))bump('kafi_pos0','taliq_pronoun');
    else bump('kafi_pos0','other');
  }
  if(D.TALIQ.test(f0)){
    add({detector:'D02_taliq_pronoun',kind:'suspended_chain',mention_id:first.id,chain_id:c.id,hadith_id:c.hadith_id,col,evidence:{rule:'chain opens with a back-reference («عنه», «وبهذا الاسناد», «وباسناده») to the previous report, not with a shaykh of the compiler',values:{surface:first.surface_ar,resolved:first.narrator_id||null,length:ms.length}},proposed_action:'mark_suspended',confidence:'high'});
    if(first.narrator_id)bump('taliq_resolved',col);
  }
}
for(const c of L.chains.values()){const ms=c.mentions;if(!ms.length)continue;if(collectionOf(L,c.hadith_id)!=='al-kafi')continue;const first=ms[0];const f0=surfaceOf(first);
  if(isShaykh(f0)||D.TALIQ.test(f0))continue;if(!hadithText.get(c.hadith_id).replace(/^s*d+s*[-ـ]?s*/,'').startsWith(f0))continue;const o=posCounts[f0];const tot=o.p0+o.mid;
  const k=cat(first.surface_ar);if(k!=='name'&&k!=='irsal_marked')continue;
  if(o.mid>=20&&o.p0/tot<0.2){add({detector:'D02b_midchain_start',kind:'suspended_chain',mention_id:first.id,chain_id:c.id,hadith_id:c.hadith_id,col:'al-kafi',evidence:{rule:'opening name is not a shaykh of the compiler and occurs mid-chain in al-Kafi far more often than first (opens mid-isnad: a report continuing an earlier chain)',values:{surface:first.surface_ar,as_first:o.p0,mid_chain:o.mid}},proposed_action:'mark_suspended',confidence:'medium'});}
}
// ---------- mention-level categories ----------
for(const m of L.d.mentions){
  const col=collectionOf(L,m.hadith_id);const c=cat(m.surface_ar);bump('cat|'+c,col);
  const base={mention_id:m.id,chain_id:m.chain_id,hadith_id:m.hadith_id,col};
  const mc=L.chains.get(m.chain_id).mentions;
  switch(c){
   case 'irsal_marked':
     add({...base,detector:'D03b_irsal_marked_surface',kind:'anonymous_gap',evidence:{rule:'surface carries an irsal/rafʿ marker (رفعه, عمن ذكره, ...): the named narrator did not hear from the next mention directly',values:{surface:m.surface_ar,resolved:m.narrator_id||null,position:m.position,length:mc.length,next_surface:(mc[m.position+1]||{}).surface_ar||null,next_resolved:(mc[m.position+1]||{}).narrator_id||null}},proposed_action:'no_pair_across',confidence:'high'});break;
   case 'collective_or_anonymous':
     if(m.narrator_id)add({...base,detector:'D03a_collective_resolved',kind:'misidentified',evidence:{rule:'collective or anonymous surface (عدة من أصحابنا, رجل, غيره, ...) carries a person identity',values:{surface:m.surface_ar,narrator_id:m.narrator_id,basis:m.extraction_method}},proposed_action:'demote_identity',confidence:'high'});break;
   case 'verb_prefixed':case 'clause':
     if(c==='clause'&&(fold(m.surface_ar).split(' ').filter(t=>t==='بن').length>=3))break;
     add({...base,detector:'D04_not_a_narrator_'+c,kind:'not_a_narrator',evidence:{rule:c==='verb_prefixed'?'surface opens with a report verb or a quotation (و روي, قال, وسئل الصادق): a report formula or an Imam quotation, not a narrator name':'surface is a clause of the text (matn or a compiler formula), not a name',values:{surface:m.surface_ar,resolved:m.narrator_id||null,position:m.position,length:mc.length}},proposed_action:m.narrator_id?'demote_identity':'mark_suspended',confidence:'high'});break;
   case 'footnote_digit':
     add({...base,detector:'D04c_footnote_in_surface',kind:'not_a_narrator',evidence:{rule:'surface contains an editorial footnote marker or a footnote text',values:{surface:m.surface_ar,resolved:m.narrator_id||null}},proposed_action:'other',confidence:'medium'});break;
   case 'fused_cotransmitter':
     add({...base,detector:'D06b_fused_cotransmitters',kind:'co_transmitter',evidence:{rule:'one mention holds two or more narrators joined by «و» (parallel co-transmitters)',values:{surface:m.surface_ar,resolved:m.narrator_id||null,position:m.position}},proposed_action:'split_chain_at',confidence:'high'});break;
  }
  if(c==='relational'&&m.narrator_id)bump('relational_resolved',col);
  if(c==='taliq_pronoun'&&m.narrator_id)bump('taliq_resolved_any_pos',col);
}
// ---------- D6a: successive mentions joined by «و» in the report text ----------
const WAW=/^\s*(\([^)]*\)\s*)*[،,\-\u2013]?\s*و\s*(\([^)]*\)\s*)*$/;
const AN=/^\s*(\([^)]*\)\s*)*[،,]?\s*(قال|وقال)?\s*(حدثنا|حدثني|اخبرنا|اخبرني)?\s*(عن|من)?\s*$/;
for(const c of L.chains.values()){const ms=c.mentions;if(ms.length<2)continue;const col=collectionOf(L,c.hadith_id);const txt=hadithText.get(c.hadith_id);
  let cursor=0;let prevEnd=null,prev=null;let aligned=true;
  for(const m of ms){const f=surfaceOf(m);const idx=f?txt.indexOf(f,cursor):-1;
    if(idx<0||idx>cursor+4000){aligned=false;bump('align_fail',col);break;}
    if(prev){const between=txt.slice(prevEnd,idx);
      const cls=WAW.test(between)?'waw':AN.test(between)?'an':'other';
      bump('connector|'+col,cls);
      if(cls==='waw'){add({detector:'D06a_waw_between_adjacent_mentions',kind:'co_transmitter',mention_id:m.id,chain_id:c.id,hadith_id:c.hadith_id,col,evidence:{rule:'the report text joins two successive mentions with «و» only: they are co-transmitters at one level, not teacher then student',values:{earlier_mention_id:prev.id,earlier:prev.surface_ar,later:m.surface_ar,text_between:between.trim(),position:m.position}},proposed_action:'split_chain_at',confidence:'high'});}
    }
    prev=m;prevEnd=idx+f.length;cursor=prevEnd;}
  if(aligned)bump('aligned_chains',col);
}
// ---------- D07 repeats ----------
for(const c of L.chains.values()){const seen=new Map();for(const m of c.mentions){const f=surfaceOf(m);const key=m.narrator_id&&!isImamId(m.narrator_id)?m.narrator_id:(f.split(' ').length>=3&&cat(m.surface_ar)==='name'?'s:'+f:null);if(!key)continue;
  if(seen.has(key)){add({detector:'D07_repeat_in_chain',kind:'branch_seam',mention_id:m.id,chain_id:c.id,hadith_id:c.hadith_id,col:collectionOf(L,c.hadith_id),evidence:{rule:'same narrator (id or identical full-name surface) occurs twice in one chain: two isnads of one report were concatenated, so the last name of the first isnad is stored as the teacher of the first name of the second',values:{surface:m.surface_ar,first_position:seen.get(key),second_position:m.position,key,earlier_mention_id:null}},proposed_action:'split_chain_at',confidence:'medium'});}else seen.set(key,m.position);}}
// ---------- D08 both directions ----------
const pairs=new Map();
for(const c of L.chains.values()){const ms=c.mentions;for(let i=0;i+1<ms.length;i++){const a=ms[i],b=ms[i+1];if(!a.narrator_id||!b.narrator_id||a.narrator_id===b.narrator_id)continue;if(isImamId(a.narrator_id))continue;
  const k=a.narrator_id+'|'+b.narrator_id;const o=pairs.get(k)||{n:0,mentions:[]};o.n++;if(o.mentions.length<6)o.mentions.push([a.id,b.id,c.id,c.hadith_id]);pairs.set(k,o);}}
let bothDir=0;
for(const [k,o] of pairs){const [s,t]=k.split('|');if(isImamId(t))continue;const rev=pairs.get(t+'|'+s);if(rev&&s<t){bothDir++;
  for(const [pair,tag] of [[o,'forward'],[rev,'reverse']].filter(([p])=>p.n<=Math.min(o.n,rev.n)&&Math.min(o.n,rev.n)/(o.n+rev.n)<0.5)){for(const mm of pair.mentions.slice(0,6)){add({detector:'D08_pair_both_directions',kind:'order_reversed',mention_id:mm[1],chain_id:mm[2],hadith_id:mm[3],col:collectionOf(L,mm[3]),evidence:{rule:'the same two identities occur as teacher->student in both directions across Imami chains',values:{student:s,teacher:t,direction:tag,forward_count:o.n,reverse_count:rev.n}},proposed_action:'other',confidence:'medium'});}}}}
stats.pairs_both_directions=bothDir;stats.pairs_total=pairs.size;
// ---------- D09 wrong Imam ----------
const beforeImam=new Map();
for(const c of L.chains.values()){const ms=c.mentions;const l=ms[ms.length-1];if(ms.length<2||!l||!isImamId(l.narrator_id))continue;const s=ms[ms.length-2];if(!s.narrator_id||isImamId(s.narrator_id))continue;const o=beforeImam.get(s.narrator_id)||{};o[l.narrator_id]=(o[l.narrator_id]||0)+1;beforeImam.set(s.narrator_id,o);}
for(const c of L.chains.values()){const ms=c.mentions;const l=ms[ms.length-1];if(ms.length<2||!l||!isImamId(l.narrator_id))continue;const s=ms[ms.length-2];if(!s.narrator_id)continue;const o=beforeImam.get(s.narrator_id);if(!o)continue;const tot=Object.values(o).reduce((a,b)=>a+b,0);if(tot<15)continue;
  const mine=o[l.narrator_id]||0;const [topId,topN]=Object.entries(o).sort((a,b)=>b[1]-a[1])[0];
  if(topId!==l.narrator_id&&mine/tot<0.05&&topN/tot>=0.85&&l.extraction_method==='imam_kunya_convention'){add({detector:'D09_wrong_imam_for_students',kind:'misidentified',mention_id:l.id,chain_id:c.id,hadith_id:c.hadith_id,col:collectionOf(L,c.hadith_id),evidence:{rule:'Imam identity differs from the Imam this student transmits from in nearly all other chains (>=85%, this Imam <5%, >=15 chains)',values:{surface:l.surface_ar,assigned:l.narrator_id,student:s.narrator_id,student_surface:s.surface_ar,student_total:tot,student_with_assigned:mine,dominant:topId,dominant_n:topN}},proposed_action:'demote_identity',confidence:'medium'});}}
// ---------- D10 relational resolved consistency ----------
const relMap=new Map();for(const c of L.chains.values()){const ms=c.mentions;for(let i=1;i<ms.length;i++){const m=ms[i];if(!/^(و ?)?(ابيه|جده|عمه|اخيه)$/.test(surfaceOf(m))||!m.narrator_id)continue;const prev=ms[i-1];if(!prev.narrator_id)continue;const k=prev.narrator_id+'|'+surfaceOf(m);const o=relMap.get(k)||{};(o[m.narrator_id]??=[]).push([m,c]);relMap.set(k,o);}}
for(const [k,o] of relMap){const ids=Object.keys(o);if(ids.length<2)continue;const sorted=ids.sort((a,b)=>o[b].length-o[a].length);const dom=sorted[0];const domN=o[dom].length;const tot=ids.reduce((a,i)=>a+o[i].length,0);
  for(const id of sorted.slice(1)){if(o[id].length/tot>0.2)continue;for(const [m,c] of o[id]){add({detector:'D10_relational_inconsistent',kind:'misidentified',mention_id:m.id,chain_id:c.id,hadith_id:c.hadith_id,col:collectionOf(L,c.hadith_id),evidence:{rule:'the same «student + أبيه» (or جده) resolves to different people; this one disagrees with the majority',values:{student_and_surface:k,assigned:id,assigned_n:o[id].length,majority:dom,majority_n:domN}},proposed_action:'demote_identity',confidence:'medium'});}}}
// ---------- D11 generation inversion from the data ----------
const depth=new Map();for(const c of L.chains.values()){const ms=c.mentions;if(ms.length<3)continue;let li=-1;for(let i=ms.length-1;i>=0;i--){if(isImamId(ms[i].narrator_id)){li=i;break;}}if(li<0)continue;
  ms.forEach((m,i)=>{if(i<li&&m.narrator_id&&!isImamId(m.narrator_id)){const o=depth.get(m.narrator_id)||{s:0,n:0};o.s+=li-i;o.n++;depth.set(m.narrator_id,o);}});}
const meanDepth=id=>{const o=depth.get(id);return o&&o.n>=20?o.s/o.n:null;};
stats.depth_narrators=[...depth.values()].filter(o=>o.n>=20).length;
for(const c of L.chains.values()){const ms=c.mentions;for(let i=0;i+1<ms.length;i++){const a=ms[i],b=ms[i+1];if(!a.narrator_id||!b.narrator_id||isImamId(a.narrator_id)||isImamId(b.narrator_id))continue;
  const da=meanDepth(a.narrator_id),db=meanDepth(b.narrator_id);if(da==null||db==null)continue;
  if(db-da>=2.5){add({detector:'D11_generation_inversion',kind:'other',mention_id:b.id,chain_id:c.id,hadith_id:c.hadith_id,col:collectionOf(L,c.hadith_id),evidence:{rule:'teacher sits on average >=2.5 links farther from the Imam than his student across all chains with a resolved Imam (>=20 occurrences each): the data order is inverted for this pair; flag only',values:{student:a.narrator_id,teacher:b.narrator_id,student_mean_distance:+da.toFixed(2),teacher_mean_distance:+db.toFixed(2)}},proposed_action:'other',confidence:'medium'});}}}

// ---------- D12 numerals/dates stored as narrators ----------
const NUM=new Set('واحد اثنين اثنتين ثلاث ثلاثة اربع اربعة خمس خمسة ست ستة سبع سبعة ثمان ثماني ثمانية تسع تسعة عشر عشرة عشرين ثلاثين اربعين خمسين ستين سبعين ثمانين تسعين مائة ماية مائتين مئتين ثلاثمائة اربعمائة خمسمائة الف سنة شهر رمضان محرم صفر ربيع الاول الاخر جمادي رجب شعبان شوال القعدة الحجة في'.split(' '));
for(const m of L.d.mentions){const t=surfaceOf(m).replace(/(^| )و(?=\S)/g,'$1').split(' ').filter(Boolean);if(t.length&&t.length<=5&&t.every(x=>NUM.has(x))&&t.some(x=>!['سنة','شهر','في','رمضان'].includes(x))){
  add({detector:'D12_numeral_as_narrator',kind:'not_a_narrator',mention_id:m.id,chain_id:m.chain_id,hadith_id:m.hadith_id,col:collectionOf(L,m.hadith_id),evidence:{rule:'surface is a number or date word (a year split on «و» in the isnad text), not a narrator',values:{surface:m.surface_ar,resolved:m.narrator_id||null}},proposed_action:m.narrator_id?'demote_identity':'mark_suspended',confidence:'high'});}}
// ---------- D06c Cartesian expansion across «جميعا» groups ----------
for(const c of L.chains.values()){const ms=c.mentions;if(ms.length<2)continue;const txt=hadithText.get(c.hadith_id);const J=txt.slice(0,900).indexOf('جميعا');if(J<0)continue;
  const col=collectionOf(L,c.hadith_id);let cursor=0;const pos=[];let ok=true;
  for(const m of ms){const f=surfaceOf(m);const idx=f?txt.indexOf(f,cursor):-1;if(idx<0){ok=false;break;}pos.push([idx,idx+f.length]);cursor=idx+f.length;}
  if(!ok){bump('d06c_align_fail',col);continue;}
  const kk=pos.findIndex(p=>p[0]>=J);if(kk<0||pos[kk][0]-J>16){bump('d06c_jamian_outside_chain',col);continue;}
  bump('d06c_chains_with_jamian',col);
  for(let i=0;i+1<ms.length;i++){if(pos[i+1][0]>=J)break;const G=txt.slice(pos[i][1],pos[i+1][0]).replace(/[،,.]/g,' ').replace(/\s+/g,' ').trim().replace(/^(عن|من)\s+/,'');if(/(حدثنا|حدثني|اخبرنا|اخبرني|قال)/.test(G+' '+txt.slice(pos[i+1][1],J)))continue;
    if(!G||/^(عن|من)$/.test(G))continue;const next=txt.slice(pos[i+1][1],J);const ownTeacher=/(^|\s)عن(\s|$)/.test(next);const innerLink=/(^|\s)عن(\s|$)/.test(G);
    if(innerLink||ownTeacher){add({detector:'D06c_cartesian_across_jamian_groups',kind:'branch_seam',mention_id:ms[i+1].id,chain_id:c.id,hadith_id:c.hadith_id,col,evidence:{rule:'the text groups «A عن B و C عن D جميعا عن E»: each group is its own sub-chain that meets at E. The stored chain links a name of one group to the next group',values:{earlier_mention_id:ms[i].id,earlier:ms[i].surface_ar,later:ms[i+1].surface_ar,text_between:G,position:ms[i+1].position}},proposed_action:'split_chain_at',confidence:'high'});}}}
// ---------- D13 source-citation prefix inside a surface (Mujam al-Ahadith al-Mutabara) ----------
for(const m of L.d.mentions){if(/^[0-9]+\/[0-9]+ /.test(surfaceOf(m))){add({detector:'D13_source_label_in_surface',kind:'other',mention_id:m.id,chain_id:m.chain_id,hadith_id:m.hadith_id,col:collectionOf(L,m.hadith_id),evidence:{rule:'surface starts with a volume/page citation and a book label (e.g. «3/45 معاني الاخبار») of the anthology, not part of the narrator name',values:{surface:m.surface_ar,resolved:m.narrator_id||null}},proposed_action:m.narrator_id?'demote_identity':'other',confidence:'high'});}}
fs.writeFileSync(OUT,JSON.stringify({F,stats}));
console.log(JSON.stringify(stats));
const by={};for(const f of F){const k=f.detector;(by[k]??={n:0,h:new Set(),cols:{}});by[k].n++;by[k].h.add(f.hadith_id);by[k].cols[f.col]=(by[k].cols[f.col]||0)+1;}
for(const k in by)console.log(k,by[k].n,'hadiths',by[k].h.size,Object.entries(by[k].cols).sort((a,b)=>b[1]-a[1]).slice(0,6).map(x=>x.join(':')).join(' '));
