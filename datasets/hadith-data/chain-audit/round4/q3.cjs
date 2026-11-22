const fs=require('fs');const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const st=s=>(s||'').replace(/[ً-ٰٟ]/g,'').replace(/\s+/g,' ').trim();
(async()=>{
const ids=JSON.parse(fs.readFileSync('sample_ids.json','utf8'));
ids.forEach((x,i)=>x.i=i);
for(const s of ids.filter(x=>/^(rabi|zayd|rida)$/.test(x.lane))){
 const [h]=await sql`select coalesce(sanad_ar,'') sa,text_ar t,sanad_inherits_from inh from hadiths where id=${s.hadith_id}`;
 const sa=st(h.sa),t=st(h.t);
 if(h.inh) {console.log('#'+s.i,'INH T:',t.slice(0,140));continue;}
 const tail=t.startsWith(sa)?t.slice(sa.length):'(!prefix) '+t.slice(0,160);
 console.log('#'+s.i,s.lane,'tail:',tail.slice(0,130));
}
await sql.end();})();
