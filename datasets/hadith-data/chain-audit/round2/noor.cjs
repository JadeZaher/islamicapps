// usage: node noor.cjs <noorHadithId> [thaqalayn hadith id]: Noor structured sanad list (public GET) beside production chains of one hadith.
const fs=require('fs');
const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{const [,,nid,hid]=process.argv;const url=`https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=${nid}`;
 const r=await fetch(url);const t=await r.text();
 fs.writeFileSync(`fetched/noor_rejal_${nid}.json`,JSON.stringify({url,fetched_utc:new Date().toISOString(),intent:'Structured sanad list of one public hadith to compare route structure (round-2 re-check)',http_status:r.status,response:r.ok?JSON.parse(t):t.slice(0,200)}));
 if(r.ok){const j=JSON.parse(t);const arr=Array.isArray(j)?j:(j.data||j.result||[]);const by={};
  for(const x of arr){const k=x.sanadId||x.sanad||x.chainId||x.order_group||'0';(by[k]=by[k]||[]).push(x);}
  console.log('noor entries',arr.length,'keys',Object.keys(arr[0]||{}).join(','));
  const sk=Object.keys(arr[0]||{});console.log(JSON.stringify(arr.slice(0,3)).slice(0,500));}
 else console.log('HTTP',r.status);
 if(hid){const chs=await sql`select c.id,c.branch,string_agg(m.surface_ar,' > ' order by m.position) s from chains c join chain_mentions m on m.chain_id=c.id and m.retired_at is null where c.hadith_id=${hid} and c.retired_at is null group by c.id,c.branch order by c.branch`;chs.forEach(c=>console.log('PROD b'+c.branch+': '+c.s));}
 await sql.end();})();
