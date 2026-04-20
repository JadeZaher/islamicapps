/**
 * seed-taxonomy.ts
 *
 * Idempotently seeds the two-axis taxonomy nodes:
 *   (:ReligiousTradition) — world religions
 *   (:SchoolOfThought)    — Islamic schools / madhhabs
 * Plus the bridging and hierarchical edges:
 *   (:SchoolOfThought)-[:WITHIN_RELIGION]->(:ReligiousTradition {name:'Islam'})
 *   (:SchoolOfThought)-[:PART_OF]->(:SchoolOfThought)    // madhhab → parent school
 *
 * Safe to re-run. Uses mergeNodeByKey / mergeEdge from src/lib/db/neo4j-helpers.ts.
 *
 * Usage: tsx src/scripts/seed-taxonomy.ts
 */

import { loadEnv } from './lib/env';
import { closeDriver } from '../lib/db/neo4j';
import { mergeNodeByKey, mergeEdge } from '../lib/db/neo4j-helpers';

loadEnv();

interface ReligionSeed {
    name: string;
    name_arabic?: string;
    description: string;
    geographic_origin?: string;
}

interface SchoolSeed {
    name: string;
    name_arabic?: string;
    category:
        | 'SUNNI_THEOLOGICAL'
        | 'SHIA_THEOLOGICAL'
        | 'IBADI_THEOLOGICAL'
        | 'SUNNI_MADHHAB'
        | 'SHIA_MADHHAB';
    founder?: string;
    founded_century_hijri?: number;
    description: string;
    /** If set, this school is a madhhab nested under a parent SchoolOfThought. */
    parent_school?: string;
}

const RELIGIONS: ReligionSeed[] = [
    {
        name: 'Islam',
        name_arabic: 'الإسلام',
        description:
            'Monotheistic Abrahamic religion founded in 7th-century Arabia, based on the Quran and the teachings and example of Prophet Muhammad.',
        geographic_origin: 'Arabian Peninsula',
    },
    {
        name: 'Judaism',
        name_arabic: 'اليهودية',
        description:
            'Monotheistic Abrahamic religion rooted in the Hebrew Bible (Tanakh) and Rabbinic literature (Mishnah, Talmud).',
        geographic_origin: 'Ancient Near East / Levant',
    },
    {
        name: 'Christianity',
        name_arabic: 'المسيحية',
        description:
            'Monotheistic Abrahamic religion centered on the life and teachings of Jesus of Nazareth as recorded in the New Testament.',
        geographic_origin: 'Roman Judea / Levant',
    },
    {
        name: 'Zoroastrianism',
        name_arabic: 'الزرادشتية',
        description:
            'Ancient Iranian religion founded by the prophet Zarathustra (Zoroaster), scripturally centered on the Avesta.',
        geographic_origin: 'Ancient Iran (Persia)',
    },
];

