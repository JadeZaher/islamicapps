// Trimmed mentions whose removed tail holds a named person that no mention of the hadith still carries.
const d=require('./sunni_diff2.json');const {toks}=require('./lib.cjs');const fs=require('fs');
const V=new Set(['سمعا','سمعوا','سمعت','سمعنا','حدثتني','حدثني','حدثنا','اخبرني','اخبرنا','اخبرته','اخبره','يحدث','يخبر','يحدثنا','حدثه','انهما','انهم','قال','قالا','يقول','سمع','فقال','فذكر','سئل','سالت','سالته','وحدثني','يرويه','يروي','حدثتنا','اخبرتني','ذكره']);
const F=new Set('بهذا الاسناد كلاهما كلهم نحوه مثله الحديث هذا في احدهما غير او حديث حديثه باسناده الا بمعناه بمثل بمعني مثل زاد الي من الخبر معناه ثم معني قوله فنهاه بنحو سواء حديثهم اما الاخر ر بمثله اللفظ يحدث يخبر المعني المعنى بمعنى بمثل الذي'.split(' '));
// new surfaces per hadith from the database is unavailable here; use projection m3 via a cached file
const m3=JSON.parse(fs.readFileSync('m3_surfaces.json','utf8'));
const out=[];
for(const [h,ch,p,o,n,nch] of d.trim){
  const O=toks(o),N=toks(n);let i=-1;for(let j=0;j+N.length<=O.length;j++){if(N.every((t,k)=>O[j+k]===t)){i=j;break;}}
  if(i<0)continue;const rem=[...O.slice(0,i),...O.slice(i+N.length)];
  // a verb followed by name tokens
  const k=O.slice(i+N.length).findIndex(t=>V.has(t));if(k<0)continue;
  const after=O.slice(i+N.length+k+1).filter(t=>!F.has(t)&&!V.has(t)&&!/^(رسول|الله|النبي|ا?بي|ابا|ابو|ان)$/.test(t));
  if(!after.length)continue;
  const have=new Set((m3[h]||[]).flatMap(s=>toks(s)));
  if(after.every(t=>have.has(t)))continue;
  out.push({h,chain:nch,old:o,new:n,lost:after.join(' ')});
}
fs.writeFileSync('lost_names.json',JSON.stringify(out));console.log('trimmed rows losing a named person:',out.length,'of',d.trim.length);
for(const r of out.slice(0,0));
