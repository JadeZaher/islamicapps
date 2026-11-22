const d=require('./sunni_diff.json');const {toks}=require('./lib.cjs');
const c={};let nameLike=0;
for(const [k,h,ch,pos,o,n] of d.trimmed){const T=new Set(toks(n));const rem=toks(o).filter(t=>!T.has(t));rem.forEach(t=>c[t]=(c[t]||0)+1);}
const top=Object.entries(c).sort((a,b)=>b[1]-a[1]);
console.log(top.slice(0,70).map(x=>x.join(':')).join('  '));console.log('distinct removed tokens',top.length);
// new surfaces that are shorter than 1 token?
console.log('empty new',d.trimmed.filter(x=>!toks(x[5]).length).length);
