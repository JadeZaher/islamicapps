// P3a (Sunni surface cut) and P6 (Imami Imam cut) by hadith-level join; appends to pop_ids.json. Read-only.
const fs=require('fs'),path=require('path');
const pg=require('postgres');const postgres=pg.default||pg;const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30,idle_timeout:20});
const SEED='round3-pop-1';
const A='83a827a8610630ed1bbc253eb6cf39483e0b9d0400cae69933286509ede96aef',B='62bcf443b3c4a0ad95e01ca38fb3be9d7d684448efd9606fac72c5da848fce9b',B2='f153d73615b1185454e1b583fd12e522d3cab03e63336321efeacaef89c81ce4';
const R3=[A,B,B2];
const file=path.join(__dirname,'pop_ids.json');let out=JSON.parse(fs.readFileSync(file,'utf8')).filter(x=>!/^P3a|^P6/.test(x.lane));
function dedupe(rows,fmt){const seen=new Set();const res=[];for(const r of rows){if(seen.has(r.hadith_id))continue;seen.add(r.hadith_id);res.push({hadith_id:r.hadith_id,chain_id:r.chain_id,note:fmt(r)});}return res;}
(async()=>{
 // retired mentions (round 3) beside a live mention of the same hadith whose surface is a proper prefix (clause cut)
 let rows=await sql`select m.chain_id,m.hadith_id,m.surface_ar s,o.surface_ar o from chain_mentions o join chain_mentions m on m.hadith_id=o.hadith_id and m.retired_at is null and o.surface_ar like m.surface_ar||' %' and length(o.surface_ar)>length(m.surface_ar)+3 and length(m.surface_ar)>3 where o.retired_at is not null and o.retired_in_dataset_version_id=any(${R3}) and o.hadith_id like 'hadith:k6:%' and (m.changed_in_dataset_version_id=any(${R3}) or m.first_seen_dataset_version_id=any(${R3})) order by md5(o.id||${SEED}) limit 4000`;
 const p3a=dedupe(rows,r=>'cut: '+r.o+' -> '+r.s);console.log('P3a rows',rows.length,'hadiths',p3a.length);
 p3a.slice(0,30).forEach(r=>out.push({lane:'P3a_sunni_surface_cut',hadith_id:r.hadith_id,chain_id:r.chain_id,coll:'',note:r.note}));
 rows=await sql`select m.chain_id,m.hadith_id,m.surface_ar s,o.surface_ar o from chain_mentions o join chain_mentions m on m.hadith_id=o.hadith_id and m.retired_at is null and o.surface_ar like m.surface_ar||' %' and length(o.surface_ar)>length(m.surface_ar)+3 and length(m.surface_ar)>3 where o.retired_at is not null and o.retired_in_dataset_version_id=${B} and o.hadith_id like 'hadith:thaqalayn:%' and (m.changed_in_dataset_version_id=${B} or m.first_seen_dataset_version_id=${B}) and (m.surface_ar like '%عبد الله%' or m.surface_ar like '%أبي جعفر%' or m.surface_ar like '%الرضا%' or m.surface_ar like '%الصادق%' or m.surface_ar like '%الباقر%' or m.surface_ar like '%أبي الحسن%' or m.surface_ar like '%الكاظم%' or m.surface_ar like '%أمير المؤمنين%' or m.surface_ar like '%أبا%') order by md5(o.id||${SEED}) limit 4000`;
 const p6=dedupe(rows,r=>'cut: '+r.o.slice(0,90)+' -> '+r.s);console.log('P6 rows',rows.length,'hadiths',p6.length);
 p6.slice(0,30).forEach(r=>out.push({lane:'P6_imami_imam_cut',hadith_id:r.hadith_id,chain_id:r.chain_id,coll:'',note:r.note}));
 fs.writeFileSync(file,JSON.stringify(out,null,1));await sql.end();})().catch(e=>{console.error(e.message);process.exit(1)});
