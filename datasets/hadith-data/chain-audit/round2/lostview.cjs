// usage: node lostview.cjs <openiti|imami_thaq> <n> : hadiths whose chain disappeared (before projection -> now), seeded sample with the start of the Arabic.
const fs=require('fs'),crypto=require('crypto');
const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{const [,,k,n]=process.argv;const L=JSON.parse(fs.readFileSync('nochain.json','utf8'))[k].lost;
 const pick=L.map(h=>[crypto.createHash('md5').update('lost'+h).digest('hex'),h]).sort((a,b)=>a[0]<b[0]?-1:1).slice(0,+n).map(x=>x[1]);
 const out=[];let i=0;
 for(const h of pick){const [r]=await sql`select collection_id,split_confidence sc,sanad_inherits_from inh,chain_status,left(coalesce(nullif(sanad_ar,''),text_ar),130) t,(select count(*) from chains c where c.hadith_id=${h} and c.retired_at is null) nc from hadiths where id=${h}`;
  if(!r){console.log(i++,'missing',h);continue;}
  out.push({h,coll:r.collection_id,nc:+r.nc});
  console.log(i++,r.collection_id.split(':').pop(),'sc='+r.sc,r.inh?'inh':'','st='+r.chain_status,'nc='+r.nc,'|',r.t.replace(/\s+/g,' '));}
 fs.writeFileSync(`lost_sample_${k}.json`,JSON.stringify(out));
 await sql.end();})();
