// Round 4 pair sampler: uniform random rows of narrator_transmissions (100 Sunni, 50 Imami) + one random supporting chain each. Read-only.
const fs=require('fs');
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
const SEED='round4-pairs-1';
(async()=>{
 const tot=await sql`select count(*)::int n from narrator_transmissions`;
 console.log('pairs in view',tot[0].n);
 const rows=await sql`select student_id,teacher_id,hadith_count from narrator_transmissions order by md5(student_id::text||'|'||teacher_id::text||${SEED}) limit 700`;
 const want={sunni:100,imami:50};const got={sunni:[],imami:[]};
 for(const r of rows){
  if(got.sunni.length>=want.sunni&&got.imami.length>=want.imami)break;
  const sup=await sql`
   select c.id chain_id,a.hadith_id,a.position apos,h.collection_id
   from chain_mentions a
   join chains c on c.id=a.chain_id and c.retired_at is null and c.structure_status is distinct from 'uncertain'
   join chain_mentions b on b.chain_id=a.chain_id and b.position=a.position+1 and b.retired_at is null
   join hadiths h on h.id=a.hadith_id and h.retired_at is null
   where a.retired_at is null and a.narrator_id=${r.student_id} and b.narrator_id=${r.teacher_id}
    and a.resolution in ('source_index','human_verified','derived_relation_verified') and b.resolution in ('source_index','human_verified','derived_relation_verified')
    and a.link_kind not in ('anonymous','not_a_narrator') and b.link_kind not in ('anonymous','not_a_narrator')
    and ((a.resolution_basis='source_index' and b.resolution_basis='source_index') or (a.resolution_basis='human_decision' and b.resolution_basis='human_decision'))
    and not exists(select 1 from chain_mentions s1 join chain_mentions s2 on s2.chain_id=s1.chain_id and s2.narrator_id=s1.narrator_id and s2.position>s1.position and s2.retired_at is null where s1.chain_id=a.chain_id and s1.retired_at is null and s1.narrator_id is not null and s1.position<=a.position and s2.position>=b.position)
   order by md5(c.id||${SEED})`;
  if(!sup.length){console.log('no support',r.student_id,r.teacher_id);continue;}
  const trads=new Set(sup.map(s=>s.collection_id.split(':')[1]));
  let lane=null;
  if(trads.has('sunni')&&got.sunni.length<want.sunni)lane='sunni';else if(trads.has('imami')&&got.imami.length<want.imami)lane='imami';
  if(!lane)continue;
  const pick=sup.find(s=>s.collection_id.split(':')[1]===lane);
  got[lane].push({lane,student:r.student_id,teacher:r.teacher_id,hadith_count:r.hadith_count,support_n:sup.length,chain_id:pick.chain_id,hadith_id:pick.hadith_id,apos:pick.apos,coll:pick.collection_id});
 }
 const out=[...got.sunni,...got.imami];
 fs.writeFileSync('pair_ids.json',JSON.stringify(out,null,1));
 console.log(got.sunni.length,got.imami.length);
 await sql.end();})();
