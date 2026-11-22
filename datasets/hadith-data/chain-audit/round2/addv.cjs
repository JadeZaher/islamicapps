// usage: node addv.cjs <sub.json> <offset> <file with lines "idx|verdict|kind|note"> [lane]  appends to verdicts.tsv
const fs=require('fs');const [,,sub,off,f,lane]=process.argv;const ids=JSON.parse(fs.readFileSync(sub,'utf8'));
let o='';for(const l of fs.readFileSync(f,'utf8').split('\n').filter(Boolean)){const [i,v,k,n]=l.split('|');const s=ids[+i-(+off)];if(!s){console.log('bad idx',i);continue;}o+=[lane||s.lane,s.chain_id,v,k||'',n||''].join('\t')+'\n';}
fs.appendFileSync('verdicts.tsv',o);console.log('added',o.split('\n').length-1);
