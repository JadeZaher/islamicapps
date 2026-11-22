// Shared: Arabic normalisation and surface-to-text alignment used by the round-2 auto pre-judge. Pure functions.
const norm=s=>(s||'').replace(/[ً-ْٰـ‌‍‏‎]/g,'').replace(/[أإآٱ]/g,'ا').replace(/ى/g,'ي').replace(/ۖ|‏|‏/g,'')
 .replace(/\(?\s*ع\.?\s*م\s*\)?|\(ع\)|\(ص\)|\(رض\)/g,' ')
 .replace(/صلي الله عليه و?اله و?سلم|صلي الله عليه و?سلم|عليه السلام|عليها السلام|عليهما السلام|عليهم السلام|رضي الله عنه[ما]?|رضي الله عنها|رضي الله عنهم|رحمه الله|رحمهم الله|قدس الله روحه|رضوان الله عليه|كرم الله وجهه/g,' ');
const toks=s=>norm(s).split(/[^ء-ي]+/).filter(Boolean);
const CONN=new Set(['حدثنا','حدثني','اخبرنا','اخبرني','انبانا','انبا','انبانا','قال','قالا','قالوا','قالت','عن','ان','انه','انها','سمع','سمعت','سمعنا','يقول','يحدث','يحدثنا','حدثه','حدثها','و','ثنا','نا','ا','ثني','ح','ثم','حدثتني','اخبرتني','حدثنيه','اخبرناه','حدثناه','جميعا','كلاهما','كلهم','عنه','عنها','عنهم','به','ذكر','ذكره','يعني','هو','روي','يرويه','رواه','باسناده','بالاسناد','بهذا','الاسناد','الاسنادين','مثله','نحوه','بمثله','بنحوه','ما','وعن','فيما','يرفعه','يبلغ','يبلغه','رفعه','في','من','ثنا','اياه','حدثهم','قراءه','عليه','وانا','اسمع','وهو','يسمع','اخبره','اخبرهم','سالت','سالته','سالنا','سال','وسالت','سمعته','قلت','قلنا','قيل','وقال','لي','له','لنا','كتب','كتبت','الي']);
// Locate each surface's tokens in order inside the haystack tokens; return per-gap residual tokens.
function align(hay,surfaces){
  const H=toks(hay);let cur=0;const res=[];const pos=[];
  for(let i=0;i<surfaces.length;i++){
    const S=toks(surfaces[i]);if(!S.length){pos.push(null);continue;}
    let found=-1;
    for(const from of [cur,0]){
      for(let j=from;j+S.length<=H.length;j++){let ok=true;for(let k=0;k<S.length;k++){const a=H[j+k],b=S[k];if(a!==b&&a!=='و'+b&&b!=='و'+a){ok=false;break;}}if(ok){found=j;break;}}
      if(found>=0)break;}
    if(found<0){pos.push(null);res.push({i,kind:'not_found'});continue;}
    if(found<cur)res.push({i,kind:'out_of_order'});
    // gap residual between previous end and this start (only when moving forward)
    const prevEnd=i>0&&pos[i-1]?pos[i-1].end:0;
    if(found>=prevEnd){const gap=H.slice(prevEnd,found).filter(t=>!CONN.has(t)&&!CONN.has(t.replace(/^و/,'')));if(gap.length)res.push({i,kind:'gap_before',words:gap.join(' ')});}
    pos.push({start:found,end:found+S.length});cur=found+S.length;}
  // tail window: up to first quote verb after last surface
  const last=[...pos].reverse().find(Boolean);
  if(last){const w=[];for(let j=last.end;j<Math.min(H.length,last.end+8);j++){const t=H[j];if(/^(قال|يقول|فقال|قالت|ان|انه|فقالت|ان)$/.test(t)&&w.length>=0&&j>last.end-1){ if(t==='قال'||t==='يقول'||t==='فقال')break;}
      if(!CONN.has(t)&&!CONN.has(t.replace(/^و/,''))&&!/^(رسول|الله|النبي|نبي|النبيء)$/.test(t))w.push(t);else if(w.length)break;}
    if(w.length)res.push({i:surfaces.length,kind:'tail',words:w.join(' ')});}
  return res;}
module.exports={norm,toks,align,CONN};
