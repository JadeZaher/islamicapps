// Detectors for the ibadi/zaydi/rida chain audit. Each detector inspects one report (hadith + stored chains + mentions) and adds hits.
// Position convention: 0 = nearest the compiler, last = nearest the Prophet; written order of the text must match.
// JS \b is ASCII-only, so word ends are written (?![ء-ي]) (see memory note js-python-word-boundary-arabic).
const {load,fold,work}=require('./lib.cjs');
const DET_DEFAULT='C:/Users/atooz/AppData/Local/Temp/claude/8b9ecadf913d98e6/95b7dde3-527e-49ce-8f56-83c964db48b2/scratchpad/det.json';
const END='(?![ء-ي])';

const OPENER_ANY=new RegExp('^(?:و?بهذا (?:السند|الاسناد)|و?باسناده|و?بسنده|و?بالسند|و?بالاسناد|و?من طريقه|و?من طريق'+END+')');
const RELATION=/^(?:ابيه|ابائه|اباءه|جده|اجداده|ابوه|ابيها|ابي|ابويه|جدها)$/;
const FRAME_ONLY=/^(?:قال|قالت|قلت|وقال|فقال|حدثني|حدثنا|اخبرني|اخبرنا|عنه|عن|المذكور|قال رسول الله|رسول الله)$/;
const HONORIFIC_TAIL=/(?:^| )(?:كرم الله|رضي الله|عليه السلام|عليهم السلام|صلي الله|صلى الله)(?: |$)/;
const MATN_WORDS=/(?:^| )(?:فقال|فقلت|قلت|يقطع|تفسد|يجب|يجزئه|يصرف|لا يجد|ايام|سئل|بلغني|يقول|تقول)(?: |$)/;
const PROPHET=/^(?:النبي|النبيء|رسول الله|محمد رسول الله|عن النبي)(?: |$)/;
const PROPHET_ATTR=/(?:عن|قال) (?:النبيء?|رسول الله)|(?:النبيء?|رسول الله) (?:صلي|صلى) الله|قال (?:النبيء?|رسول الله)/;
const SPEAKER_FUSED=/^(?:و?سالت|و?سئل|و?قلت|قال|قالت) \S/;
const SPEAKER_OK=new RegExp('^قال (?:ابو|ابن|علي|زيد|جابر|الربيع)'+END);
const FRAME_FUSED=new RegExp('^(?:جابر|الربيع|ابو عبيده|جابر بن زيد|الربيع بن حبيب|عايشه|عائشه)'+END+'.* (?:بلغني|سئل|سال|انها|انه)'+END);

// Align each mention's surface to the written text; return per-mention {at, anywhere} indexes in folded text.
function align(textFold, mentions){
  let cursor=0;const idx=[];
  for(const m of mentions){
    const s=fold(m.surface_ar).replace(/^و(?=\S)/,'');
    const toks=s.split(' ').filter(Boolean);
    let at=-1;
    for(const n of [toks.length,4,3,2,1]){
      if(n>toks.length||n<1)continue;
      const key=toks.slice(0,n).join(' ');
      if(key.length<3)continue;
      const i=textFold.indexOf(key,cursor);
      if(i>=0){at=i;break;}
    }
    let anywhere=-1;
    if(at<0){for(const n of [toks.length,3,2]){if(n>toks.length||n<1)continue;const key=toks.slice(0,n).join(' ');if(key.length<4)continue;const i=textFold.indexOf(key);if(i>=0){anywhere=i;break;}}}
    idx.push({at,anywhere});
    if(at>=0)cursor=at+1;
  }
  return idx;
}

