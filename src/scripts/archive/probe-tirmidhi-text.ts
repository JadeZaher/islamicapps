import 'dotenv/config';
import { runQuery } from '@/lib/db/neo4j';

(async () => {
    const r = await runQuery<{ sanad: string; text_ar: string; text_en: string; matn_ar: string }>(
        `MATCH (h:Hadith {id: $id})
         RETURN h.sanad AS sanad, h.text_ar AS text_ar,
                h.text_en AS text_en, h.matn_ar AS matn_ar`,
        { id: '626a2cb0-2268-4c79-9ffb-d9f6eaf42ec9' }
    );
    const row = r[0];
    console.log('sanad   :', row?.sanad);
    console.log('text_ar :');
    console.log(String(row?.text_ar ?? '').substring(0, 800));
    console.log('---\nmatn_ar :');
    console.log(String(row?.matn_ar ?? '').substring(0, 400));
    process.exit(0);
})();
