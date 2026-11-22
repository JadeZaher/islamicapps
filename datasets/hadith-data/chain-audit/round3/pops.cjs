// Round 3 changed-population samples (30 each). Versions: A=83a827a8 (.6), B=62bcf443 (.7), B2=f153d736 (.8). Read-only.
const fs=require('fs'),path=require('path');
const pg=require('postgres');const postgres=pg.default||pg;const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30,idle_timeout:20});
const SEED='round3-pop-1';
const A='83a827a8610630ed1bbc253eb6cf39483e0b9d0400cae69933286509ede96aef',B='62bcf443b3c4a0ad95e01ca38fb3be9d7d684448efd9606fac72c5da848fce9b',B2='f153d73615b1185454e1b583fd12e522d3cab03e63336321efeacaef89c81ce4';
const R3=[A,B,B2];
const out=[];const counts={};
function add(pop,rows,n){counts[pop]=rows.total!=null?rows.total:rows.length;let k=0;for(const r of rows){out.push({lane:pop,hadith_id:r.hadith_id,chain_id:r.chain_id||null,coll:r.coll||'',note:r.note||''});if(++k>=n)break;}}
function dedupe(rows,fmt){const seen=new Set();const res=[];for(const r of rows){if(seen.has(r.hadith_id))continue;seen.add(r.hadith_id);res.push({hadith_id:r.hadith_id,chain_id:r.chain_id,note:fmt(r)});}res.total=rows.length;return res;}
(async()=>{
 // P1 Sunni reports with >1 live chain, at least one chain touched by round 3
 let rows=await sql`select h.id hadith_id,h.collection_id coll from hadiths h where h.retired_at is null and h.collection_id like 'collection:sunni:%' and (select count(*) from chains c where c.hadith_id=h.id and c.retired_at is null)>1 and exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null and (c.changed_in_dataset_version_id=any(${R3}) or c.first_seen_dataset_version_id=any(${R3}))) order by md5(h.id||${SEED}) limit 400`;
 const c1=await sql`select count(*) n from hadiths h where h.retired_at is null and h.collection_id like 'collection:sunni:%' and (select count(*) from chains c where c.hadith_id=h.id and c.retired_at is null)>1 and exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null and (c.changed_in_dataset_version_id=any(${R3}) or c.first_seen_dataset_version_id=any(${R3})))`;
 rows.total=+c1[0].n;add('P1_sunni_multichain',rows,30);console.log('P1');
 // P2 Sunni reports whose chains retired in A and fewer live chains now (split in r2, restored whole in r3)
 rows=await sql`with ret as (select hadith_id,count(*) nr from chains where retired_in_dataset_version_id=${A} group by 1), live as (select hadith_id,count(*) nl from chains where retired_at is null group by 1) select h.id hadith_id,h.collection_id coll,ret.nr,live.nl from hadiths h join ret on ret.hadith_id=h.id join live on live.hadith_id=h.id where h.retired_at is null and h.collection_id like 'collection:sunni:%' and live.nl<ret.nr order by md5(h.id||${SEED})`;
 rows.total=rows.length;add('P2_sunni_restored_whole',rows.map(r=>({...r,note:'retiredA='+r.nr+' live='+r.nl})),30);console.log('P2');
 // P3a Sunni live mentions changed in round 3 whose retired predecessor (same chain, position) was longer and starts with the live surface (cut)
 rows=await sql`select m.chain_id,m.hadith_id,m.surface_ar s,o.surface_ar o from chain_mentions m join chain_mentions o on o.chain_id=m.chain_id and o.position=m.position and o.retired_at is not null and o.retired_in_dataset_version_id=any(${R3}) where m.retired_at is null and m.changed_in_dataset_version_id=any(${R3}) and m.hadith_id like 'hadith:k6:%' and length(o.surface_ar)>length(m.surface_ar)+3 and o.surface_ar like m.surface_ar||' %' order by md5(m.id||${SEED}) limit 3000`;
 add('P3a_sunni_surface_cut',dedupe(rows,r=>'cut: '+r.o+' -> '+r.s),30);console.log('P3a');
 // P3b Sunni mentions first seen in round 3 (new mentions), uniform
 rows=await sql`select m.chain_id,m.hadith_id,m.surface_ar s from chain_mentions m where m.retired_at is null and m.first_seen_dataset_version_id=any(${R3}) and m.hadith_id like 'hadith:k6:%' order by md5(m.id||${SEED}) limit 400`;
 const c3=await sql`select count(*) n from chain_mentions m where m.retired_at is null and m.first_seen_dataset_version_id=any(${R3}) and m.hadith_id like 'hadith:k6:%'`;
 const r3b=dedupe(rows,r=>'new mention '+r.s);r3b.total=+c3[0].n;add('P3b_sunni_new_mentions',r3b,30);console.log('P3b');
 // P4 al-Kafi reports with >=2 live chains touched in B, text has no jamian
 rows=await sql`select h.id hadith_id from hadiths h where h.retired_at is null and h.collection_id='collection:imami:al-kafi' and h.text_ar not like '%جميعا%' and (select count(*) from chains c where c.hadith_id=h.id and c.retired_at is null)>=2 and exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null and (c.changed_in_dataset_version_id=${B} or c.first_seen_dataset_version_id=${B})) order by md5(h.id||${SEED}) limit 300`;
 const c4=await sql`select count(*) n from hadiths h where h.retired_at is null and h.collection_id='collection:imami:al-kafi' and h.text_ar not like '%جميعا%' and (select count(*) from chains c where c.hadith_id=h.id and c.retired_at is null)>=2 and exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null and (c.changed_in_dataset_version_id=${B} or c.first_seen_dataset_version_id=${B}))`;
 rows.total=+c4[0].n;add('P4_kafi_regrouped_no_jamian',rows,30);console.log('P4');
 // P5 Thawab al-Amal live chains touched in B
 rows=await sql`select c.id chain_id,c.hadith_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id='collection:imami:thawab-al-amal' and (c.changed_in_dataset_version_id=${B} or c.first_seen_dataset_version_id=${B}) order by md5(c.id||${SEED}) limit 100`;
 const c5=await sql`select count(*) n from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id='collection:imami:thawab-al-amal' and (c.changed_in_dataset_version_id=${B} or c.first_seen_dataset_version_id=${B})`;
 rows.total=+c5[0].n;add('P5_thawab_changed_B',rows,30);console.log('P5');
 // P6 Imami live mentions changed in B where the retired predecessor was longer and the live surface is an Imam (Imam cut from following words)
 rows=await sql`select m.chain_id,m.hadith_id,m.surface_ar s,o.surface_ar o from chain_mentions m join chain_mentions o on o.chain_id=m.chain_id and o.position=m.position and o.retired_at is not null and o.retired_in_dataset_version_id=${B} where m.retired_at is null and m.changed_in_dataset_version_id=${B} and m.hadith_id like 'hadith:thaqalayn:%' and length(o.surface_ar)>length(m.surface_ar)+3 and o.surface_ar like m.surface_ar||' %' and (m.surface_ar like '%عبد الله%' or m.surface_ar like '%أبي جعفر%' or m.surface_ar like '%الرضا%' or m.surface_ar like '%الصادق%' or m.surface_ar like '%الباقر%' or m.surface_ar like '%أبي الحسن%' or m.surface_ar like '%الكاظم%' or m.surface_ar like '%أمير المؤمنين%') order by md5(m.id||${SEED}) limit 3000`;
 add('P6_imami_imam_cut',dedupe(rows,r=>'cut: '+r.o.slice(0,80)+' -> '+r.s),30);console.log('P6');
 // P7 ghayr wahid live mentions touched in round 3 (15 Sunni, 15 Imami)
 for(const [lk,nm] of [['hadith:k6:%','sunni'],['hadith:thaqalayn:%','imami']]){
  const rr=await sql`select m.chain_id,m.hadith_id,m.surface_ar s from chain_mentions m where m.retired_at is null and (m.changed_in_dataset_version_id=any(${R3}) or m.first_seen_dataset_version_id=any(${R3})) and m.hadith_id like ${lk} and m.surface_ar like '%غير واحد%' order by md5(m.id||${SEED}) limit 400`;
  add('P7_ghayr_wahid_'+nm,dedupe(rr,r=>r.s),15);}
 console.log('P7');
 // P8 Rabi/Zayd low-confidence reports with a chain first seen/changed in A
 for(const [coll,nm] of [['collection:ibadi:musnad-rabi','rabi'],['collection:zaydi:musnad-zayd','zayd']]){
  const rr=await sql`select h.id hadith_id from hadiths h where h.retired_at is null and h.collection_id=${coll} and h.split_confidence='low' and exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null and (c.first_seen_dataset_version_id=${A} or c.changed_in_dataset_version_id=${A})) order by md5(h.id||${SEED}) limit 100`;
  const cc=await sql`select count(*) n from hadiths h where h.retired_at is null and h.collection_id=${coll} and h.split_confidence='low' and exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null and (c.first_seen_dataset_version_id=${A} or c.changed_in_dataset_version_id=${A}))`;
  rr.total=+cc[0].n;add('P8_'+nm+'_low_chain_back',rr,15);}
 console.log('P8');
 // P9 Rida chains touched in A
 rows=await sql`select c.id chain_id,c.hadith_id,c.length from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id='collection:imami:sahifat-al-imam-ali-al-rida' and (c.changed_in_dataset_version_id=${A} or c.first_seen_dataset_version_id=${A}) order by md5(c.id||${SEED})`;
 rows.total=rows.length;add('P9_rida_changed_A',rows.map(r=>({...r,note:'len '+r.length})),30);
 fs.writeFileSync(path.join(__dirname,'pop_ids.json'),JSON.stringify(out,null,1));
 console.log(counts,out.length);await sql.end();})().catch(e=>{console.error(e.message);process.exit(1)});
