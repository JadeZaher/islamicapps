// Compare each sampled Imami chain's hadith (best branch) with the Thaqalayn English sanad (public API JSON saved by the imami lane; same URLs/hosts, re-used read-only).
const fs=require('fs');const T=require('../imami/thaq_lib.cjs');
const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
 const idx=T.loadThaq();const ids=JSON.parse(fs.readFileSync('sample_ids.json','utf8')).filter(s=>s.lane==='imami');const out={};
 let st={matched:0,agree:0,disagree:0,none:0};
 for(const s of ids){
  const [h]=await sql`select id,url,volume,collection_id from hadiths where id=${s.hadith_id}`;const col=h.collection_id.replace('collection:imami:','');
  const th=idx.get(T.keyOf(h,col));if(!th||!th.en){st.none++;out[s.chain_id]={status:'no_english'};continue;}
  const names=T.englishNames(th.en);if(names.length<2){st.none++;out[s.chain_id]={status:'english_unparsed',en:th.en.slice(0,160)};continue;}
  const chs=await sql`select c.id,array_agg(m.surface_ar order by m.position) s from chains c join chain_mentions m on m.chain_id=c.id and m.retired_at is null where c.hadith_id=${s.hadith_id} and c.retired_at is null group by c.id`;
  let best=null;for(const c of chs){const a=T.align(c.s,names);const sc=a.ordered/Math.max(a.n,a.m);if(!best||sc>best.sc)best={sc,a,id:c.id};}
  if(!best){st.none++;out[s.chain_id]={status:'no_chain'};continue;}
  const a=best.a;const tol=Math.max(1,Math.round(0.15*Math.max(a.n,a.m)));
  const agree=(Math.abs(a.n-a.m)<=1&&a.ordered>=Math.min(a.n,a.m))||(a.ordered>=Math.min(a.n,a.m)-tol&&Math.abs(a.n-a.m)<=tol);
  st.matched++;agree?st.agree++:st.disagree++;out[s.chain_id]={status:agree?'agree':'disagree',n:a.n,m:a.m,ordered:a.ordered,en:th.en.slice(0,200),url:`https://www.thaqalayn-api.net/api/v2/${th.bookId}`};
 }
 fs.writeFileSync('thaq_compare.json',JSON.stringify(out));console.log(st);
 await sql.end();})();
