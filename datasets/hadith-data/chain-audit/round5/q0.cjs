const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const a=await sql`select attname from pg_attribute where attrelid='narrator_transmissions'::regclass and attnum>0 and not attisdropped`;
console.log(a.map(x=>x.attname).join(','));
const d=await sql`select kind from (select relkind::text kind from pg_class where relname='narrator_transmissions') t`; console.log(JSON.stringify(d));
const n=await sql`select count(*)::int c from narrator_transmissions`; console.log(n);
await sql.end();})();
