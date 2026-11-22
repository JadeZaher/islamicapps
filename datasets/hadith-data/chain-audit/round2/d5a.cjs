// OpenITI hadiths that lost every chain (v6 -> m3) and whose Arabic opens with a written chain (the Ibadi/Zaydi lane detector D5a).
const fs=require('fs');
const det=JSON.parse(fs.readFileSync('C:/Users/atooz/AppData/Local/Temp/claude/8b9ecadf913d98e6/95b7dde3-527e-49ce-8f56-83c964db48b2/scratchpad/det/iz_det.json','utf8'));
const lost=new Set(JSON.parse(fs.readFileSync('nochain.json','utf8')).openiti.lost);
const d5a=(Array.isArray(det)?det:det.list||Object.values(det)).filter(x=>x.hits.some(h=>h.code==='D5a'||h.det==='D5a'||(h[0]==='D5a')||JSON.stringify(h).includes('D5a')));
console.log('D5a hadiths',d5a.length,'by work',d5a.reduce((a,x)=>(a[x.work]=(a[x.work]||0)+1,a),{}),'of which lost-in-fix',d5a.filter(x=>lost.has(x.hadith_id)).length);
fs.writeFileSync('d5a_hadiths.json',JSON.stringify(d5a.map(x=>({hadith_id:x.hadith_id,work:x.work,lost_in_fix:lost.has(x.hadith_id),hit:x.hits.find(h=>JSON.stringify(h).includes('D5a'))}))));
console.log(JSON.stringify(d5a[0]).slice(0,300));
