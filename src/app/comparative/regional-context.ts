export interface RegionalContext {
    school: string;
    traditions: string[];
    narrators: string[];
    notes: string;
}

/** Editorial reference table of transmission centres and the communities present there (static content, not graph data). */
export const REGIONAL_CONTEXT: RegionalContext[] = [
    {
        school: 'Damascus (Syria)',
        traditions: ['Judaism', 'Christianity'],
        narrators: ["Ka'b al-Ahbar", 'Wahb ibn Munabbih'],
        notes: "Isra'iliyyat reports are associated with this centre. Ka'b al-Ahbar was a Jewish convert who settled in Damascus under the Umayyads.",
    },
    {
        school: 'Kufa (Iraq)',
        traditions: ['Judaism', 'Zoroastrianism'],
        narrators: ['Salman al-Farisi', "Ibn Mas'ud students"],
        notes: "Persian cultural contact and active Jewish diaspora communities. Scholars have discussed the relation of ra'y methodology to both.",
    },
    {
        school: 'Basra (Iraq)',
        traditions: ['Zoroastrianism', 'Manichaeism'],
        narrators: ['Al-Hasan al-Basri'],
        notes: 'Gateway to Persia. Zoroastrian converts were common in the early Islamic period. Some ascetic themes have been compared with Zoroastrian and Manichaean material.',
    },
    {
        school: 'Medina (Hijaz)',
        traditions: ['Judaism', 'Christianity'],
        narrators: ['Abdullah ibn Salam'],
        notes: 'Jewish tribes of Banu Qaynuqa, Banu Nadir and Banu Qurayza had a historical presence. Christian contact via trade routes.',
    },
    {
        school: 'Khorasan / Persia',
        traditions: ['Zoroastrianism'],
        narrators: ["Late Tabi'in chains"],
        notes: 'Abbasid-era expansion. Zoroastrian conceptual vocabulary appears in Islamic theological discourse during the translation movement.',
    },
    {
        school: 'Yemen',
        traditions: ['Judaism', 'Christianity'],
        narrators: ['Wahb ibn Munabbih', "Ka'b al-Ahbar (origin)"],
        notes: 'Wahb ibn Munabbih was of Yemeni/South Arabian origin with a Jewish background. Yemen had ancient Jewish and Christian communities.',
    },
];
