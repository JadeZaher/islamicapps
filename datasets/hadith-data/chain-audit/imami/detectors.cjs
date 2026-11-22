// Imami chain detectors. Each takes the loaded context and returns findings; see README.md for rules.
const {fold}=require('./lib.cjs');

const IMAM_TOKEN=/^(و ?)?(ابي|ابا|ابو) (عبد الله|جعفر|الحسن|ابراهيم)( (الاول|الثاني|الثالث|الماضي|الرضا|موسي|الصادق|الباقر|الكاظم|العسكري|الهادي|الجواد|الاخير|ع|عليه السلام|جعفر بن محمد|محمد بن علي|علي بن موسي|محمد|علي))*$|^(و ?)?(الصادق|الباقر|الكاظم|الرضا|الجواد|الهادي|العسكري|السجاد|امير المؤمنين|احدهما|ابائه|ابيه|جده|ابائي|رسول الله|النبي)( |$)|^(و ?)?(ابو جعفر|ابو عبد الله) (الصادق|الباقر)?( ع)?$/;
const IMAM_FINAL_CONT=/^(ابيه|ابائه|جده|ابائي|رسول الله|النبي|امير المؤمنين|علي|ابي|ابيه ع|ابائه ع)( |$)|^(ابي|ابا|ابو) (عبد الله|جعفر|الحسن|محمد|ابراهيم)|^(الصادق|الباقر|الكاظم|الرضا|الجواد|الهادي|العسكري|السجاد)/;
const TALIQ=/^(و ?)?(عنه|عنهم|عنهما|به|بهذا|بهذه|باسناده|بالاسناد|بالاسانيد)( |$)/;
const COLLECTIVE=/^(و ?)?(عدة|عده|بعض|جماعة|جماعه|رجل|رجلا|الرجل|بعضهم|غيره|غيرهما|رجال|بعض رجاله|رجل من|شيخ|منهم)( |$)/;
const IRSAL_SUFFIX=/( رفعه| يرفعه| عمن ذكره| عمن رواه| عمن حدثه| يبلغ به| رواه| مرسلا| سماه| عن رجل| عن بعض| عن بعض اصحابه| عن بعض اصحابنا)$/;
const RELATIONAL=/^(و ?)?(ابيه|ابي|ابوه|جده|عمه|اخيه|ابائه|ابنه|خاله|اخي)$/;
const VERB_PREFIX=/^(و ?)?(روي|رواه|قال|سال|سئل|ذكر|حدثني|حدثنا|اخبرني|اخبرنا|عن|وروي)( |$)/;
const CLAUSE_WORDS=new Set('ولا ليس الا لان فقد هذا ذلك اذا فان لم ما كان كانت كانوا الذي التي ان انه انها اي حيث ثم او هو هي'.split(' '));
const FUSED_GIVEN=/ و(محمد|احمد|علي|الحسين|الحسن|ابراهيم|عبد|عبيد|سعد|عمر|يحيي|جعفر|موسي|هارون|ابي|ابن|عدة|بعض|غيره|جماعة|اخي|اخوه|ابنه|الفضل|سهل|صفوان|حماد|جميل|عثمان|القاسم)(?![ء-ي])|^و ?(محمد|احمد) بن .* و ?(محمد|احمد) /;
const STANDALONE_AND=/(^| )و ( ?)(?=\S)/;
const KULAYNI_SHAYKH=new Set(['علي بن ابراهيم','علي بن ابراهيم بن هاشم','محمد بن يحيي','عدة من اصحابنا','الحسين بن محمد','الحسين بن محمد الاشعري','ابو علي الاشعري','حميد بن زياد','محمد بن اسماعيل','احمد بن ادريس']);

function cat(surface){
  const f=fold(surface);
  if(TALIQ.test(f))return 'taliq_pronoun';
  if(/[0-9]/.test(f)&&f.split(' ').length>1&&!/^\d/.test(f))return 'footnote_digit';
  if(IRSAL_SUFFIX.test(f))return 'irsal_marked';
  if(COLLECTIVE.test(f))return 'collective_or_anonymous';
  if(RELATIONAL.test(f))return 'relational';
  if(/^(و ?)?(روي|وروي|قال|وقال|سال|سئل)( |$)/.test(f))return 'verb_prefixed';
  const toks=f.split(' ');
  if(toks.some(t=>CLAUSE_WORDS.has(t))&&toks.length>=3)return 'clause';
  if(toks.length>=12)return 'clause';
  if(FUSED_GIVEN.test(f)||/ و (محمد|احمد|علي|عبد|ابي|الحسين|الحسن|سعد|عمر|يحيي)/.test(f))return 'fused_cotransmitter';
  if(IMAM_TOKEN.test(f))return 'imam_surface';
  return 'name';
}
const isImamId=id=>!!id&&id.startsWith('narrator:imam:');
function collectionOf(L,hid){return L.hid.get(hid).collection_id.replace('collection:imami:','');}
module.exports={cat,isImamId,collectionOf,IMAM_TOKEN,IMAM_FINAL_CONT,TALIQ,KULAYNI_SHAYKH,fold};
