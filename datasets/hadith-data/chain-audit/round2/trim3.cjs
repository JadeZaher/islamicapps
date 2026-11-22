const d=require('./sunni_diff2.json');const {toks}=require('./lib.cjs');const crypto=require('crypto');
const F=new Set('بهذا الاسناد كلاهما كلهم نحوه مثله الحديث هذا في احدهما غير او حديث حديثه باسناده فذكر سمعا حدثتني نحو الا بمعناه بمثل بمعني مثل زاد الي من الخبر معناه ثم فقال معني يحدث قوله فنهاه بنحو سواء حديثهم اما الاخر يخبر ر بمثله اللفظ'.split(' '));
const pick=(arr,n,seed)=>arr.map(a=>[crypto.createHash('md5').update(seed+JSON.stringify(a)).digest('hex'),a]).sort((a,b)=>a[0]<b[0]?-1:1).slice(0,n).map(a=>a[1]);
const nt=d.trim.filter(([h,c,p,o,n])=>{const T=new Set(toks(n));return toks(o).filter(t=>!T.has(t)).some(t=>!F.has(t));});
console.log('trim with non-formula tokens removed',nt.length,'of',d.trim.length);
for(const r of pick(nt,26,'a'))console.log(r[0].replace('hadith:',''),'|',r[3],'=>',r[4]);
const dn=d.drop.filter(([h,c,p,o])=>!toks(o).some(t=>F.has(t)||/^ل/.test(t)));
console.log('drop without formula word',dn.length,'of',d.drop.length);
for(const r of pick(dn,22,'b'))console.log(r[0].replace('hadith:',''),'|',r[3]);
