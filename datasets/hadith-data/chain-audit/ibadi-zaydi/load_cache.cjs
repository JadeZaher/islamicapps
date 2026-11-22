// Read-only: dump the three OpenITI works (rabi, zayd, rida) with chains/mentions/narrators/candidates/transmissions to a local JSON cache (argv[2]).
const fs=require('fs');const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const out=process.argv[2];
const like='hadith:openiti:%';
const hadiths=await sql`select id,record_id,collection_id,hadith_no,text_ar,sanad_ar,matn_ar,sanad_inherits_from,split_confidence,source_notes,chain_status from hadiths where id like ${like} and retired_at is null`;
const hid=new Set(hadiths.map(h=>h.id));
const chains=await sql`select c.id,c.hadith_id,c.branch,c.length,c.extraction_method from chains c where c.hadith_id like ${like} and c.retired_at is null`;
const mentions=await sql`select cm.id,cm.chain_id,cm.hadith_id,cm.position,cm.surface_ar,cm.name_latin,cm.narrator_id,cm.resolution,cm.resolution_basis,cm.extraction_method from chain_mentions cm where cm.hadith_id like ${like} and cm.retired_at is null order by cm.chain_id,cm.position`;
const cands=await sql`select cc.mention_id,cc.narrator_id,cc.basis,cc.detail,cc.source_position,cc.source_ref from chain_mention_candidates cc join chain_mentions cm on cm.id=cc.mention_id where cm.hadith_id like ${like} and cm.retired_at is null`;
const ids=[...new Set([...mentions.map(m=>m.narrator_id),...cands.map(c=>c.narrator_id)].filter(Boolean))];
const narrators=await sql`select id,name,name_ar,name_latin,placeholder_reason from narrators where id = any(${ids})`;
const trans=await sql`select distinct on (student_id,teacher_id) student_id,teacher_id,hadith_count,extraction_methods from narrator_transmissions where student_id = any(${ids}) or teacher_id = any(${ids})`;
fs.writeFileSync(out,JSON.stringify({hadiths,chains,mentions,cands,narrators,trans}));
console.log(hadiths.length,chains.length,mentions.length,cands.length,narrators.length,trans.length);
await sql.end();})().catch(e=>{console.error(e.message);process.exit(1)});
