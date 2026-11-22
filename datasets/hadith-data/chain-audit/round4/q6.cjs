// Round 4: do chain mentions whose surface is «تابع/» (or any surface with '/') carry a standing identity, i.e. reach narrator_transmissions? Read-only.
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:60});
(async()=>{
const r=await sql`select count(*)::int mentions,count(*) filter (where m.narrator_id is not null)::int with_id,count(*) filter (where m.narrator_id is not null and m.resolution in ('source_index','human_verified','derived_relation_verified') and m.link_kind not in ('anonymous','not_a_narrator'))::int standing,count(distinct m.surface_ar)::int surfaces from chain_mentions m join chains c on c.id=m.chain_id where c.retired_at is null and m.retired_at is null and c.structure_status='checked_by_rule' and m.surface_ar like '%/%'`;
console.log(JSON.stringify(r));
const s=await sql`select m.surface_ar,count(*)::int n,min(m.link_kind::text) lk,min(m.resolution::text) res from chain_mentions m join chains c on c.id=m.chain_id where c.retired_at is null and m.retired_at is null and c.structure_status='checked_by_rule' and m.surface_ar like '%/%' group by 1 order by 2 desc limit 6`;
console.log(JSON.stringify(s));
// pairs whose student or teacher is such a mention
const p=await sql`select count(distinct (a.narrator_id,b.narrator_id))::int pairs from chain_mentions a join chain_mentions b on b.chain_id=a.chain_id and b.position=a.position+1 and b.retired_at is null join chains c on c.id=a.chain_id and c.retired_at is null and c.structure_status='checked_by_rule' join narrator_transmissions t on t.student_id=a.narrator_id and t.teacher_id=b.narrator_id where a.retired_at is null and (a.surface_ar like '%/%' or b.surface_ar like '%/%') and a.narrator_id is not null and b.narrator_id is not null`;
console.log('pairs touching a slash surface',JSON.stringify(p));
// Faqih: 'D/E2' examples pairs with clause links: how many transmission pairs involve a Faqih link of >=4 words with no nasab word?
await sql.end();})();
