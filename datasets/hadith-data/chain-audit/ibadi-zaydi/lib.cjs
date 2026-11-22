// Shared loader for the ibadi-zaydi audit: hadith -> chains -> ordered mentions. Cache path in env IZ_CACHE.
const fs=require('fs');
const SCR='C:/Users/atooz/AppData/Local/Temp/claude/8b9ecadf913d98e6/95b7dde3-527e-49ce-8f56-83c964db48b2/scratchpad/iz_cache.json';
const work=id=>id.match(/openiti:\w+:(\w+?)_/)[1];
function fold(s){return (s||'').normalize('NFKC').replace(/[\u064B-\u065F\u0670\u0640]/g,'').replace(/[إأآٱ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه').replace(/[.,:;،؛؟?!«»"'()\[\]{}\-–—_*|<>=\/\\]/g,' ').replace(/\s+/g,' ').trim();}
function load(){
  const d=JSON.parse(fs.readFileSync(process.env.IZ_CACHE||SCR,'utf8'));
  const nar=new Map(d.narrators.map(n=>[n.id,n]));
  const hid=new Map(d.hadiths.map(h=>[h.id,h]));
  const chains=new Map(d.chains.map(c=>[c.id,{...c,mentions:[]}]));
  for(const m of d.mentions){const c=chains.get(m.chain_id); if(c)c.mentions.push(m);}
  for(const c of chains.values())c.mentions.sort((a,b)=>a.position-b.position);
  const cands=new Map(); for(const c of d.cands){(cands.get(c.mention_id)||cands.set(c.mention_id,[]).get(c.mention_id)).push(c);}
  const byHadith=new Map(); for(const c of chains.values()){(byHadith.get(c.hadith_id)||byHadith.set(c.hadith_id,[]).get(c.hadith_id)).push(c);}
  for(const l of byHadith.values())l.sort((a,b)=>a.branch-b.branch);
  return {d,nar,hid,chains,cands,byHadith};
}
module.exports={load,fold,work};
