// Runs every detector on real production rows (fixtures/real_examples.json) and fails if a detector misses its confirmed example.
// Run: node datasets/hadith-data/chain-audit/imami/test_detectors.cjs
const fs=require('fs'),path=require('path'),os=require('os'),{spawnSync}=require('child_process');
const fixture=path.join(__dirname,'fixtures','real_examples.json');
const out=path.join(os.tmpdir(),'imami_detector_test_findings.json');
const r=spawnSync(process.execPath,[path.join(__dirname,'run_all.cjs')],{env:{...process.env,IMAMI_CACHE:fixture,FINDINGS:out},encoding:'utf8'});
if(r.status!==0){console.error(r.stderr);process.exit(1);}
const {F}=JSON.parse(fs.readFileSync(out,'utf8'));
const {expected}=JSON.parse(fs.readFileSync(fixture,'utf8'));
let failed=0,passed=0;
for(const [det,hadithIds] of Object.entries(expected)){
  for(const id of hadithIds){const hit=F.some(f=>f.detector===det&&f.hadith_id===id);
    if(hit){passed++;console.log('PASS',det,id.slice(-8));}else{failed++;console.error('FAIL',det,id,'not caught');}}}
// negative controls: clean real chains must stay silent (a detector that fires everywhere would pass the loop above)
const {negatives}=JSON.parse(fs.readFileSync(fixture,'utf8'));
for(const id of negatives){const bad=F.filter(f=>f.hadith_id===id&&f.confidence==='high');if(bad.length){failed++;console.error('FAIL negative control flagged',id,bad.map(b=>b.detector));}else{passed++;console.log('PASS clean chain stays silent',id.slice(-8));}}
console.log(`${passed} checks passed, ${failed} failed`);
fs.rmSync(out,{force:true});
process.exit(failed?1:0);
