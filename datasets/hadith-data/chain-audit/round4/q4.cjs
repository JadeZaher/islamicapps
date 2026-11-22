const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const [h]=await sql`select id,volume,hadith_no,chapter_no,source_record_id,provider_hadith_id from hadiths where id='hadith:thaqalayn:79ac9f6a03f95d29e8492c6c' or id=(select hadith_id from chains where id='chain:thaqalayn:79ac9f6a03f95d29e8492c6c:0001')`;
console.log(JSON.stringify(h));
const r=await sql`select id,hadith_no,left(text_ar,420) t from hadiths where collection_id='collection:imami:kamal-al-din' and retired_at is null and volume=${h.volume} and hadith_no::int between ${+h.hadith_no-2} and ${+h.hadith_no} order by hadith_no::int`.catch(async e=>{console.log(e.message);return []});
for(const x of r){console.log(x.id,x.hadith_no,x.t.replace(/\s+/g,' '));
 const ms=await sql`select c.branch,m.surface_ar from chain_mentions m join chains c on c.id=m.chain_id where c.hadith_id=${x.id} and c.retired_at is null and m.retired_at is null order by c.branch,m.position`;console.log(ms.map(m=>m.surface_ar).join(' > '));}
await sql.end();})();
