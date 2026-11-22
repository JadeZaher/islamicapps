// usage: node pairdump.cjs <from> <to> [textlen]  -> sampled pair, supporting chain with the pair bracketed, narrator names, Arabic. Read-only.
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const strip=s=>(s||'').replace(/[ً-ٰٟ]/g,'').replace(/\s+/g,' ');
(async()=>{
 const [,,a,b,tl]=process.argv;const L=+tl||360;
 const ids=JSON.parse(fs.readFileSync('pair_ids.json','utf8')).slice(+a,+b);
 for(let i=0;i<ids.length;i++){
  const s=ids[i];
  const [h]=await sql`select collection_id,hadith_no,sanad,coalesce(sanad_ar,'') sa,text_ar from hadiths where id=${s.hadith_id}`;
  const [S]=await sql`select name_ar from narrators where id=${s.student}`;const [T]=await sql`select name_ar from narrators where id=${s.teacher}`;
  const ms=await sql`select m.position,m.surface_ar from chain_mentions m where m.chain_id=${s.chain_id} and m.retired_at is null order by m.position`;
  const pc=/ahmad|darimi|muwatta/.test(h.collection_id);
  let o=`#${+a+i} ${s.lane} [${h.collection_id.split(':').pop()} ${h.hadith_no}] ${s.chain_id} supports=${s.support_n} hc=${s.hadith_count}\n  STU: ${strip(S&&S.name_ar).slice(0,70)}  | TEA: ${strip(T&&T.name_ar).slice(0,70)}\n`;
  if(pc)o+=`  S: ${strip(h.sanad).slice(0,L)}\n`;
  o+=`  T: ${strip(pc?h.text_ar.slice(0,80):(h.sa||h.text_ar)).slice(0,L)}\n`;
  o+=`  C: `+ms.map(m=>m.position===s.apos?`[${strip(m.surface_ar)}`:m.position===s.apos+1?`${strip(m.surface_ar)}]`:strip(m.surface_ar)).join(' > ')+'\n';
  console.log(o);
 }
 await sql.end();})();
