// usage: node dump.cjs <ids.json> <from> <to> [textlen]  -> compact view of stored chains vs Arabic. Read-only.
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const nz=x=>(x||'').replace(/[ً-ْـ]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').split(/[^ء-ي]+/).filter(t=>t.length>1&&!/^(بن|ابن|ابو|ابي|ال)$/.test(t));
const tokOverlap=(a,b)=>{const B=new Set(nz(b).map(t=>t.replace(/^ال/,'')));return nz(a).some(t=>B.has(t.replace(/^ال/,'')));};
(async()=>{
 const [,,file,a,b,tl]=process.argv;const L=+tl||330;
 const ids=JSON.parse(fs.readFileSync(file,'utf8')).slice(+a,+b);
 for(let i=0;i<ids.length;i++){
  const s=ids[i];
  const [h]=await sql`select id,collection_id,hadith_no,sanad,coalesce(sanad_ar,'') sanad_ar,text_ar,split_confidence,sanad_inherits_from from hadiths where id=${s.hadith_id}`;
  const chs=await sql`select id,branch,suspension,missing_link_after from chains where hadith_id=${s.hadith_id} and retired_at is null order by branch,id`;
  let o=`#${+a+i} ${s.lane} ${s.chain_id} [${h.collection_id.split(':').pop()} ${h.hadith_no}] conf=${h.split_confidence}${h.sanad_inherits_from?' inh='+h.sanad_inherits_from:''}\n`;
  if(s.note)o+=`  N: ${s.note}
`;
  if(s.flags&&s.flags.length)o+=`  F: ${s.flags.map(f=>f.kind+(f.i!=null?'@'+f.i:'')+(f.words?'«'+f.words+'»':'')).join(' | ')}
`;
  if(s.pcsanad||/ahmad|darimi|muwatta/.test(s.coll||''))o+=`  S: ${h.sanad||''}
`;
  const san=h.sanad_ar||h.text_ar.slice(0,s.coll&&/ahmad|darimi|muwatta/.test(s.coll)?90:L);
  o+=`  T: ${san.slice(0,L).replace(/\s+/g,' ')}${san.length>L?'…':''}\n`;
  if(h.sanad_inherits_from){const [p]=await sql`select coalesce(sanad_ar,'') sanad_ar,text_ar from hadiths where id=${h.sanad_inherits_from}`;o+=`  P: ${(p.sanad_ar||p.text_ar).slice(0,L).replace(/\s+/g,' ')}\n`;
    const pc=await sql`select m.position,m.surface_ar from chain_mentions m join chains c on c.id=m.chain_id where c.hadith_id=${h.sanad_inherits_from} and c.retired_at is null and m.retired_at is null order by c.branch,m.position`;o+=`  Pchain: ${pc.map(x=>x.surface_ar).join(' > ')}\n`;}
  const MAXB=+process.env.MAXB||6;let shown=0;
  for(const c of chs){ if(c.id!==s.chain_id&&shown>=MAXB){continue;} if(c.id!==s.chain_id)shown++;
   const ms=await sql`select m.position,m.surface_ar,m.narrator_id,m.link_kind,m.resolution,m.inherited_from_mention_id inh,m.identity_withheld_reason w,n.name_ar nm from chain_mentions m left join narrators n on n.id=m.narrator_id where m.chain_id=${c.id} and m.retired_at is null order by m.position`;
   o+=`  ${c.id===s.chain_id?'*':' '}b${c.branch}${c.suspension?' susp='+c.suspension:''}${c.missing_link_after!=null?' miss@'+c.missing_link_after:''}: `+ms.map(m=>`${m.position}:${m.surface_ar}${m.narrator_id&&m.nm&&!tokOverlap(m.surface_ar,m.nm)?'{'+m.nm.slice(0,40)+'}':''}${m.link_kind&&!['narrator','person','unclassified'].includes(m.link_kind)?'<'+m.link_kind+'>':''}${m.inh?'^':''}`).join(' > ')+'\n';
  }
  if(chs.length>MAXB+1)o+=`  (${chs.length} chains total)
`;
  console.log(process.env.NODIAC?o.replace(/[ً-ٰٟ]/g,""):o);
 }
 await sql.end();})();
