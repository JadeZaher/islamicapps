// Classify each judged-defect chain as unchanged by the fix (a miss), worse (after is a strict sub-run of a before chain), or changed otherwise.
const fs=require('fs');const {toks}=require('./lib.cjs');
const D=JSON.parse(fs.readFileSync('defects.json','utf8'));const BA=JSON.parse(fs.readFileSync('before_after3.json','utf8'));
const F=new Set('و عن قال حدثنا حدثني اخبرنا ح بهذا الاسناد'.split(' '));
const out=[];const tally={};
for(const d of D){
 const side=d.lane.startsWith('sunni')?'sunni':d.lane.startsWith('imami')?'imami':null;if(!side){out.push({...d,change:'not_compared'});continue;}
 const bef=BA[side+'_before'][d.hadith_id]||{},aft=BA[side+'_after'][d.hadith_id]||{};
 const after=aft[d.chain_id];if(after===undefined){out.push({...d,change:'no_after'});continue;}
 const B=Object.values(bef);let change='changed_other',best=null;
 if(B.includes(after))change='unchanged';
 else{const A=toks(after);const set=new Set(A);
  let bestOv=-1;for(const b of B){const T=toks(b);const ov=T.filter(t=>set.has(t)).length;if(ov>bestOv){bestOv=ov;best=b;}}
  if(best){const T=toks(best);const lost=T.filter(t=>!set.has(t)&&!F.has(t));
   if(lost.length&&A.every(t=>T.includes(t)))change='worse_lost_names';
   else if(!B.length)change='new_hadith_chain';}}
 const key=side+':'+change;tally[key]=(tally[key]||0)+1;
 out.push({...d,side,change,before_best:best,before_all:B.length,after});
}
fs.writeFileSync('regress_classified.json',JSON.stringify(out));console.log(tally);
for(const o of out.filter(o=>o.change==='worse_lost_names').slice(0,12))console.log(o.lane,o.kind,'\n  BEFORE:',(o.before_best||'').slice(0,150),'\n  AFTER :',o.after.slice(0,150));
