// usage: node turath.cjs "<public Arabic words>" [needle] : Turath full-text search, prints best hits with the matching passage; saves response with URL/UTC/intent.
const fs=require('fs'),crypto=require('crypto');
(async()=>{const q=process.argv[2];const needle=process.argv[3];
 const url='https://api.turath.io/search?q='+encodeURIComponent(q);
 const r=await fetch(url);const t=await r.text();
 const f='fetched/turath_'+crypto.createHash('md5').update(q).digest('hex').slice(0,10)+'.json';
 fs.writeFileSync(f,JSON.stringify({url,fetched_utc:new Date().toISOString(),intent:'Re-read the written isnad of a public hadith by its opening words (round-3 re-check)',http_status:r.status,response:r.ok?JSON.parse(t):t.slice(0,200)}));
 if(!r.ok){console.log('HTTP',r.status);return;}
 const j=JSON.parse(t);const d=j.data||[];console.log('hits',d.length,f);
 for(const x of d.slice(0,3)){const txt=(x.text||'').replace(/<[^>]+>/g,'').replace(/[ً-ْٰـ]/g,'').replace(/\s+/g,' ');console.log('-',x.meta&&x.meta.book||'',x.book_id,x.page_id||x.pg||'','|',needle?(txt.indexOf(needle)>=0?txt.slice(Math.max(0,txt.indexOf(needle)-120),txt.indexOf(needle)+260):txt.slice(0,300)):txt.slice(0,300));}
})();
