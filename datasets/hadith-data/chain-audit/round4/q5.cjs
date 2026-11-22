const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
const ids=['chain:k6:11548:0000','chain:k6:18170:0000','chain:thaqalayn:de66b3121465da74f145e031:0001','chain:thaqalayn:587489582923dabc3b41fbe1:0001','chain:k6:12353:0000','chain:k6:22473:0000'];
const r=await sql`select id,structure_status,structure_reasons from chains where id in ${sql(ids)}`;
console.log(JSON.stringify(r));
await sql.end();})();
