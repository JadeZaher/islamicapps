// Read-only: dump active Imami hadiths/chains/mentions/narrators/candidates to a local JSON cache (path argv[2]).
const fs=require('fs');const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const out=process.argv[2];
const L="collection:imami:%";
const hadiths=await sql`select id,record_id,collection_id,volume,chapter_no,hadith_no,hadith_no_int,url,text_ar,sanad_ar,chain_status,provider_hadith_id from hadiths where collection_id like ${L} and retired_at is null`;
const chains=await sql`select c.id,c.hadith_id,c.branch,c.length,c.extraction_method from chains c join hadiths h on h.id=c.hadith_id where h.collection_id like ${L} and c.retired_at is null`;
const mentions=await sql`select cm.id,cm.chain_id,cm.hadith_id,cm.position,cm.surface_ar,cm.name_latin,cm.narrator_id,cm.resolution,cm.resolution_basis,cm.extraction_method,cm.link_kind from chain_mentions cm join hadiths h on h.id=cm.hadith_id where h.collection_id like ${L} and cm.retired_at is null order by cm.chain_id,cm.position`;
const cands=await sql`select cc.mention_id,cc.narrator_id,cc.basis,cc.detail from chain_mention_candidates cc join chain_mentions cm on cm.id=cc.mention_id join hadiths h on h.id=cm.hadith_id where h.collection_id like ${L} and cm.retired_at is null`;
const ids=[...new Set([...mentions.map(m=>m.narrator_id),...cands.map(c=>c.narrator_id)].filter(Boolean))];
const narrators=await sql`select id,name,name_ar,name_latin,placeholder_reason from narrators where id = any(${ids})`;
const trans=await sql`select student_id,teacher_id,hadith_count,extraction_methods from narrator_transmissions where student_id like 'narrator:riwayat:%' or student_id like 'narrator:imam:%' or student_id like 'narrator:hadith-kg:%'`;
fs.writeFileSync(out,JSON.stringify({hadiths,chains,mentions,cands,narrators,trans}));
console.log(hadiths.length,chains.length,mentions.length,cands.length,narrators.length,trans.length);
await sql.end();})().catch(e=>{console.error(e.message);process.exit(1)});