const SCHOOLS: SchoolSeed[] = [
    // Theological schools (direct children of Islam)
    {
        name: 'Sunni',
        name_arabic: 'أهل السنة والجماعة',
        category: 'SUNNI_THEOLOGICAL',
        description:
            'The largest denomination of Islam, following the Quran and the sunnah of Prophet Muhammad as transmitted through the six canonical hadith collections and recognizing the first four caliphs as legitimate successors.',
    },
    {
        name: 'Ibadi',
        name_arabic: 'الإباضية',
        category: 'IBADI_THEOLOGICAL',
        founder: "Jabir ibn Zayd al-Azdi",
        founded_century_hijri: 1,
        description:
            "The Ibadi school emerged from the early Kharijite movement. Its foundational hadith collection is al-Jami' al-Sahih (Musnad al-Rabi' b. Habib), and its theology emphasizes a third path between Sunni and Shia traditions.",
    },
    {
        name: 'Shia Imami',
        name_arabic: 'الشيعة الإمامية',
        category: 'SHIA_THEOLOGICAL',
        description:
            'Also known as Twelver Shia. Believes in the imamate of twelve divinely appointed leaders descended from Ali ibn Abi Talib, and uses its own canonical hadith collections (al-Kutub al-Arbaʿa).',
    },
    {
        name: 'Shia Zaydi',
        name_arabic: 'الشيعة الزيدية',
        category: 'SHIA_THEOLOGICAL',
        founder: 'Zayd ibn Ali',
        founded_century_hijri: 2,
        description:
            'A branch of Shia Islam that follows Zayd ibn Ali and is theologically closer to Sunni Islam than the Imami tradition. Predominant historically in Yemen.',
    },

    // Sunni madhhabs (legal schools) — PART_OF Sunni
    {
        name: 'Hanafi',
        name_arabic: 'الحنفية',
        category: 'SUNNI_MADHHAB',
        founder: "Abu Hanifa al-Nu'man",
        founded_century_hijri: 2,
        description:
            'The largest Sunni school of jurisprudence, founded by Abu Hanifa (d. 150 AH). Known for extensive use of qiyas (analogical reasoning) and istihsan.',
        parent_school: 'Sunni',
    },
    {
        name: 'Maliki',
        name_arabic: 'المالكية',
        category: 'SUNNI_MADHHAB',
        founder: 'Malik ibn Anas',
        founded_century_hijri: 2,
        description:
            "Founded by Imam Malik (d. 179 AH), author of al-Muwatta'. Places strong weight on the practice of the people of Medina as a source of law.",
        parent_school: 'Sunni',
    },
    {
        name: "Shafi'i",
        name_arabic: 'الشافعية',
        category: 'SUNNI_MADHHAB',
        founder: "Muhammad ibn Idris al-Shafi'i",
        founded_century_hijri: 3,
        description:
            "Founded by al-Shafi'i (d. 204 AH). Systematized classical Sunni usul al-fiqh through his Risala, recognizing Quran, Sunnah, ijma, and qiyas as the four sources.",
        parent_school: 'Sunni',
    },
    {
        name: 'Hanbali',
        name_arabic: 'الحنبلية',
        category: 'SUNNI_MADHHAB',
        founder: 'Ahmad ibn Hanbal',
        founded_century_hijri: 3,
        description:
            'Founded by Ahmad ibn Hanbal (d. 241 AH), compiler of the Musnad. Emphasizes hadith-based jurisprudence over analogical reasoning.',
        parent_school: 'Sunni',
    },

    // Shia madhhab — PART_OF Shia Imami
    {
        name: "Ja'fari",
        name_arabic: 'الجعفرية',
        category: 'SHIA_MADHHAB',
        founder: "Ja'far al-Sadiq",
        founded_century_hijri: 2,
        description:
            "The jurisprudential school of Twelver Shia Islam, traced to the teachings of the sixth Imam Ja'far al-Sadiq (d. 148 AH).",
        parent_school: 'Shia Imami',
    },
];

async function main() {
    console.log('🌱 Seeding taxonomy (ReligiousTradition + SchoolOfThought)...\n');

    // 1. Religions
    console.log('📚 Religions:');
    for (const r of RELIGIONS) {
        const res = await mergeNodeByKey({
            label: 'ReligiousTradition',
            keyProp: 'name',
            keyValue: r.name,
            createProps: {
                name_arabic: r.name_arabic ?? null,
                description: r.description,
                geographic_origin: r.geographic_origin ?? null,
            },
        });
        console.log(`  ${res.created ? '  CREATED' : '  exists '}  ${r.name}  (id=${res.id})`);
    }

    // 2. SchoolsOfThought
    console.log('\n🎓 Schools of Thought:');
    for (const s of SCHOOLS) {
        const res = await mergeNodeByKey({
            label: 'SchoolOfThought',
            keyProp: 'name',
            keyValue: s.name,
            createProps: {
                name_arabic: s.name_arabic ?? null,
                category: s.category,
                founder: s.founder ?? null,
                founded_century_hijri: s.founded_century_hijri ?? null,
                description: s.description,
            },
        });
        console.log(`  ${res.created ? '  CREATED' : '  exists '}  ${s.name.padEnd(14)}  [${s.category}]  (id=${res.id})`);
    }

    // 3. WITHIN_RELIGION edges (all schools → Islam)
    console.log('\n🔗 WITHIN_RELIGION edges:');
    for (const s of SCHOOLS) {
        await mergeEdge({
            fromLabel: 'SchoolOfThought',
            fromKey: { prop: 'name', value: s.name },
            toLabel: 'ReligiousTradition',
            toKey: { prop: 'name', value: 'Islam' },
            relType: 'WITHIN_RELIGION',
        });
        console.log(`  ${s.name} -[:WITHIN_RELIGION]-> Islam`);
    }

    // 4. PART_OF edges for madhhabs under parent theological schools
    console.log('\n🔗 PART_OF edges (madhhab → parent school):');
    for (const s of SCHOOLS) {
        if (!s.parent_school) continue;
        await mergeEdge({
            fromLabel: 'SchoolOfThought',
            fromKey: { prop: 'name', value: s.name },
            toLabel: 'SchoolOfThought',
            toKey: { prop: 'name', value: s.parent_school },
            relType: 'PART_OF',
        });
        console.log(`  ${s.name} -[:PART_OF]-> ${s.parent_school}`);
    }

    console.log('\n✅ Taxonomy seed complete.\n');
    await closeDriver();
}

main().catch((err) => {
    console.error('❌ Seed failed:', err);
    process.exit(1);
});
