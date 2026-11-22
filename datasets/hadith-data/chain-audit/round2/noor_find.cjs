// usage: node noor_find.cjs "<opening Arabic words>" <label> : Noor exact search in al-Kafi (book 1348) then HadithRejalList of the top hit; prints Noor sanads.
const fs=require('fs');
(async()=>{const [,,text,label]=process.argv;
 const body={Text:text,BookList:[1348],PageNumber:1,PageSize:3,SearchType:'exact',isErab:false,InFeild:'all',SearchIn:'hadith',PageSizeGrouping:10,PageNumGrouping:1,AccessLevel:0,isGroup:false,SortColumn:0,SortDirection:1,FlexibleForStem:false,FlexibleForLetter:false};
 const url='https://hadith.inoor.ir/service/api/elastic/v2/ElasticHadithList';
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (archive-research)'},body:JSON.stringify(body)});const t=await r.text();
 fs.writeFileSync(`fetched/noor_search_${label}.json`,JSON.stringify({url:url+' (POST, public Arabic query: '+text+')',fetched_utc:new Date().toISOString(),intent:'locate a public al-Kafi hadith by opening words to compare its sanad structure (round-2 re-check)',http_status:r.status,response:r.ok?JSON.parse(t):t.slice(0,200)}));
 if(!r.ok){console.log('HTTP',r.status);return;}
 const j=JSON.parse(t);const items=(j.data&&(j.data.items||j.data.list||j.data.hadithList||j.data))||[];const arr=Array.isArray(items)?items:Object.values(items);
 const first=JSON.stringify(j).match(/"hadithId":(\d+)/);console.log(label,'top hadithId',first&&first[1]);
 if(first){const u=`https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=${first[1]}`;const rr=await fetch(u,{headers:{'User-Agent':'Mozilla/5.0 (archive-research)'}});const tt=await rr.text();
  fs.writeFileSync(`fetched/noor_rejal_${first[1]}.json`,JSON.stringify({url:u,fetched_utc:new Date().toISOString(),intent:'Structured sanad list of the hadith located above (round-2 re-check)',http_status:rr.status,response:rr.ok?JSON.parse(tt):tt.slice(0,200)}));
  if(rr.ok){for(const s of JSON.parse(tt).data.sanadList)console.log('NOOR:',s.sanad.filter(x=>x.type===0||x.type===4).map(x=>x.title).join(' > '));
   const m=JSON.stringify(j).match(new RegExp('"hadithId":'+first[1]+'[^}]{0,600}'));}}
})();
