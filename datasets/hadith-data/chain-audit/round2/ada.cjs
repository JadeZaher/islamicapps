const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
const a=await sql`select count(*) n,count(distinct c.hadith_id) h from chains c join chain_mentions m1 on m1.chain_id=c.id and m1.retired_at is null and m1.position=1 where c.retired_at is null and m1.surface_ar='عدة من أصحابنا' and exists(select 1 from chain_mentions m0 where m0.chain_id=c.id and m0.retired_at is null and m0.position=0 and m0.surface_ar<>'عدة من أصحابنا')`;
console.log('chains with «عدة من أصحابنا» at position 1 under a named opener:',a[0].n,'hadiths',a[0].h);
const b=await sql`select count(*) n from chains c join chain_mentions m1 on m1.chain_id=c.id and m1.retired_at is null and m1.position=1 where c.retired_at is null and m1.surface_ar in ('أبيه','ابيه') and exists(select 1 from chain_mentions m2 where m2.chain_id=c.id and m2.retired_at is null and m2.position=2 and m2.surface_ar ~ '^(الفضل بن شاذان|سهل بن زياد|الفضل)')`;
console.log('chains أبيه at 1 then الفضل/سهل at 2 (false-link shape):',b[0].n);
await sql.end();})();
