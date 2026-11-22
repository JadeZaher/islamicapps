// Random 60 of the rows judged fixed (mechanical test) from regress_now.json; seeded.
const fs=require('fs'),crypto=require('crypto');
const a=require('./regress_now.json');
const lenient=new Set(['hadith:k6:13603','hadith:k6:14152','hadith:k6:30978','hadith:k6:31291','hadith:pure-canon:pc_33025','hadith:pure-canon:pc_24900','hadith:pure-canon:pc_45473']);
const fixed=a.filter(x=>x.status==='name_now_present'||x.status==='now_has_chain'||(x.status==='name_still_absent'&&lenient.has(x.hadith_id)));
const man=a.filter(x=>x.status==='manual');
const rank=x=>crypto.createHash('md5').update(x.hadith_id+x.kind+(x.detail||'')+'r3pick').digest('hex');
const pick=fixed.sort((p,q)=>rank(p)<rank(q)?-1:1).slice(0,60);
fs.writeFileSync('pick60.json',JSON.stringify(pick.map(x=>({kind:x.kind,hadith_id:x.hadith_id,detail:x.detail})),null,1));
const nz=s=>(s||'').replace(/[ً-ٰٟ]/g,'');
pick.forEach((x,i)=>{
 console.log('#F'+i,x.kind.replace('chain_lost_written_chain_present','chain_back').replace('name_lost_by_trim','name'),x.hadith_id,x.detail?'lost=«'+x.detail+'»':'','n='+x.n_chains);
 console.log(' T:',nz(x.text).replace(/\s+/g,' ').slice(0,190));
 const show=x.kind==='name_lost_by_trim'?x.now.filter(l=>l.includes((x.detail||'').split(' ')[0].replace(/ا$/,'').slice(0,4))).slice(0,2):x.now.slice(0,2);
 (show.length?show:x.now.slice(0,2)).forEach(l=>console.log('  '+l.slice(0,190)));
});
