const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const a=await sql`select attname from pg_attribute where attrelid='narrator_transmissions'::regclass and attnum>0 and not attisdropped`;
console.log(a.map(x=>x.attname).join(','));
const d=await sql`select definition from pg_matviews where matviewname='narrator_transmissions'`;
console.log(d[0]&&d[0].definition);
const r=await sql`select split_part(h.collection_id,':',2)||':'||split_part(h.collection_id,':',3) w, c.structure_status s, count(*) n from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null group by 1,2 order by 1,2`;
console.log(r.map(x=>`${x.w} ${x.s} ${x.n}`).join('\n'));
const rs=await sql`select structure_reasons, count(*) from chains where retired_at is null and structure_status='uncertain' group by 1 order by 2 desc limit 15`;
console.log(JSON.stringify(rs));
await sql.end();})();
