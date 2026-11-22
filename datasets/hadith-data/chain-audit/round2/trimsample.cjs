const d=require('./sunni_diff.json');const {toks}=require('./lib.cjs');const crypto=require('crypto');
const NAME=new Set(['بن','ابي','عبد','سعيد','ابو','هريرة','محمد','علي','يحيي','الله','سلمة','زهير','نمير','بكر','ابن']);
const rows=d.trimmed.map(x=>({x,rem:toks(x[4]).filter(t=>!new Set(toks(x[5])).has(t))}));
const nm=rows.filter(r=>r.rem.some(t=>NAME.has(t)));
console.log('trimmed with name-ish tokens removed:',nm.length,'of',rows.length);
const pick=(arr,n,seed)=>arr.map(a=>[crypto.createHash('md5').update(seed+a.x[0]).digest('hex'),a]).sort((a,b)=>a[0]<b[0]?-1:1).slice(0,n).map(a=>a[1]);
for(const r of pick(nm,25,'r2nm'))console.log(r.x[0].replace('mention:',''),'|',r.x[4],'=>',r.x[5]);
