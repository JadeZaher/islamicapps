// Fraction of live chains in a collection whose written sanad has name words between stored surfaces (missing links) - pre-judge alignment only.
const {align}=require('./lib.cjs');
const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
 for(const coll of process.argv.slice(2)){
  const rows=await sql`select c.id cid,coalesce(nullif(h.sanad_ar,''),left(h.text_ar,500)) hay,h.sanad_inherits_from inh,(select array_agg(m.surface_ar order by m.position) from chain_mentions m where m.chain_id=c.id and m.retired_at is null) s from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id=${'collection:'+coll} order by md5(c.id||'gs') limit 1200`;
  let n=0,gap=0,notfound=0;
  for(const r of rows){if(!r.s||r.inh)continue;n++;const f=align(r.hay,r.s);if(f.some(x=>x.kind==='gap_before'))gap++;if(f.some(x=>x.kind==='not_found'))notfound++;}
  console.log(coll.padEnd(40),'n='+n,'gap_before='+(100*gap/n).toFixed(1)+'%','not_found='+(100*notfound/n).toFixed(1)+'%');
 }
 await sql.end();})();
