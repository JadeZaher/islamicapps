// defect chains (sample + populations) with hadith ids -> defects.json for the before/after comparison
const fs=require('fs');const hid=new Map();
for(const f of fs.readdirSync('.').filter(x=>/^(sample_ids|pop_[a-z_]+)\.json$/.test(x)))for(const s of JSON.parse(fs.readFileSync(f,'utf8')))hid.set(s.chain_id,s.hadith_id);
const rows=[];
for(const [f,hasPop] of [['verdicts.tsv',false],['pop_verdicts.tsv',true]])for(const l of fs.readFileSync(f,'utf8').split('\n').slice(1).filter(Boolean)){const c=l.split('\t');
 const [a,b,v,k,n]=c;const lane=a,chain=b;if(v!=='defect')continue;rows.push({lane,chain_id:chain,hadith_id:hid.get(chain),kind:k,note:n,pop:hasPop});}
fs.writeFileSync('defects.json',JSON.stringify(rows));console.log(rows.length,rows.filter(r=>!r.hadith_id).length);
