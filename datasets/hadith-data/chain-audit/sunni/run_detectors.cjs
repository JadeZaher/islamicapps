// Usage: node run_detectors.cjs <cache.json> <hits_out.jsonl> -> writes detector_counts.json next to this file.
const fs=require('fs');const path=require('path');const D=require('./detectors.cjs');
const cache=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const ctx=D.prepare(cache);
const hits=D.runAll(ctx);
fs.writeFileSync(process.argv[3],hits.map(h=>JSON.stringify(h)).join('\n'));
const counts={};const bump=(o,...k)=>{let p=o;for(const x of k.slice(0,-1)){p=p[x]=p[x]||{};}p[k[k.length-1]]=(p[k[k.length-1]]||0)+1;};
for(const h of hits){bump(counts,h.detector,'by_collection',h.collection);bump(counts,h.detector,'by_extraction_method',h.extraction_method);bump(counts,h.detector,'total');}
const totals={chains:ctx.chains.size,mentions:cache.mentions.length,hadiths:cache.hadiths.length};
fs.writeFileSync(path.join(__dirname,'detector_counts.json'),JSON.stringify({totals,counts},null,1));
for(const [d,v] of Object.entries(counts)) console.log(d,v.total,JSON.stringify(v.by_collection).replace(/collection:sunni:/g,''));
