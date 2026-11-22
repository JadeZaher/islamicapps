const d=require('./sunni_diff2.json');const {toks}=require('./lib.cjs');
const c={},cd={};
for(const [h,ch,p,o,n] of d.trim){const T=new Set(toks(n));toks(o).filter(t=>!T.has(t)).forEach(t=>c[t]=(c[t]||0)+1);}
console.log('TRIM removed tokens:',Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,60).map(x=>x.join(':')).join(' '));
for(const [h,ch,p,o] of d.drop){toks(o).forEach(t=>cd[t]=(cd[t]||0)+1);}
console.log('DROP tokens:',Object.entries(cd).sort((a,b)=>b[1]-a[1]).slice(0,50).map(x=>x.join(':')).join(' '));
