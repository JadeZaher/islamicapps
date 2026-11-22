const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
const q=async(l,p)=>{const r=await p;console.log(l.padEnd(60),r.map(x=>Object.entries(x).map(([k,v])=>k+'='+v).join(' ')).join(' ; '));};
await q('imami mentions exactly «و»',sql`select count(*) n from chain_mentions m join hadiths h on h.id=m.hadith_id where m.retired_at is null and h.collection_id like 'collection:imami:%' and m.surface_ar='و'`);
await q('imami mentions with link_kind not_a_narrator by suspension',sql`select c.suspension s,count(*) n from chain_mentions m join chains c on c.id=m.chain_id join hadiths h on h.id=m.hadith_id where m.retired_at is null and c.retired_at is null and h.collection_id like 'collection:imami:%' and m.link_kind='not_a_narrator' group by 1`);
await q('imami live chains by suspension',sql`select coalesce(c.suspension,'none') s,count(*) n from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id like 'collection:imami:%' group by 1`);
await q('imami mentions with inherited_from set (chains)',sql`select count(distinct m.chain_id) n from chain_mentions m join hadiths h on h.id=m.hadith_id where m.retired_at is null and m.inherited_from_mention_id is not null and h.collection_id like 'collection:imami:%'`);
await q('rida chains / hadiths',sql`select count(distinct c.id) chains,count(distinct h.id) h from hadiths h left join chains c on c.hadith_id=h.id and c.retired_at is null where h.collection_id='collection:imami:sahifat-al-imam-ali-al-rida' and h.retired_at is null`);
await sql.end();})();
