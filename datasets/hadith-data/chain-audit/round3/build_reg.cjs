// Merges my re-judgment of round2/regressions.jsonl into regressions.jsonl and writes regress_rejudge.tsv. No DB access.
const fs=require('fs'),path=require('path');const d=__dirname;
const now=require('./regress_now.json');const pick=require('./pick60.json');
const lenient=new Set(['hadith:k6:13603','hadith:k6:14152','hadith:k6:30978','hadith:k6:31291','hadith:pure-canon:pc_33025','hadith:pure-canon:pc_24900','hadith:pure-canon:pc_45473']);
// my reading of the random 60 (index in pick60.json): defect = row is "fixed" mechanically but the report is still wrong
const defect60={19:'name «غبطة» is back but the chain stops there: «حدثتني عمتي أم الحسن، عن جدتها، عن عائشة» not stored',41:'«قال: قالت عائشة»: chain [أبو عبيدة > جابر بن زيد > ت], عائشة lost, verb remnant «ت» is a link',43:'«قال أبو عبيدة: بلغني عن سعيد بن جبير، قال: قال ابن عباس»: only [أبو عبيدة]',45:'«عن ابن عباس قال: قال بلال: حدثني أبو بكر الصديق»: بلال and أبو بكر not stored',50:'k6:21409 now holds the commentary «وسألت محمدا ... حدثنا سليمان بن حرب» as the chain, the source sanad chain (الدورقي > هشيم > ...) is still absent',51:'«عن جابر بن زيد قال عبادة بن الصامت قال: بايعنا»: عبادة not stored',52:'«بلغني عن عروة بن الزبير قال: قالت لي أم سلمة»: أم سلمة not stored',56:'«عن جابر بن زيد عن عن أبي سعيد الخدري» (doubled «عن»): أبو سعيد not stored'};
const minor60={11:'«حدثني جملة من أصحاب النبي»: the collective not stored',13:'«بلغني عن رجل من الصحابة»: not stored'};
const openManual={'hadith:k6:4018':'one flattened chain «.. نافع > موسى بن إسماعيل > جويرية > نافع», Ibn Umar not stored','hadith:k6:14123':'b0 «قتيبة > يعقوب > عبد العزيز» joins two routes; b2 «قتيبة > قتيبة» duplicate','hadith:k6:10412':'b0 «.. عبد الله بن نمير > أبي > عبيد الله»: «أبي» (Ibn Numayr\'s father, second route) shared into the first route','hadith:k6:19178':'b1 «.. نوح بن ربيعة > جده > جده», b2 «جده من قبل أمه أبو ذباب > جده»: «إياس وجده عن جده» still mis-parsed','hadith:k6:21409':'chain «وسألت محمدا > سليمان بن حرب > حماد بن زيد» is the commentary, not the report isnad'};
const sameNonName=new Set(['hadith:k6:14168','hadith:k6:18828','hadith:k6:32457','hadith:k6:6864']);
const rows=[];const tsv=['kind\thadith_id\tmechanical_status\tmy_verdict\tnote'];
const pickKey=new Set(pick.map(p=>p.hadith_id+'|'+p.kind+'|'+(p.detail||'')));
now.forEach(x=>{
 let verdict,note='';
 const key=x.hadith_id+'|'+x.kind+'|'+(x.detail||'');
 if(x.status==='name_still_absent'&&!lenient.has(x.hadith_id)){verdict='already_correct';note='lost words are not a narrator name (aside, matn, «فذكر حديثا»)'+(sameNonName.has(x.hadith_id)?'; BUT another link of the chain is a non-narrator now':'');}
 else if(x.status==='manual'||x.kind==='chain_lost'){verdict=openManual[x.hadith_id]?'still_open':'fixed';note=openManual[x.hadith_id]||'now reads correctly';}
 else if(x.status==='still_no_chain'){verdict='still_open';note='written isnad, no chain stored (fixer: owner decision)';}
 else{verdict='fixed_unread';}
 const pi=pick.findIndex(p=>p.hadith_id+'|'+p.kind+'|'+(p.detail||'')===key);
 if(pi>=0&&verdict==='fixed_unread'){verdict=defect60[pi]?'fixed_but_still_wrong':'fixed_confirmed';note=defect60[pi]||minor60[pi]||'';}
 tsv.push([x.kind,x.hadith_id,x.status,verdict,note].join('\t'));
 if(verdict==='still_open'||verdict==='fixed_but_still_wrong'||(verdict==='already_correct'&&sameNonName.has(x.hadith_id)))rows.push({source:'round2 regressions.jsonl re-judged now',lane:x.lane,chain_id:x.chain_id,hadith_id:x.hadith_id,kind:x.kind,verdict,evidence:{note,now:x.now.slice(0,3)}});
});
fs.writeFileSync(path.join(d,'regress_rejudge.tsv'),tsv.join('\n')+'\n');
const base=fs.readFileSync(path.join(d,'_reg_main_pop.jsonl'),'utf8').trim().split('\n').filter(Boolean);
fs.writeFileSync(path.join(d,'regressions.jsonl'),base.concat(rows.map(r=>JSON.stringify(r))).join('\n')+'\n');
const c={};tsv.slice(1).forEach(l=>{const p=l.split('\t');c[p[0]+' / '+p[3]]=(c[p[0]+' / '+p[3]]||0)+1;});console.log(c,'rows',base.length+rows.length);
