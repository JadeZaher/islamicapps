// usage: node qt.cjs <hadith_id> [len] -> text_ar head (not sanad_ar)
const pg=require('postgres'); const postgres=pg.default||pg; const sql=postgres(process.env.DATABASE_URL_PRODUCTION,{max:1,connect_timeout:30});
(async()=>{const [h]=await sql`select sanad_ar,text_ar from hadiths where id=${process.argv[2]}`;console.log('SANAD:',h.sanad_ar,'\nTEXT:',h.text_ar.slice(0,+process.argv[3]||300).replace(/\s+/g,' '));await sql.end();})();
