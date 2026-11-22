// Round 4: broader candidate count for "a named source after the last stored link, before the Prophet is mentioned" (K6 six works, checked chains). Read-only.
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:60,idle_timeout:0});
const st=s=>(s||'').replace(/[ً-ٰٟـ]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').replace(/\s+/g,' ');
const PROPHET=/(?<![ء-ي])(?:رسول\s+الله|النبي|نبي\s+الله|رسول)(?![ء-ي])|["“‏]/;
const SPEECH=/(?<![ء-ي])(?:قال|قالت|سمعت|سمعنا|قرات|انتهيت|نظر|دخلت|شهدت|شهدنا|نشهد|حدثني|حدثتني|اخبرني|حدثه|اخبره|حدثهم|يحدث|يقول|تقول)(?![ء-ي])/;
const PHRASE_OK=/^[\s،,]*(?:انه|ان|قال|قالت|يقول|بهذا الحديث|بهذا الاسناد|عن)?[\s،,]*$/;
(async()=>{
 const cur=sql`select c.id chain_id,h.id hadith_id,h.collection_id coll,left(h.text_ar,900) t,(select array_agg(m.surface_ar order by m.position) from chain_mentions m where m.chain_id=c.id and m.retired_at is null) surfs from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and c.structure_status='checked_by_rule' and h.collection_id in ('collection:sunni:bukhari','collection:sunni:muslim','collection:sunni:nasai','collection:sunni:tirmidhi','collection:sunni:abudawud','collection:sunni:ibnmajah')`.cursor(2000);
 let n=0,flag=[];
 for await(const rows of cur){for(const r of rows){n++;const surfs=(r.surfs||[]).map(st);if(!surfs.length)continue;const t=st(r.t);const last=surfs[surfs.length-1];const idx=t.indexOf(last);if(idx<0)continue;
  const rem=t.slice(idx+last.length);const p=rem.search(PROPHET);const gap=(p<0?rem.slice(0,120):rem.slice(0,p)).slice(0,160);
  if(PHRASE_OK.test(gap))continue;const toks=gap.split(/[\s،,]+/).filter(Boolean);
  if(toks.length>=3&&SPEECH.test(gap)&&!/^[\s،,]*(?:قال|قالت)?[\s،,]*(?:سمعت|سمعنا)?\s*$/.test(gap))flag.push({chain:r.chain_id,hadith:r.hadith_id,gap});}}
 // seeded pick of 15 for reading
 flag.sort((a,b)=>a.chain<b.chain?-1:1);
 const pick=[];let k=7;const seen=new Set();while(pick.length<15&&seen.size<flag.length){k=(k*1103515245+12345)%2147483648;const i=k%flag.length;if(!seen.has(i)){seen.add(i);pick.push(flag[i]);}}
 fs.writeFileSync('counts4b.json',JSON.stringify({scanned:n,flagged:flag.length,flagged_hadiths:new Set(flag.map(f=>f.hadith)).size,pick},null,1));
 console.log(n,flag.length);
 await sql.end();})();
