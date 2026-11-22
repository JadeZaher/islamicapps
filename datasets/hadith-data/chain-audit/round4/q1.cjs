const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
for(const id of ['rabi_0612','rabi_0613','rabi_0614','rabi_0615','rabi_0616','rabi_0368','rabi_0369']){
 const r=await sql`select id,coalesce(sanad_ar,'') s,left(text_ar,200) t,sanad_inherits_from i from hadiths where id like ${'hadith:openiti:ibadi:'+id+'|%'} and retired_at is null`;
 for(const x of r){const ms=await sql`select m.surface_ar from chain_mentions m join chains c on c.id=m.chain_id where c.hadith_id=${x.id} and c.retired_at is null and m.retired_at is null order by c.branch,m.position`;console.log(x.id,'|',(x.s||x.t).replace(/[ً-ٰٟ]/g,'').slice(0,160),'| inh',x.i,'|',ms.map(m=>m.surface_ar).join(' > '));}
}
const k=await sql`select m.link_kind,m.surface_ar,c.structure_status from chain_mentions m join chains c on c.id=m.chain_id where c.id in ('chain:thaqalayn:1b07b8a96e4211ca706cb301:0000','chain:openiti:ibadi:rabi_0415|415|V01P110:0000','chain:openiti:ibadi:rabi_0290|290|V01P076:0000') and m.retired_at is null and m.surface_ar in ('رفعه','بلغني')`;
console.log(JSON.stringify(k));
await sql.end();})();
