// Read-only: dump all active Sunni chains/mentions/narrators/lifespans to a local JSON cache (path argv[2]).
const fs=require('fs');const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const out=process.argv[2];
const hadiths=await sql`select id,collection_id,hadith_no,text_ar from hadiths where collection_id like 'collection:sunni:%' and retired_at is null`;
const chains=await sql`select c.id,c.hadith_id,c.branch,c.length,c.extraction_method from chains c join hadiths h on h.id=c.hadith_id where h.collection_id like 'collection:sunni:%' and c.retired_at is null`;
const mentions=await sql`select cm.id,cm.chain_id,cm.hadith_id,cm.position,cm.surface_ar,cm.narrator_id,cm.resolution,cm.extraction_method,cm.link_kind from chain_mentions cm join hadiths h on h.id=cm.hadith_id where h.collection_id like 'collection:sunni:%' and cm.retired_at is null order by cm.chain_id,cm.position`;
const ids=[...new Set(mentions.map(m=>m.narrator_id).filter(Boolean))];
const narrators=await sql`select n.id,n.name,n.name_ar,l.birth_min,l.birth_max,l.death_min,l.death_max from narrators n left join narrator_lifespans l on l.narrator_id=n.id where n.id = any(${ids})`;
const trans=await sql`select student_id,teacher_id,hadith_count,temporal_plausibility from narrator_transmissions`;
fs.writeFileSync(out,JSON.stringify({hadiths,chains,mentions,narrators,trans}));
console.log(hadiths.length,chains.length,mentions.length,narrators.length,trans.length);
await sql.end();})();
