// Imami chains whose back-reference opening was filled from the previous report (inherited_from_mention_id set).
const fs=require('fs');
const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
 const r=await sql`select count(distinct m.chain_id) n from chain_mentions m join hadiths h on h.id=m.hadith_id where m.retired_at is null and m.inherited_from_mention_id is not null and h.collection_id like 'collection:imami:%' and h.collection_id<>'collection:imami:sahifat-al-imam-ali-al-rida'`;console.log('chains with inherited mentions (imami thaqalayn):',r[0].n);
 const s=await sql`select c.id chain_id,c.hadith_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id like 'collection:imami:%' and h.collection_id<>'collection:imami:sahifat-al-imam-ali-al-rida' and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null and m.inherited_from_mention_id is not null) order by md5(c.id||'popF') limit 30`;
 fs.writeFileSync('pop_imami_filled.json',JSON.stringify(s.map(x=>({lane:'imami',pop:'imami_filled',...x}))));
 for(const x of s.slice(0,30)){
  const ms=await sql`select m.position,m.surface_ar,m.inherited_from_mention_id inh,m.link_kind from chain_mentions m where m.chain_id=${x.chain_id} and m.retired_at is null order by position`;
  const [h]=await sql`select left(text_ar,120) t,collection_id from hadiths where id=${x.hadith_id}`;
  const inhIds=ms.filter(m=>m.inh).map(m=>m.inh);
  const par=inhIds.length?await sql`select m.hadith_id,m.position,m.surface_ar,c.branch from chain_mentions m join chains c on c.id=m.chain_id where m.id=${inhIds[0]}`:[];
  let pc='';if(par[0]){const pm=await sql`select m.surface_ar from chain_mentions m join chains c on c.id=m.chain_id where c.hadith_id=${par[0].hadith_id} and c.branch=${par[0].branch} and c.retired_at is null and m.retired_at is null order by m.position`;const [ph]=await sql`select left(text_ar,70) t from hadiths where id=${par[0].hadith_id}`;pc=pm.map(q=>q.surface_ar).join(' > ')+'  | PT: '+ph.t.replace(/\s+/g,' ');}
  console.log(s.indexOf(x)+' '+h.collection_id.split(':').pop()+'\n  T: '+h.t.replace(/\s+/g,' ')+'\n  *: '+ms.map(m=>m.surface_ar+(m.inh?'^':'')).join(' > ')+'\n  P: '+pc);}
 await sql.end();})();
