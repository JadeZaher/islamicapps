// Round 4: production counts (live, CHECKED chains only) for each missed pattern. Read-only. Prints JSON; examples are ids.
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:60,idle_timeout:0});
const st=s=>(s||'').replace(/[ً-ٰٟـ]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').replace(/\s+/g,' ');
const K6=new Set(['bukhari','muslim','nasai','tirmidhi','abudawud','ibnmajah']);
const PCW=new Set(['ahmad','darimi','muwatta']);
const IMAMI3=new Set(['al-kafi','man-la-yahduruhu-al-faqih','thawab-al-amal']);
const out={};const ex={};
const add=(k,chain,hadith,extra)=>{out[k]=out[k]||{chains:0,hadiths:new Set()};out[k].chains++;out[k].hadiths.add(hadith);(ex[k]=ex[k]||[]);if(ex[k].length<4&&Math.random()<0.02||ex[k].length<2)ex[k].push({chain,extra});};
const HEAR=/^[\s،,]*(?:قال[\s،,]*)?(?:(?:انه|ان)\s+)?(?:سمعت|سمع|قرات علي|قرات على|انتهيت الي|انتهيت الى|نظر الي|نظر الى|دخلت علي|دخلت على)\s+(?!رسول|النبي|نبي|الله|ابي القاسم)([ء-ي]+(?:\s+[ء-ي]+)?)/;
const VERBMID=/\S\s+و?(?:حدثناه|حدثنيه|اخبرناه|اخبرنيه|حدثنا|اخبرنا|حدثني|اخبرني)(?![ء-ي])/;
const NASAB=/(?:^|\s)(?:بن|ابن|ابو|ابي|ابا|ام|مولي|مولى|بنت|عبد|عدة|بعض|عن|اصحابنا|غير|رجل|رجاله|عمن|الامام|امير|رجال|ال)(?![ء-ي])/;
const SECOND=/و?(?:حدثنيه|حدثناه|اخبرنيه|اخبرناه)\s+[ء-ي ]{3,50}[،,]\s*(?:حدثنا|اخبرنا|حدثني|اخبرني)/;
const JOINED_AN=/(?:السلام|\(ع\)|\sع)\s*\)?\s*و\s?عن\s/;
const RIDA2=/(?:حدثني|حدثتني)\s[^.]{3,70}?قال[:\s]*(?:حدثتني|حدثني|اخبرني)\s/;
(async()=>{
 const cur=sql`select c.id chain_id,h.id hadith_id,h.collection_id coll,left(h.text_ar,1000) t,left(coalesce(h.sanad_ar,''),600) sa,(select array_agg(m.surface_ar order by m.position) from chain_mentions m where m.chain_id=c.id and m.retired_at is null) surfs,(select count(*) from chains c2 where c2.hadith_id=h.id and c2.retired_at is null)::int nch from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and c.structure_status='checked_by_rule'`.cursor(2000);
 let n=0;const total={};
 for await(const rows of cur){
  for(const r of rows){
   n++;const w=r.coll.split(':').pop(),trad=r.coll.split(':')[1];
   total[w]=(total[w]||0)+1;
   const surfs=(r.surfs||[]).map(st);if(!surfs.length)continue;
   const text=st(r.sa&&trad!=='sunni'?r.sa:r.t);
   const hadithText=st(r.t);
   if(K6.has(w)){
    // A: name lost after a hearing/reading verb following the last stored link
    const last=surfs[surfs.length-1];const idx=text.indexOf(last);
    if(idx>=0){const rem=text.slice(idx+last.length,idx+last.length+80);const m=HEAR.exec(rem);if(m&&!last.includes(m[1].split(' ')[0]))add('A_name_lost_after_hearing_verb_K6',r.chain_id,r.hadith_id,m[0].trim().slice(0,50));}
    // B: second isnad written after the matn, one chain stored
    if(r.nch===1){const p=hadithText.search(SECOND);if(p>150)add('B_second_isnad_after_matn_one_chain_K6',r.chain_id,r.hadith_id,hadithText.slice(p,p+50));}
    // C: verb inside a stored surface (not leading)
    if(surfs.some(s=>VERBMID.test(s)))add('C_two_people_and_verb_in_one_link_K6',r.chain_id,r.hadith_id,surfs.find(s=>VERBMID.test(s)).slice(0,70));
   }
   if(IMAMI3.has(w)||w==='sahifat-al-imam-ali-al-rida'){
    // D: link without nasab/connector words, 3+ words (matn/clause as narrator)
    const bad=surfs.find(s=>s.split(' ').length>=4&&!NASAB.test(s));
    if(bad)add('D_clause_or_matn_as_link_Imami',r.chain_id,r.hadith_id,bad.slice(0,60)+(w==='man-la-yahduruhu-al-faqih'?' [faqih]':''));
    if(w==='man-la-yahduruhu-al-faqih'){
      if(surfs.some(s=>/(?:\sاخاه|العبد الصالح)(?![ء-ي])/.test(s)))add('E_faqih_asker_and_Imam_merged',r.chain_id,r.hadith_id,surfs.find(s=>/(?:\sاخاه|العبد الصالح)(?![ء-ي])/.test(s)).slice(0,70));
      if(surfs.length===1&&surfs[0].split(' ').length>=3&&!NASAB.test(surfs[0]))add('E2_faqih_single_link_not_a_name',r.chain_id,r.hadith_id,surfs[0].slice(0,60));
    }
    // F: two routes joined by «وعن» after an Imam
    if(IMAMI3.has(w)&&JOINED_AN.test(hadithText.slice(0,350)))add('F_imami_two_routes_joined_by_wa_an',r.chain_id,r.hadith_id,hadithText.slice(0,90));
    if(w==='sahifat-al-imam-ali-al-rida'&&RIDA2.test(hadithText.slice(0,200)))add('H_rida_second_source_after_haddathatni',r.chain_id,r.hadith_id,hadithText.slice(0,90));
   }
   if(w==='musnad-rabi'||w==='musnad-zayd'){
    if(surfs.length<=1&&/(?:^|\s)عنه(?![ء-ي])/.test(text.slice(0,80)))add('G_unresolved_pronoun_source_Rabi_Zayd',r.chain_id,r.hadith_id,text.slice(0,70));
   }
   if(PCW.has(w)){
    if(surfs.some(s=>s.includes('/')))add('J_pure_canon_slash_link',r.chain_id,r.hadith_id,surfs.find(s=>s.includes('/')).slice(0,40));
   }
  }
 }
 const res={};for(const k of Object.keys(out))res[k]={chains:out[k].chains,hadiths:out[k].hadiths.size,examples:ex[k]};
 res._checked_chains_scanned=n;res._checked_by_work=total;
 fs.writeFileSync('counts.json',JSON.stringify(res,null,1));
 console.log(JSON.stringify(Object.fromEntries(Object.entries(res).filter(([k])=>!k.startsWith('_')).map(([k,v])=>[k,[v.chains,v.hadiths]]))));
 await sql.end();})();
