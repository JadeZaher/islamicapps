// Fresh seeded uniform samples of live chains per work; excludes hadith ids used by earlier lanes. Read-only.
const fs=require('fs'),path=require('path');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const SEED='round2-seed-1';
const prior=new Set();
for(const d of ['sunni','imami','ibadi-zaydi']){const t=fs.readFileSync(path.join(__dirname,'..',d,'sample_check.csv'),'utf8');for(const m of t.matchAll(/hadith:[a-z0-9_:|\-]+/gi))prior.add(m[0]);}
const plan=[];
const sun=['bukhari','muslim','nasai','tirmidhi','abudawud','ibnmajah','ahmad','darimi','muwatta'];
sun.forEach((c,i)=>plan.push({lane:'sunni',coll:'collection:sunni:'+c,n:i==0?12:11}));
plan.push({lane:'imami',coll:'collection:imami:al-kafi',n:50});
plan.push({lane:'imami',coll:'collection:imami:man-la-yahduruhu-al-faqih',n:12});
const others=['al-amali-mufid','al-amali-saduq','al-khisal','al-tawhid-saduq','fadail-al-shia','kamal-al-din','kamil-al-ziyarat','kitab-al-duafa','kitab-al-ghayba-numani','kitab-al-ghayba-tusi','kitab-al-mumin','kitab-al-zuhd','maani-al-akhbar','mujam-al-ahadith-al-mutabara','sifat-al-shia','thawab-al-amal','uyun-akhbar-al-rida','risalat-al-huquq'];
others.forEach((c,i)=>plan.push({lane:'imami',coll:'collection:imami:'+c,n:i<2?3:2}));
plan.push({lane:'rabi',coll:'collection:ibadi:musnad-rabi',n:40});
plan.push({lane:'zayd',coll:'collection:zaydi:musnad-zayd',n:40});
plan.push({lane:'rida',coll:'collection:imami:sahifat-al-imam-ali-al-rida',n:40});
(async()=>{
 const out=[];
 for(const p of plan){
  const rows=await sql`select c.id chain_id,c.hadith_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id=${p.coll} and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null) order by md5(c.id||${SEED}) limit ${p.n*3}`;
  const pick=[];const seenH=new Set();
  for(const r of rows){if(prior.has(r.hadith_id)||seenH.has(r.hadith_id))continue;seenH.add(r.hadith_id);pick.push({...p,chain_id:r.chain_id,hadith_id:r.hadith_id});if(pick.length>=p.n)break;}
  out.push(...pick);
 }
 fs.writeFileSync(path.join(__dirname,'sample_ids.json'),JSON.stringify(out,null,1));
 const cnt={};out.forEach(x=>cnt[x.lane]=(cnt[x.lane]||0)+1);console.log(cnt,'prior',prior.size);
 await sql.end();})();
