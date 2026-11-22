// Re-test every row of round2/regressions.jsonl against production now. Read-only. Writes regress_now.json
const fs=require('fs'),path=require('path');
const pg=require('postgres');const postgres=pg.default||pg;const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30,idle_timeout:20});
const rows=fs.readFileSync(path.join(__dirname,'..','round2','regressions.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const nz=s=>(s||'').replace(/[ً-ٰٟـ]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه').replace(/\s+/g,' ').trim();
(async()=>{
 const out=[];
 for(const r of rows){
  const h=r.hadith_id;
  const ch=await sql`select c.id,c.branch,c.suspension,(select string_agg(m.surface_ar,' > ' order by m.position) from chain_mentions m where m.chain_id=c.id and m.retired_at is null) s from chains c where c.hadith_id=${h} and c.retired_at is null order by c.branch`;
  const [hh]=await sql`select retired_at,split_confidence,left(coalesce(sanad_ar,text_ar),260) t from hadiths where id=${h}`;
  let status='?';let detail='';
  const joined=nz(ch.map(c=>c.s).join(' | '));
  if(r.kind==='chain_lost_written_chain_present'||r.kind==='chain_lost'){status=ch.length?'now_has_chain':'still_no_chain';}
  else if(r.kind==='name_lost_by_trim'){
   const lost=nz(r.evidence.lost_words||'');
   if(!lost)status='unknown';
   else{const toks=lost.split(' ').filter(t=>t.length>1);const hit=toks.length&&toks.every(t=>joined.includes(t));status=hit?'name_now_present':'name_still_absent';detail=lost;}
  } else {status='manual';}
  out.push({kind:r.kind,lane:r.lane,hadith_id:h,chain_id:r.chain_id,status,detail,retired:!!(hh&&hh.retired_at),conf:hh&&hh.split_confidence,text:hh&&hh.t,now:ch.slice(0,6).map(c=>'b'+c.branch+(c.suspension?'['+c.suspension+']':'')+': '+c.s),n_chains:ch.length,evidence:r.evidence});
 }
 fs.writeFileSync(path.join(__dirname,'regress_now.json'),JSON.stringify(out,null,1));
 const c={};out.forEach(o=>{const k=o.kind+' / '+o.status;c[k]=(c[k]||0)+1;});console.log(c);
 await sql.end();})().catch(e=>{console.error(e.message);process.exit(1)});
