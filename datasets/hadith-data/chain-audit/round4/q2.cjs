const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
for(const id of process.argv.slice(2)){
 const r=await sql`select id,coalesce(sanad_ar,'') s,text_ar t,sanad_inherits_from i from hadiths where id=${id}`;
 for(const x of r){console.log(x.id,'|S:',x.s.slice(0,300),'|T:',x.t.replace(/[ً-ٰٟ]/g,'').slice(0,500));
 const ms=await sql`select c.id,m.position,m.surface_ar,m.link_kind,m.resolution,m.resolution_basis,m.narrator_id from chain_mentions m join chains c on c.id=m.chain_id where c.hadith_id=${x.id} and c.retired_at is null and m.retired_at is null order by c.branch,m.position`;console.log(ms.map(m=>`${m.position}:${m.surface_ar}<${m.link_kind}|${m.resolution}|${m.resolution_basis}|${m.narrator_id}>`).join(' > '));}
}
await sql.end();})();
