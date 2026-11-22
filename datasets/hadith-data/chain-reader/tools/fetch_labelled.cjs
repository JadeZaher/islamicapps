const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{
 const [,,idsFile,out]=process.argv;
 const ids=JSON.parse(fs.readFileSync(idsFile,'utf8'));
 const res={};
 const hs=await sql`select id,collection_id,hadith_no,sanad,sanad_ar,text_ar,sanad_inherits_from,split_confidence,retired_at from hadiths where id in ${sql(ids)}`;
 for(const h of hs) res[h.id]={h:{...h,retired_at:h.retired_at?String(h.retired_at):null},chains:[]};
 const cs=await sql`select id,hadith_id,branch,structure_status,structure_reasons,suspension,missing_link_after from chains where hadith_id in ${sql(ids)} and retired_at is null order by hadith_id,branch,id`;
 const cmap={};
 for(const c of cs){c.mentions=[];cmap[c.id]=c;if(res[c.hadith_id])res[c.hadith_id].chains.push(c);}
 const ms=await sql`select chain_id,position,surface_ar from chain_mentions where chain_id in ${sql(cs.map(c=>c.id))} and retired_at is null order by chain_id,position`;
 for(const m of ms) cmap[m.chain_id].mentions.push([m.position,m.surface_ar]);
 fs.writeFileSync(out,JSON.stringify({fetched_at:new Date().toISOString(),rows:res}));
 console.log(hs.length,cs.length,ms.length);
 await sql.end();})();
