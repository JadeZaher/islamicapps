// Run: node --test datasets/hadith-data/chain-audit/ibadi-zaydi/test_detectors.cjs
// Each detector must fire on a confirmed real report (fixtures/confirmed_examples.json, extracted from production by make_fixtures.cjs),
// and legitimate shapes (mursal of Jabir, balagha, a clean Abu Ubayda chain) must raise no structural detector.
const test=require('node:test');
const assert=require('node:assert');
const fs=require('fs');
const path=require('path');
const {detectAll,align}=require('./detectors.cjs');
const {fold}=require('./lib.cjs');

const fx=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures','confirmed_examples.json'),'utf8'));

function contextFor(ids,mutate){
  const hadiths=[],byHadith=new Map();
  for(const id of ids){
    const rec=fx.hadiths[id];hadiths.push(rec.hadith);
    byHadith.set(id,rec.chains.map(c=>({...c,mentions:c.mentions.map(m=>({...m}))})));
  }
  if(mutate)mutate(byHadith);
  return {d:{hadiths},byHadith,nar:new Map(Object.entries(fx.narrators))};
}
function hitsFor(exampleKey,mutate){
  const id=fx.examples[exampleKey];
  const parent=fx.hadiths[id].hadith.sanad_inherits_from;
  const ids=[id].concat(parent&&fx.hadiths[parent]?[parent]:[]);
  const res=detectAll(contextFor(ids,mutate)).find(r=>r.hadith_id===id);
  return res.hits;
}

// detector id -> [example key, expected hit kind]; every entry is a confirmed real report adjudicated against an online text (sample_check.csv)
const REAL={
  D1a:['D1a','opener_as_narrator'],D1b:['D1b','inherited_chain_missing'],D1c:['D1c','undeclared_continuation'],D2b:['D2b','prophet_as_mention'],
  D2c:['D2c','compiler_as_mention'],D3a:['D3a','relation_as_mention'],D3b:['D3b','not_a_narrator'],D3c:['D3c','not_a_narrator'],D3d:['D3d','not_a_narrator'],
  D3e:['D3e','merged_names'],D3f:['D3f','other'],D3g:['D3g','not_a_narrator'],D3h:['D3h','not_a_narrator'],D3i:['D3i','not_a_narrator'],D3j:['D3j','other'],
  D3k:['D3k','not_a_narrator'],D4a:['D4a','misidentified'],D4c:['D4c','same_narrator_twice'],D5a:['D5a','missing_chain'],D5c:['D5c','inheriting_no_chain'],
  D5d:['D5d','low_confidence_chain'],D6a:['D6a','other'],D6b:['D6b','missing_chain'],D6c:['D6c','other'],D6d:['D6d','other']
};
for(const [det,[key,kind]] of Object.entries(REAL)){
  test(`${det} fires on the confirmed real report ${fx.examples[key].split(':').pop().split('|')[0]}`,()=>{
    const hits=hitsFor(key);
    assert.ok(hits.some(h=>h.det===det&&h.kind===kind),`${det}/${kind} not in ${JSON.stringify(hits.map(h=>h.det))}`);
  });
}

test('legitimate shapes raise no structural detector (mursal of Jabir, balagha, clean chain, clean Zayd chain)',()=>{
  const structural=/^(?:D1|D2a|D2b|D3[b-k]|D4c|D5a|D5c|D6)/;
  for(const key of ['NEG_mursal','NEG_balagha','NEG_clean','NEG_zayd']){
    const bad=hitsFor(key).filter(h=>structural.test(h.det));
    assert.deepStrictEqual(bad.map(h=>h.det),[],`${key} wrongly flagged`);
  }
});

// Detectors with no real hit in production (0 on all 1,901 reports): exercised by mutating a real chain.
test('D2a (order_reversed) has no real hit; a reversed copy of a real chain is caught, the real one is clean',()=>{
  assert.deepStrictEqual(hitsFor('NEG_clean').filter(h=>h.det==='D2a'),[]);
  const reversed=hitsFor('NEG_clean',by=>{const id=fx.examples.NEG_clean;for(const c of by.get(id)){c.mentions.reverse();c.mentions.forEach((m,i)=>m.position=i);}});
  assert.ok(reversed.some(h=>h.det==='D2a'));
});
test('D4b (resolved narrator shares no name token) caught on a mutated real identity',()=>{
  const hits=hitsFor('D4a',by=>{const id=fx.examples.D4a;by.get(id)[0].mentions.find(m=>m.narrator_id).surface_ar='سليمان بن داود';});
  assert.ok(hits.some(h=>h.det==='D4b'));
});
test('D5b (chain stored where none is written) caught when sanad_ar is empty',()=>{
  const id=fx.examples.NEG_clean;const rec=fx.hadiths[id];
  const ctx=contextFor([id]);ctx.d.hadiths[0]={...rec.hadith,sanad_ar:''};
  const res=detectAll(ctx)[0];
  assert.ok(res.hits.some(h=>h.det==='D5b'));
});

test('alignment keeps written order on a real chain (position 0 nearest the compiler)',()=>{
  const id=fx.examples.NEG_clean;
  const chain=fx.hadiths[id].chains[0].mentions;
  const ix=align(fold(fx.hadiths[id].hadith.text_ar),chain).map(x=>x.at);
  assert.ok(ix.every((v,i)=>v>=0&&(i===0||v>ix[i-1])),JSON.stringify(ix));
});
