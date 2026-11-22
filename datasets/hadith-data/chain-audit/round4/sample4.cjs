// Round 4 fresh seeded uniform samples of CHECKED (and UNCERTAIN) chains; excludes every hadith/chain id in any earlier sample_check.csv / verdicts.tsv under chain-audit/. Read-only.
const fs=require('fs'),path=require('path');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const SEED='round4-seed-1';
const root=path.join(__dirname,'..');
const priorH=new Set(),priorC=new Set();
function walk(d){for(const f of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,f.name);if(f.isDirectory()){if(f.name!=='round4'&&f.name!=='fetched')walk(p);}else if(/^(sample_check\.csv|verdicts\.tsv)$/.test(f.name)){const t=fs.readFileSync(p,'utf8');for(const m of t.matchAll(/hadith:[^\s",|]+/gi))priorH.add(m[0]);for(const m of t.matchAll(/chain:[^\s",|]+/gi))priorC.add(m[0]);}}}
walk(root);
const plan=[];
const K6=[['muslim',20],['bukhari',13],['nasai',13],['tirmidhi',13],['abudawud',13],['ibnmajah',13]];
K6.forEach(([c,n])=>plan.push({lane:'sunni_k6',coll:'collection:sunni:'+c,n,status:'checked_by_rule'}));
[['ahmad',15],['darimi',10],['muwatta',10]].forEach(([c,n])=>plan.push({lane:'sunni_pc',coll:'collection:sunni:'+c,n,status:'checked_by_rule'}));
[['al-kafi',70],['man-la-yahduruhu-al-faqih',20],['thawab-al-amal',10]].forEach(([c,n])=>plan.push({lane:'imami',coll:'collection:imami:'+c,n,status:'checked_by_rule'}));
plan.push({lane:'rabi',coll:'collection:ibadi:musnad-rabi',n:40,status:'checked_by_rule'});
plan.push({lane:'zayd',coll:'collection:zaydi:musnad-zayd',n:25,status:'checked_by_rule'});
plan.push({lane:'rida',coll:'collection:imami:sahifat-al-imam-ali-al-rida',n:25,status:'checked_by_rule'});
(async()=>{
 const out=[];
 for(const p of plan){
  const rows=await sql`select c.id chain_id,c.hadith_id,c.structure_reasons from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id=${p.coll} and c.structure_status=${p.status} and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null) order by md5(c.id||${SEED}) limit ${p.n*5}`;
  const pick=[];const seenH=new Set();
  for(const r of rows){if(priorH.has(r.hadith_id)||priorC.has(r.chain_id)||seenH.has(r.hadith_id))continue;seenH.add(r.hadith_id);pick.push({...p,chain_id:r.chain_id,hadith_id:r.hadith_id});if(pick.length>=p.n)break;}
  out.push(...pick);
 }
 fs.writeFileSync(path.join(__dirname,'sample_ids.json'),JSON.stringify(out,null,1));
 const cnt={};out.forEach(x=>cnt[x.lane]=(cnt[x.lane]||0)+1);console.log(cnt,'priorH',priorH.size,'priorC',priorC.size);
 // uncertain: 40 sunni, 20 imami uniform across uncertain chains
 const U=[];
 for(const [lane,trad,n] of [['u_sunni','sunni',40],['u_imami','imami',20]]){
  const rows=await sql`select c.id chain_id,c.hadith_id,c.structure_reasons,h.collection_id from chains c join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.retired_at is null and h.collection_id like ${'collection:'+trad+':%'} and c.structure_status='uncertain' and exists(select 1 from chain_mentions m where m.chain_id=c.id and m.retired_at is null) order by md5(c.id||${SEED}||'u') limit ${n*5}`;
  const seenH=new Set();let k=0;
  for(const r of rows){if(priorH.has(r.hadith_id)||priorC.has(r.chain_id)||seenH.has(r.hadith_id))continue;seenH.add(r.hadith_id);U.push({lane,coll:r.collection_id,chain_id:r.chain_id,hadith_id:r.hadith_id,reasons:r.structure_reasons});if(++k>=n)break;}
 }
 fs.writeFileSync(path.join(__dirname,'sample_ids_uncertain.json'),JSON.stringify(U,null,1));
 console.log('uncertain',U.length);
 await sql.end();})();
