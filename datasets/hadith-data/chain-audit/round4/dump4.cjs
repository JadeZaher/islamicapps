// usage: node dump4.cjs <ids.json> <from> <to> [textlen]  -> compact view of stored chains vs Arabic. Read-only. Diacritics stripped.
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const strip=s=>(s||'').replace(/[ً-ٰٟ]/g,'').replace(/\s+/g,' ');
(async()=>{
 const [,,file,a,b,tl]=process.argv;const L=+tl||420;
 const ids=JSON.parse(fs.readFileSync(file,'utf8')).slice(+a,+b);
 for(let i=0;i<ids.length;i++){
  const s=ids[i];
  const [h]=await sql`select id,collection_id,hadith_no,sanad,coalesce(sanad_ar,'') sanad_ar,text_ar,sanad_inherits_from from hadiths where id=${s.hadith_id}`;
  const chs=await sql`select id,branch,suspension,missing_link_after,structure_reasons from chains where hadith_id=${s.hadith_id} and retired_at is null order by branch,id`;
  let o=`#${+a+i} ${s.lane} ${s.chain_id} [${h.collection_id.split(':').pop()} ${h.hadith_no}]${h.sanad_inherits_from?' inh='+h.sanad_inherits_from:''}${s.reasons?' R='+JSON.stringify(s.reasons):''}\n`;
  const pc=/ahmad|darimi|muwatta/.test(h.collection_id);
  if(pc)o+=`  S: ${strip(h.sanad).slice(0,L)}\n`;
  const san=h.sanad_ar||h.text_ar;
  o+=`  T: ${strip(pc?h.text_ar.slice(0,120):san).slice(0,L)}${san.length>L&&!pc?'…':''}\n`;
  if(h.sanad_inherits_from){const [p]=await sql`select coalesce(sanad_ar,'') sanad_ar,text_ar from hadiths where id=${h.sanad_inherits_from}`;o+=`  P: ${strip(p.sanad_ar||p.text_ar).slice(0,L)}\n`;}
  let shown=0;
  for(const c of chs){ if(c.id!==s.chain_id&&shown>=8)continue; if(c.id!==s.chain_id)shown++;
   const ms=await sql`select m.position,m.surface_ar from chain_mentions m where m.chain_id=${c.id} and m.retired_at is null order by m.position`;
   o+=`  ${c.id===s.chain_id?'*':' '}b${c.branch}${c.suspension?' susp='+c.suspension:''}${c.missing_link_after!=null?' miss@'+c.missing_link_after:''}: `+ms.map(m=>`${m.position}:${strip(m.surface_ar)}`).join(' > ')+'\n';
  }
  if(chs.length>9)o+=`  (${chs.length} chains total)\n`;
  console.log(o);
 }
 await sql.end();})();
