const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
for (const t of ['chains','chain_mentions','hadiths','narrator_transmissions','collections','narrators']){
 const r=await sql`select column_name,data_type from information_schema.columns where table_name=${t} order by ordinal_position`;
 console.log(t, r.map(x=>x.column_name).join(','));
}
const c=await sql`select c.id, count(distinct h.id) h, count(distinct ch.id) filter (where ch.retired_at is null) ch from collections c left join hadiths h on h.collection_id=c.id left join chains ch on ch.hadith_id=h.id group by c.id order by c.id`;
console.log(c.map(x=>`${x.id} h=${x.h} ch=${x.ch}`).join('\n'));
await sql.end();})();
