const {norm}=require('./lib.cjs');
const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
const rows=await sql`select c.id cid,h.id hid,coalesce(h.sanad_ar,'') s,left(h.text_ar,260) t,string_agg(m.surface_ar||case when m.narrator_id is not null then '[id]' else '' end,' > ' order by m.position) shape from chains c join hadiths h on h.id=c.hadith_id join chain_mentions m on m.chain_id=c.id and m.retired_at is null where c.retired_at is null and h.collection_id='collection:zaydi:musnad-zayd' group by c.id,h.id,h.sanad_ar,h.text_ar`;
const std=/^[^>]+\[id\] > أبيه\[id\] > جده(?: الحسين(?: بن علي)?)?\[id\] > [^>]+$/;
let applied=0,bad=[];
for(const r of rows){ if(!/\[id\]/.test(r.shape))continue;applied++;
  const T=norm((r.s||r.t)).replace(/\s+/g,' ');
  const ok=/زيد بن علي.{0,40}عن ابيه.{0,30}عن جده.{0,40}عن (علي|ابيه)/.test(T)||/زيد بن علي.{0,40}عن ابيه.{0,30}عن جده/.test(T);
  if(!ok)bad.push([r.cid,r.shape,(r.s||r.t).slice(0,200).replace(/\s+/g,' ')]);}
console.log('chains with identities applied',applied,'whose text does not show the zayd>abihi>jaddihi order',bad.length);
bad.slice(0,8).forEach(b=>console.log(b.join('\n   ')));
await sql.end()})();
