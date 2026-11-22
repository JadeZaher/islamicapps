// usage: node q.cjs <hadith_id> [len]  -> full sanad/text head + all chains
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{const id=process.argv[2],L=+process.argv[3]||900;
const [h]=await sql`select id,collection_id,hadith_no,sanad,coalesce(sanad_ar,'') sanad_ar,text_ar,sanad_inherits_from from hadiths where id=${id}`;
console.log(id,h.collection_id,h.hadith_no,'\nT:',(h.sanad_ar||h.text_ar).slice(0,L).replace(/\s+/g,' '));
const chs=await sql`select id,branch,suspension from chains where hadith_id=${id} and retired_at is null order by branch`;
for(const c of chs){const ms=await sql`select position,surface_ar from chain_mentions where chain_id=${c.id} and retired_at is null order by position`;console.log(' b'+c.branch+(c.suspension?' susp='+c.suspension:'')+': '+ms.map(m=>m.surface_ar).join(' > '));}
await sql.end();})();
