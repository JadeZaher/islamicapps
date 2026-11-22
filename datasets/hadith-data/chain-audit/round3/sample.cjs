// Round 3 fresh seeded uniform samples; excludes hadith ids in earlier lanes + round2 sample_check.csv. Read-only.
const fs=require('fs'),path=require('path');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const SEED='round3-seed-1';
const prior=new Set();
for(const d of ['sunni','imami','ibadi-zaydi','round2']){const t=fs.readFileSync(path.join(__dirname,'..',d,'sample_check.csv'),'utf8');for(const m of t.matchAll(/hadith:[^\s",]+/gi))prior.add(m[0]);}
const plan=[];
const sun=['bukhari','muslim','nasai','tirmidhi','abudawud','ibnmajah','ahmad','darimi','muwatta'];
sun.forEach((c,i)=>plan.push({lane:'sunni',coll:'collection:sunni:'+c,n:i<1?12:11}));
plan.push({lane:'imami',coll:'collection:imami:al-kafi',n:50});
plan.push({lane:'imami',coll:'collection:imami:man-la-yahduruhu-al-faqih',n:12});
plan.push({lane:'imami',coll:'collection:imami:thawab-al-amal',n:6});
const others=['al-amali-mufid','al-amali-saduq','al-khisal','al-tawhid-saduq','fadail-al-shia','kamal-al-din','kamil-al-ziyarat','kitab-al-duafa','kitab-al-ghayba-numani','kitab-al-ghayba-tusi','kitab-al-mumin','kitab-al-zuhd','maani-al-akhbar','mujam-al-ahadith-al-mutabara','sifat-al-shia','uyun-akhbar-al-rida'];
others.forEach((c,i)=>plan.push({lane:'imami',coll:'collection:imami:'+c,n:2}));
(async()=>{
 const out=[];
 for(const p of plan){
  const rows=await sql`select c.id chain_id,c.hadith_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id=${p.coll} and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null) order by md5(c.id||${SEED}) limit ${p.n*4}`;
  const pick=[];const seenH=new Set();
  for(const r of rows){if(prior.has(r.hadith_id)||seenH.has(r.hadith_id))continue;seenH.add(r.hadith_id);pick.push({...p,chain_id:r.chain_id,hadith_id:r.hadith_id});if(pick.length>=p.n)break;}
  out.push(...pick);
 }
 for(const [lane,coll] of [['rabi','collection:ibadi:musnad-rabi'],['zayd','collection:zaydi:musnad-zayd'],['rida','collection:imami:sahifat-al-imam-ali-al-rida']]){
  const rows=await sql`select h.id hadith_id from hadiths h where h.retired_at is null and h.collection_id=${coll} order by md5(h.id||${SEED}) limit 160`;
  let k=0;for(const r of rows){if(prior.has(r.hadith_id))continue;out.push({lane,coll,chain_id:null,hadith_id:r.hadith_id});if(++k>=40)break;}
 }
 fs.writeFileSync(path.join(__dirname,'sample_ids.json'),JSON.stringify(out,null,1));
 const cnt={};out.forEach(x=>cnt[x.lane]=(cnt[x.lane]||0)+1);console.log(cnt,'prior',prior.size);
 await sql.end();})();
