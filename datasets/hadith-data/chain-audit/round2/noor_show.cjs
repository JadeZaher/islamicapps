// usage: node noor_show.cjs <noorHadithId> [production hadith id]
const fs=require('fs');const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{const [,,nid,hid]=process.argv;const d=JSON.parse(fs.readFileSync(`fetched/noor_rejal_${nid}.json`,'utf8'));
 for(const s of d.response.data.sanadList)console.log('NOOR:',s.sanad.filter(x=>x.type===0||x.type===4).map(x=>x.title).join(' > '));
 if(hid){const chs=await sql`select c.branch,string_agg(m.surface_ar,' > ' order by m.position) s from chains c join chain_mentions m on m.chain_id=c.id and m.retired_at is null where c.hadith_id=${hid} and c.retired_at is null group by c.id,c.branch order by c.branch`;chs.forEach(c=>console.log('PROD b'+c.branch+':',c.s));}
 await sql.end();})();
