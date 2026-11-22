const pg=require('postgres');const sql=(pg.default||pg)(process.env.DATABASE_URL_PRODUCTION,{max:1});
(async()=>{
const q=async(label,p)=>{const r=await p;console.log(label.padEnd(72),r.map(x=>Object.entries(x).map(([k,v])=>k+'='+v).join(' ')).join(' ; '));};
// chains that end well before a sibling chain of the same hadith (route head without the shared tail): len<=3, sibling len>=5, sibling last 2 surfaces differ from this chain's last
await q('KAFI hadiths with a chain of <=3 mentions beside a sibling of >=5 (route stops early)',sql`
 with L as (select c.id,c.hadith_id,count(m.id) n from chains c join chain_mentions m on m.chain_id=c.id and m.retired_at is null join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id='collection:imami:al-kafi' group by c.id,c.hadith_id)
 select count(distinct a.hadith_id) hadiths,count(distinct a.id) short_chains from L a join L b on a.hadith_id=b.hadith_id and a.id<>b.id where a.n<=3 and b.n>=5`);
await q('SUNNI K6 hadiths with a chain of <=3 beside a sibling of >=5',sql`
 with L as (select c.id,c.hadith_id,count(m.id) n from chains c join chain_mentions m on m.chain_id=c.id and m.retired_at is null join hadiths h on h.id=c.hadith_id where c.retired_at is null and h.collection_id like 'collection:sunni:%' and h.id like 'hadith:k6:%' group by c.id,c.hadith_id)
 select count(distinct a.hadith_id) hadiths,count(distinct a.id) short_chains from L a join L b on a.hadith_id=b.hadith_id and a.id<>b.id where a.n<=3 and b.n>=5`);
await q('FAQIH hadiths opening «و ما كان فيه عن» (mashyakha form) / with chains',sql`select count(*) hadiths,count(*) filter (where exists(select 1 from chains c where c.hadith_id=h.id and c.retired_at is null)) with_chain from hadiths h where h.retired_at is null and h.collection_id='collection:imami:man-la-yahduruhu-al-faqih' and h.text_ar ~ '^\s*(و )?ما كان فيه عن'`);
await q('SUNNI K6 mentions with two+ names fused by «و» («X و Y»)',sql`select count(*) n from chain_mentions m join hadiths h on h.id=m.hadith_id where m.retired_at is null and h.collection_id like 'collection:sunni:%' and h.id like 'hadith:k6:%' and m.surface_ar ~ '(^| )و[ء-ي]+ بن '`);
await sql.end();})();