function detectAll(ctx){
  const {d,byHadith,nar}=ctx;
  const out=[];
  const narName=id=>fold((nar.get(id)||{}).name_ar||'');
  for(const h of d.hadiths){
    const w=work(h.id); const chains=byHadith.get(h.id)||[];
    const tf=fold(h.text_ar);
    const head=fold(h.sanad_ar||h.text_ar.slice(0,260));
    const hits=[]; const add=(det,kind,extra)=>hits.push({det,kind,...extra});
    const startsOpener=OPENER_ANY.test(tf);
    // D1 continuation openers
    for(const c of chains)for(const m of c.mentions){
      const s=fold(m.surface_ar);
      if(OPENER_ANY.test(s)||(h.sanad_inherits_from&&m.position===0&&FRAME_ONLY.test(s)))
        add('D1a','opener_as_narrator',{mention:m.id,chain:c.id,surface:m.surface_ar});
    }
    if(h.sanad_inherits_from){
      const parentChains=byHadith.get(h.sanad_inherits_from)||[];
      const mine=chains.flatMap(c=>c.mentions.map(m=>fold(m.surface_ar)));
      const parentSet=new Set(parentChains.flatMap(c=>c.mentions.map(m=>fold(m.surface_ar))));
      const inherited=mine.filter(s=>parentSet.has(s)).length;
      const edgeable=chains.some(c=>c.mentions.filter(m=>!OPENER_ANY.test(fold(m.surface_ar))&&!FRAME_ONLY.test(fold(m.surface_ar))).length>=2);
      if(!inherited||!edgeable)add('D1b','inherited_chain_missing',{inherits:h.sanad_inherits_from,parent_mentions:parentChains.reduce((a,c)=>a+c.mentions.length,0),own_mentions:mine.length});
    } else if(startsOpener){
      add('D1c','undeclared_continuation',{opener:tf.slice(0,40)});
    }
    // D2 order, prophet-first, compiler
    for(const c of chains){
      const ix=align(tf,c.mentions);
      let prev=-1;
      c.mentions.forEach((m,i)=>{
        const a=ix[i];
        if(a.at>=0){ if(a.at<prev) add('D2a','order_reversed',{mention:m.id,chain:c.id}); prev=Math.max(prev,a.at);}
        else if(a.anywhere>=0 && ix.slice(0,i).some(x=>x.at>a.anywhere)) add('D2a','order_reversed',{mention:m.id,chain:c.id,note:'found before cursor'});
      });
      const prophetPos=c.mentions.findIndex(m=>PROPHET.test(fold(m.surface_ar)));
      if(prophetPos>=0)add('D2b','prophet_as_mention',{mention:c.mentions[prophetPos].id,position:prophetPos,of:c.mentions.length,first:prophetPos===0});
      c.mentions.forEach(m=>{
        const s=fold(m.surface_ar);
        if(w==='rabi'&&new RegExp('(^| )الربيع'+END).test(s)&&!/ابو عبيده/.test(s))add('D2c','compiler_as_mention',{mention:m.id,position:m.position,surface:m.surface_ar});
        if(w==='zayd'&&/^(?:\(?حدثني\)? )?ابو خالد/.test(s))add('D2c','compiler_as_mention',{mention:m.id,position:m.position,surface:m.surface_ar});
        if(w==='rabi'&&/الربيع/.test(s)&&/ابو عبيده/.test(s))add('D3e','merged_names',{mention:m.id,position:m.position,surface:m.surface_ar,why:'compiler opener fused with Abu Ubayda'});
      });
    }
    // D3 relation / not a narrator / collectives / matn
    for(const c of chains)for(const m of c.mentions){
      const s=fold(m.surface_ar); const nw=s.split(' ').length;
      if(OPENER_ANY.test(s))continue; // counted by D1a
      if(RELATION.test(s))add('D3a','relation_as_mention',{mention:m.id,position:m.position,surface:m.surface_ar,resolved:!!m.narrator_id});
      else if(FRAME_ONLY.test(s))add('D3b','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'frame word'});
      else if(/^(?:و?جهه|و?جوه|و?جهي)(?: |$)/.test(s))add('D3g','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'orphan honorific fragment (كرم الله وجهه split on waw), usually with matn attached'});
      else if(/^(?:لو|ان|ما|لا|من|في|الي|هو|هذا|هذه|كان|ثم|قد|اذا|فان|اني|انا)$/.test(s))add('D3k','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'function word left by splitting a matn word on waw (e.g. «ولو»)'});
      else if(/(?:^| )(?:و?سالت|و?سالته|و?سئل)(?: |$)/.test(s))add('D3i','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'question frame (سألت/سئل) in the middle of the surface'});
      else if(/^(?:وعن|وكان|كان) /.test(s))add('D3j','other',{mention:m.id,position:m.position,surface:m.surface_ar,why:'connector وعن kept inside the surface'});
      else if(/(?:^| )(?:في )?قول(?:ه|ك)?(?: الله)? (?:تعالي|عزوجل|عز وجل)|(?:^| )في قول(?:ه|ك)?(?: |$)/.test(s))add('D3h','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'Quran citation formula (في قوله تعالى) stored as or fused into a narrator'});
      else if(HONORIFIC_TAIL.test(s))add('D3c','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'honorific kept in name'});
      else if((SPEAKER_FUSED.test(s)&&!SPEAKER_OK.test(s))||/^(?:و?سالت|و?سئل|و?قلت)/.test(s))add('D3d','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'frame verb (سألت/سئل/قال) fused with a name'});
      else if(/امير المؤمنين \S+ بن/.test(s))add('D3e','merged_names',{mention:m.id,position:m.position,surface:m.surface_ar,why:'two narrators fused in one surface'});
      else if(FRAME_FUSED.test(s)||/ (?:انه|انها|انهما)(?: |$)/.test(s))add('D3f','other',{mention:m.id,position:m.position,surface:m.surface_ar,why:'name fused with a frame word (بلغني/سئل/أنها)'});
      else if((nw>=5&&!/(?:^| )(?:بن|ابن|ابو|ابي|ام|عبد)(?: |$)/.test(s))||(nw>=3&&MATN_WORDS.test(s)&&!/(?:^| )(?:بن|ابن)(?: |$)/.test(s)))
        add('D3d','not_a_narrator',{mention:m.id,position:m.position,surface:m.surface_ar,why:'matn words captured as a narrator'});
    }
    for(const c of chains){
      const seen=new Map();
      for(const m of c.mentions){const k=m.narrator_id||fold(m.surface_ar);if(seen.has(k)&&!RELATION.test(fold(m.surface_ar)))add('D4c','same_narrator_twice',{mention:m.id,first:seen.get(k),surface:m.surface_ar});seen.set(k,m.id);}
    }
    // D4 identity vs surface
    for(const c of chains)for(const m of c.mentions){
      if(!m.narrator_id)continue;
      const s=fold(m.surface_ar), n=narName(m.narrator_id);
      const keep=t=>t.length>=2&&!['بن','ابن','بنت','ابو','ابي'].includes(t);
      const st=new Set(s.split(' ').filter(keep)), nt=new Set(n.split(' ').filter(keep));
      let ov=0;for(const t of st)if(nt.has(t))ov++;
      const kunyaOnly=/^(?:ابو|ابي|ابن) \S+$/.test(s);
      const info={mention:m.id,surface:m.surface_ar,narrator:m.narrator_id,narrator_name:(nar.get(m.narrator_id)||{}).name_ar,basis:m.resolution_basis};
      if(/^ابو عبيده$/.test(s)&&w==='rabi'&&!/ابي كريمه/.test(n))
        add('D4a','misidentified',{...info,why:'Abu Ubayda (named Muslim b. Abi Karima in the work) resolved to a different patronymic'});
      else if(/^جابر بن عبد الله/.test(n)&&/^جابر( بن زيد)?$/.test(s))add('D4a','misidentified',{...info,why:'Jabir b. Zayd surface resolved to Jabir b. Abd Allah'});
      else if(ov===0&&!kunyaOnly&&/(?:^| )بن(?: |$)/.test(s))add('D4b','misidentified',{...info,why:'no shared name token'});
    }
    // D6 chain stops before the Prophet attribution although more links are written
    for(const c of chains){
      if(!c.mentions.length)continue;
      const last=c.mentions[c.mentions.length-1];
      const ix=align(tf,c.mentions);const lastIdx=ix[ix.length-1].at;
      if(lastIdx<0)continue;
      const rest=tf.slice(lastIdx+fold(last.surface_ar).length);
      const pm=PROPHET_ATTR.exec(rest);
      if(!pm)continue;
      const seg=rest.slice(0,pm.index);
      if(seg.length<400&&/(?:^| )(?:حدثني|حدثنا) |(?:^| )عن \S/.test(seg)&&!/[«"]/.test(seg))add('D6a','other',{chain:c.id,why:'links written after the last stored mention',missed:seg.slice(0,120)});
    }
    // D6c/D6d: a Companion named after «قال:», or the last link after «عن جده» (Ali) missing
    for(const c of chains){
      if(!c.mentions.length)continue;
      const last=c.mentions[c.mentions.length-1];
      const ix=align(tf,c.mentions);const lastIdx=ix[ix.length-1].at;
      if(lastIdx<0)continue;
      const rest=tf.slice(lastIdx+fold(last.surface_ar).length);
      if(/^ (?:قال |انه قال )?قال (?:ابو|ابن|ابي|عبد|ام|عايشه|عائشه|انس|جابر|عمر|علي|عثمان|سعد|زيد|عمران|معاذ|ابوه) /.test(rest)&&/^جابر|^زيد|ابو عبيده|ابو خالد/.test(fold(last.surface_ar))&&!/[«"]/.test(rest.slice(0,8)))
        add('D6c','other',{chain:c.id,why:'a Companion named after قال is not stored',missed:rest.slice(0,60)});
      if(RELATION.test(fold(last.surface_ar))&&/^(?: ع م)? عن \S/.test(rest))add('D6d','other',{chain:c.id,why:'link after «جده» (usually Ali) written but not stored',missed:rest.slice(0,50)});
    }
    if(w==='rida'&&/rida_0001\|/.test(h.id)&&!chains.some(c=>c.mentions.some(m=>/علي بن موسي/.test(fold(m.surface_ar)))))
      add('D6b','missing_chain',{why:'the Imam chain (Ali b. Musa al-Rida back to Ali b. Abi Talib) written in rida_0001 is not stored; all inheriting reports lose it'});
    // D5 missing / spurious chain
    const writtenChain=/(?:حدثني|حدثنا|اخبرني|اخبرنا|سمعت|^(?:قال )?(?:الربيع|ابو عبيده|زيد بن علي)|(?:^| )عن .+ عن )/.test(head);
    if(chains.length===0&&writtenChain&&!h.sanad_inherits_from)add('D5a','missing_chain',{head:head.slice(0,100),sanad_null:!h.sanad_ar});
    if(chains.length===0&&h.sanad_inherits_from)add('D5c','inheriting_no_chain',{inherits:h.sanad_inherits_from});
    if(chains.length>0&&h.sanad_ar===''&&!h.sanad_inherits_from)add('D5b','chain_without_written_chain',{n:chains.length});
    if(chains.length>0&&!h.sanad_ar&&h.split_confidence==='low')add('D5d','low_confidence_chain',{mentions:chains.reduce((a,c)=>a+c.mentions.length,0)});
    out.push({hadith_id:h.id,work:w,hits});
  }
  return out;
}
module.exports={detectAll,align,OPENER_ANY,RELATION,FRAME_ONLY};
if(require.main===module){
  const ctx=load();const res=detectAll(ctx);
  const tab={};
  for(const r of res)for(const k of new Set(r.hits.map(x=>x.det+' '+x.kind))){tab[k]=tab[k]||{rabi:0,zayd:0,rida:0};tab[k][r.work]++;}
  const mt={};for(const r of res)for(const x of r.hits){const k=x.det+' '+x.kind;mt[k]=mt[k]||{rabi:0,zayd:0,rida:0};mt[k][r.work]++;}
  console.log('REPORTS with >=1 hit per detector');console.table(tab);
  console.log('HITS (mentions/chains) per detector');console.table(mt);
  const any={rabi:0,zayd:0,rida:0};const tot={rabi:0,zayd:0,rida:0};for(const r of res){tot[r.work]++;if(r.hits.length)any[r.work]++;}
  console.log('any hit',any,'total',tot);
  require('fs').writeFileSync(process.env.IZ_DET||DET_DEFAULT,JSON.stringify(res));
}
