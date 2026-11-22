// usage: node fetchhadith.cjs <edition> <no> : saves public numbered Arabic hadith (fawazahmed0 hadith-api via jsDelivr) with header, prints text start.
const fs=require('fs');
(async()=>{const [,,ed,no]=process.argv;const url=`https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/${ed}/${no}.json`;
 const r=await fetch(url);const t=await r.text();
 fs.writeFileSync(`fetched/hadithapi_${ed}_${no}.json`,JSON.stringify({url,fetched_utc:new Date().toISOString(),intent:'Re-read the isnad of a public numbered hadith from an independent Arabic edition (round-2 re-check)',http_status:r.status,response:r.ok?JSON.parse(t):t.slice(0,200)}));
 if(r.ok){const j=JSON.parse(t);console.log(ed,no,j.hadiths[0].text.slice(0,330).replace(/\s+/g,' '));}else console.log(ed,no,r.status);})();
