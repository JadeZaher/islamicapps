// Draws the changed-population samples (seeded, read-only). usage: node pops.cjs
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const prior=new Set();
(async()=>{
 const out={};
 const split=JSON.parse(fs.readFileSync('sunni_diff.json','utf8')).split;
 out.sunni_split=await sql`select c.id chain_id,c.hadith_id from chains c where c.retired_at is null and c.hadith_id=any(${split}) and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null) order by md5(c.id||'popA') limit 30`;
 out.imami_jamian=await sql`select c.id chain_id,c.hadith_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id like 'collection:imami:%' and h.text_ar ~ 'جميعا' and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null) and (select count(*) from chains c2 where c2.hadith_id=c.hadith_id and c2.retired_at is null)>1 order by md5(c.id||'popJ') limit 30`;
 const sv=await sql`select suspension,count(*) n from chains where retired_at is null and suspension is not null group by 1`;console.log(sv);
 out.imami_susp={};
 for(const s of sv){out.imami_susp[s.suspension]=await sql`select c.id chain_id,c.hadith_id from chains c where c.retired_at is null and c.suspension=${s.suspension} order by md5(c.id||'popS') limit 30`;}
 out.imami_anon=await sql`select distinct on (c.id) c.id chain_id,c.hadith_id,md5(c.id||'popN') o from chains c join chain_mentions m on m.chain_id=c.id and m.retired_at is null and m.link_kind='anonymous' join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id like 'collection:imami:%' order by c.id,o`;
 out.imami_anon=out.imami_anon.sort((a,b)=>a.o<b.o?-1:1).slice(0,30);
 const lk=await sql`select link_kind,count(*) n from chain_mentions where retired_at is null group by 1`;console.log(lk);
 out.rabi_inherit=await sql`select c.id chain_id,c.hadith_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id='collection:ibadi:musnad-rabi' and h.sanad_inherits_from is not null order by md5(c.id||'popR') limit 30`;
 for(const k of Object.keys(out)){if(!Array.isArray(out[k])){fs.writeFileSync(`pop_${k}.json`,JSON.stringify(Object.entries(out[k]).flatMap(([s,v])=>v.map(x=>({lane:'imami',pop:k+':'+s,chain_id:x.chain_id,hadith_id:x.hadith_id})))));}
  else {fs.writeFileSync(`pop_${k}.json`,JSON.stringify(out[k].map(x=>({lane:k.split('_')[0],pop:k,chain_id:x.chain_id,hadith_id:x.hadith_id}))));console.log(k,out[k].length);}}
 await sql.end();})();
