// usage: node auto.cjs <ids.json> <out.json>: per sample the pre-judge flags (surface-to-text alignment). Read-only.
const fs=require('fs');const {align}=require('./lib.cjs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
 const ids=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const out=[];
 for(const s of ids){
  const [h]=await sql`select coalesce(sanad_ar,'') sanad_ar,text_ar,sanad_inherits_from from hadiths where id=${s.hadith_id}`;
  const ms=await sql`select position,surface_ar,inherited_from_mention_id inh,link_kind from chain_mentions where chain_id=${s.chain_id} and retired_at is null order by position`;
  const hay=h.sanad_ar&&h.sanad_ar.length>5?h.sanad_ar:h.text_ar.slice(0,700);
  const pc=s.hadith_id.includes('pure-canon');
  const flags=pc?[{kind:'pure_canon_sanad_field'}]:h.sanad_inherits_from||ms.some(m=>m.inh)?[{kind:'inherited'}]:align(hay,ms.map(m=>m.surface_ar));
  const nonperson=ms.filter(m=>m.link_kind&&m.link_kind!=='person'&&m.link_kind!=='narrator').map(m=>m.link_kind);
  out.push({...s,n:ms.length,flags,kinds:[...new Set(nonperson)]});
 }
 fs.writeFileSync(process.argv[3],JSON.stringify(out));
 const by={};out.forEach(o=>{const k=o.lane+':'+(o.flags.length?'flag':'clean');by[k]=(by[k]||0)+1;});console.log(by);
 await sql.end();})();
