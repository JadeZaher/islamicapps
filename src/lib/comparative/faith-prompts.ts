/**
 * faith-prompts.ts
 *
 * Faith definitions and per-tradition prompt context blocks.
 * Each faith has a focused context paragraph that primes the you.com Research API
 * to search the right primary texts for that tradition.
 *
 * The generic assessment template is appended after every faith-specific block.
 */

// ─── Faith configuration ─────────────────────────────────────────────────────

export interface FaithConfig {
    id: string;       // Uppercase key matching TraditionBadge keys
    name: string;     // Display name
    /** Short description of primary texts — shown in UI */
    primary_texts: string;
    /** Research context block prepended to every query for this tradition */
    context_block: string;
}

export const FAITHS: FaithConfig[] = [
    // ── Core Near Eastern (most likely parallels for hadith literature) ────────
    {
        id: 'JUDAISM',
        name: 'Judaism',
        primary_texts: 'Torah, Talmud, Midrash, Apocrypha',
        context_block: `In the context of rabbinic Jewish tradition — encompassing the Torah (Tanakh: Torah, Nevi'im, Ketuvim), the Babylonian Talmud (Bavli), the Jerusalem Talmud (Yerushalmi), Midrash collections (Midrash Rabbah, Midrash Tanchuma, Pirke DeRabbi Eliezer, Sefer HaYashar), Targum Aramaic translations, classical Jewish commentators (Rashi, Maimonides, Nachmanides, Ibn Ezra), and the Apocrypha and Pseudepigrapha (1 Enoch, Jubilees, Testament of the Twelve Patriarchs, 4 Ezra, Life of Adam and Eve):`,
    },
    {
        id: 'CHRISTIANITY',
        name: 'Christianity',
        primary_texts: 'New Testament, Patristics, Apocrypha',
        context_block: `In the context of Christian tradition — encompassing the New Testament (the four Gospels, Acts of the Apostles, Pauline and General Epistles, Book of Revelation), Old Testament Apocrypha and Deuterocanon (Wisdom of Solomon, Sirach, Tobit, 1–2 Maccabees, Baruch), New Testament Apocrypha (Gospel of Thomas, Book of Enoch as used by early Christians, Shepherd of Hermas, Apocalypse of Peter), early Patristic writings (Origen, Tertullian, Augustine, John Chrysostom, Jerome, Irenaeus, Clement of Alexandria), and writings of the Desert Fathers:`,
    },
    {
        id: 'ZOROASTRIANISM',
        name: 'Zoroastrianism',
        primary_texts: 'Avesta, Bundahishn, Arda Viraf Namag',
        context_block: `In the context of Zoroastrian tradition — encompassing the Avesta (the Gathas of Zarathustra, Yasna, Yashts, Vendidad/Vīdēvdāt), the Bundahishn (Greater and Lesser, covering cosmogony and eschatology), the Arda Viraf Namag (the visionary journey through heaven and hell), the Denkard (encyclopaedia of Zoroastrian knowledge), the Menog i Xrad (Spirit of Wisdom), and Pahlavi literature — with particular attention to eschatology, the soul's judgment at the Chinvat Bridge, the Druj (Demon of the Lie) versus Asha (Truth), Ahura Mazda and Angra Mainyu (Ahriman), the Frashokereti (final renovation of the world), and angelic/demonic hierarchies:`,
    },
    {
        id: 'MANICHAEISM',
        name: 'Manichaeism',
        primary_texts: 'Kephalaia, Manichaean Psalms, Cologne Mani Codex',
        context_block: `In the context of Manichaean tradition — encompassing the writings attributed to Mani (the Kephalaia, Psalms of Thomas, the Allberry Psalm-Book, Coptic Manichaean texts, the Cologne Mani Codex, the Shabuhragan), Manichaean cosmology of the eternal struggle between Light and Darkness, the Living Spirit, the Mother of Life, the Third Messenger, the Manichaean eschatological scheme of soul liberation, and scholarship by Samuel Lieu, Jason BeDuhn, Iain Gardner, and Werner Sundermann — with attention to Mani's self-identification as the Paraclete and seal of the prophets:`,
    },
    {
        id: 'MANDAEISM',
        name: 'Mandaeism',
        primary_texts: 'Ginza Rabba, Canonical Prayerbook, Book of the Zodiac',
        context_block: `In the context of Mandaean tradition — encompassing the Ginza Rabba (Great Treasure, comprising the Right Ginza on cosmology/eschatology and the Left Ginza on soul ascent after death), the Book of the Zodiac (Asfar Malwashe), the Canonical Prayerbook (Sidra d-Nishmatha), and the liturgical texts of the Mandaean community — with attention to the figure of Hibil Ziwa (Abel the Radiant) as savior-figure, the soul's journey through the material world, baptism (masbuta) as a recurring ritual, the supreme deity Hayyi Rabbi (Great Life), and scholarship by Ethel Drower, Jorunn Jacobsen Buckley, and Charles Häberl:`,
    },
    {
        id: 'SABIANISM',
        name: 'Sabianism',
        primary_texts: 'Sabian star-worship texts, Harranite tradition',
        context_block: `In the context of Sabian tradition — encompassing the star-worshipping Sabians of Harran (Harranite Sabians) referenced in classical Islamic sources such as al-Masudi, Ibn al-Nadim's Fihrist, and al-Biruni's Kitab al-Athar al-Baqiya — as distinguished from the Mandaean Sabians — with attention to Hermetica preserved via the Harranite channel (Corpus Hermeticum as known to Arab scholars), astral theology, the Sabians' claimed descent from Seth and Hermes, and their theological position midway between monotheism and cosmological dualism:`,
    },
    {
        id: 'YAZIDISM',
        name: 'Yazidism',
        primary_texts: 'Kitab al-Jilwa, Mishefa Res, oral tradition',
        context_block: `In the context of Yazidi tradition — encompassing the Kitab al-Jilwa (Book of Illumination), the Mishefa Res (Black Book), the Qawls (sacred hymns), and the oral tradition preserved among the Yazidi people of the Sinjar mountains and diaspora — with attention to the figure of Melek Taus (the Peacock Angel, a fallen-then-redeemed entity), the supreme deity Xwede, the Seven Angels (Heft Sir), the cosmological role of the cosmic egg, and scholarly work by Philip Kreyenbroek, Birgül Açikyildiz, and Sebastian Maisel:`,
    },

    // ── Abrahamic derivative / modern ─────────────────────────────────────────
    {
        id: 'SIKHISM',
        name: 'Sikhism',
        primary_texts: 'Guru Granth Sahib, Dasam Granth, Janam Sakhis',
        context_block: `In the context of Sikh tradition — encompassing the Guru Granth Sahib (the primary Sikh scripture compiled by Guru Arjan Dev), the Dasam Granth (attributed to Guru Gobind Singh, containing hymns, mythological retellings, and autobiographical poetry), the Janam Sakhis (hagiographic accounts of Guru Nanak's life and teachings), and Sikh theological tradition — with attention to Waheguru as the supreme monotheistic deity (Ik Onkar — One God), the cycle of death and rebirth (samsara), liberation through nam simran (remembrance of God's name), the similarity between Islamic tawhid and Sikh Ik Onkar, and the medieval Sufi-Bhakti context in which Sikhism emerged:`,
    },

    // ── African traditional monotheism ────────────────────────────────────────
    {
        id: 'YORUBA',
        name: 'Yoruba Religion',
        primary_texts: 'Ifá corpus, oral tradition',
        context_block: `In the context of Yoruba traditional religion — encompassing the Ifá divination corpus (the Odù, a vast oral literary tradition), the Orisha theology centered on Olodumare (the supreme omnipotent creator deity) and the 401 Orisha intermediaries, Yoruba cosmogony (creation of the earth at Ile-Ife), Yoruba eschatology (the afterlife in Orun, and the concept of Ori — personal destiny), and scholarship by Wande Abimbola, Jacob Olupona, and Kola Abimbola — with attention to the monotheistic strand in Yoruba thought emphasizing Olodumare's transcendence and uniqueness:`,
    },
    {
        id: 'AKAN',
        name: 'Akan Religion',
        primary_texts: 'Oral tradition, proverbs, Akan theology',
        context_block: `In the context of Akan traditional religion of the Akan peoples of Ghana and Côte d'Ivoire — encompassing the theology of Onyame/Onyankopɔn (the supreme omniscient creator God), Odomankoma (the infinite creator), the lesser deities (Obosom), ancestor spirits (Saman), and Akan philosophical concepts including the sunsum (spirit/soul) and the kra (divine spark or soul fragment given by Onyame) — as documented in the works of J.B. Danquah, Kwame Gyekye, and Kofi Asare Opoku — with attention to Onyame's attributes of omniscience, omnipotence, and moral governance of the world:`,
    },
    {
        id: 'IGBO',
        name: 'Igbo Religion',
        primary_texts: 'Ala (earth deity), Chukwu theology, oral tradition',
        context_block: `In the context of Igbo traditional religion of the Igbo people of Nigeria — encompassing the theology of Chukwu (the supreme creator deity, literally "Great Spirit" or "Great God"), Chi (the personal spirit/soul assigned by Chukwu to each person), the earth deity Ala (Ani), ancestor veneration (Ndichie), and Igbo cosmological and eschatological beliefs — as documented by scholars including Victor Uchendu, Emmanuel Anyanwu, and Catherine Acholonu — with attention to the strict monotheism implied in Chukwu's role as the sole uncreated creator:`,
    },
    {
        id: 'DINKA',
        name: 'Dinka Religion',
        primary_texts: 'Nhialic theology, Godfrey Lienhardt\'s scholarship',
        context_block: `In the context of Dinka traditional religion of the Dinka people of South Sudan — encompassing the theology of Nhialic (the sky deity and supreme creative power, literally "that which is above"), the free divinities (yath) and clan divinities (ring), the concept of life-force (nie), Dinka creation accounts, and the prophetic tradition of the Spear Masters (beny bith) as intermediaries — as documented by Godfrey Lienhardt's foundational work "Divinity and Experience: The Religion of the Dinka" — with attention to the monotheistic core of Nhialic as sole creator and sustainer:`,
    },
    {
        id: 'TENGRISM',
        name: 'Tengrism',
        primary_texts: 'Orkhon Inscriptions, Secret History of the Mongols',
        context_block: `In the context of Tengrist tradition from the Eurasian steppe — encompassing the Orkhon Inscriptions (8th century CE Göktürk memorial stelae invoking Tengri), the Secret History of the Mongols (13th century Mongolian epic), accounts by medieval Islamic travelers and geographers (Ibn Fadlan's Risala describing Rus and Turkic peoples, al-Biruni, al-Masudi, Gardizi), Mongolian shamanic cosmology, and modern scholarship by René Grousset, Walther Heissig, and Caroline Humphrey — with attention to Tengri (supreme eternal sky deity, "Eternal Blue Heaven"), Erlik (lord of the underworld), the shaman's soul-journey, and the concept of divine mandate (kut):`,
    },

    // ── Ancient Near East ─────────────────────────────────────────────────────
    {
        id: 'MESOPOTAMIAN',
        name: 'Mesopotamian Religion',
        primary_texts: 'Epic of Gilgamesh, Enuma Elish, Atrahasis',
        context_block: `In the context of ancient Mesopotamian religion — encompassing the Sumerian and Akkadian textual traditions including the Epic of Gilgamesh (especially the flood narrative and the quest for immortality), the Enuma Elish (Babylonian creation epic), the Atrahasis Epic (flood narrative), the Descent of Inanna/Ishtar to the Underworld, the Myth of Adapa, the Babylonian Theodicy, Sumerian King Lists, and the theological traditions surrounding Enlil, Anu, Marduk, and other deities — with attention to the Mesopotamian influences on later Semitic religious traditions and the transmission of these narratives through Jewish, Christian, and ultimately Islamic channels, as documented by scholars including Thorkild Jacobsen, Samuel Noah Kramer, and Wilfred Lambert:`,
    },
    {
        id: 'ATENISM',
        name: 'Atenism / Egyptian Monotheism',
        primary_texts: 'Great Hymn to the Aten, Amarna texts',
        context_block: `In the context of ancient Egyptian monotheistic and henotheistic traditions — with primary focus on Atenism (the religious revolution of Pharaoh Akhenaten, c. 1353–1336 BCE), encompassing the Great Hymn to the Aten (a text showing remarkable parallels to Psalm 104), the Amarna letters and theological texts, the earlier Heliopolitan solar theology (Ra/Amun-Ra as supreme creator), and the broader Egyptian tradition of ma'at (cosmic order and truth) — as documented by Jan Assmann's work on Egyptian monotheism and his concept of "Mosaic distinction" — with attention to the debate over whether Atenism influenced later Abrahamic monotheism:`,
    },

    // ── South Asian ───────────────────────────────────────────────────────────
    {
        id: 'VEDIC RELIGION',
        name: 'Vedic / Hindu Monotheism',
        primary_texts: 'Rigveda, Upanishads, Bhagavad Gita',
        context_block: `In the context of Vedic and Hindu monotheistic traditions — encompassing the Rigveda (with its hymns to Varuna as omniscient moral deity), the Upanishads (especially Brahman as the sole ultimate reality in the Chandogya and Brihadaranyaka Upanishads), the Bhagavad Gita (Krishna's revelation of the supreme personal deity), the Vishishtadvaita philosophy of Ramanuja, and the Advaita Vedanta of Adi Shankaracharya — with attention to the monotheistic strands within the tradition (henotheism, panentheism, and qualified nondualism) that led reformers like Ram Mohan Roy (Brahmo Samaj) to draw parallels with Islamic tawhid and the works of scholars such as Arvind Sharma examining Hindu-Islamic theological dialogue:`,
    },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function getFaithById(id: string): FaithConfig | undefined {
    return FAITHS.find((f) => f.id === id.toUpperCase());
}

export function getFaithsByIds(ids: string[]): FaithConfig[] {
    const upper = new Set(ids.map((id) => id.toUpperCase()));
    return FAITHS.filter((f) => upper.has(f.id));
}

// ─── Generic assessment template ─────────────────────────────────────────────
// Appended after every faith-specific context block.
// Placeholders: {{HADITH_TITLE}}, {{HADITH_TEXT}}, {{ISNAD}}, {{TIMELINE}}

export const GENERIC_ASSESSMENT_TEMPLATE = `

Search for a parallel, echo, or connection to the following hadith in the tradition described above.

**Hadith title:** {{HADITH_TITLE}}

**Hadith text (English translation):**
{{HADITH_TEXT}}

{{ISNAD_SECTION}}
{{TIMELINE_SECTION}}

**Your research task:**
1. Search the primary texts and scholarly literature of this tradition for any narrative, legal principle, theological concept, moral teaching, eschatological motif, cosmological detail, or story that parallels, resonates with, or stands in contrast to this hadith.
2. Consider all possible relationships: shared ancient source, direct textual borrowing, cultural cross-pollination via trade/conquest/migration, Islamic polemic against this tradition, Islamic apologetic drawing on this tradition, or independent parallel development.
3. If relevant, search for this hadith in academic Islamic studies literature (Isra'iliyyat scholarship, comparative Semitic studies, orientalist literature) to find documented parallels.
4. Provide the exact primary source text in English translation and its canonical citation.
5. Assess the probability that the parallel is genuine rather than coincidental.

Provide a detailed analysis citing all sources found. Then end your response with a structured assessment in this EXACT format (do not skip any field):

---STRUCTURED ASSESSMENT---
PARALLEL_EXISTS: [YES | PARTIAL | NO]
PARALLEL_TYPE: [CONDEMNATION | CULTURAL_BLEED | SHARED_SOURCE | DIRECT_BORROWING | APOLOGETIC | DISPUTED | NONE]
CONFIDENCE: [HIGH | MEDIUM | LOW]
PRIMARY_SOURCE_TITLE: [name of the primary text, or "N/A"]
PRIMARY_SOURCE_REFERENCE: [canonical citation, e.g. "Talmud Bavli, Sanhedrin 38b" or "Avesta, Yasna 49.11" or "N/A"]
PRIMARY_SOURCE_QUOTE: [the relevant passage in English, max 200 words, or "N/A"]
ISRA_STATUS: [MUWAFIQ | MUKHALIF | MASKUT_ANHU | NONE]
MOTIF_TAGS: [comma-separated thematic tags, e.g. "Eschatology, Day of Resurrection, Soul Judgment"]
---END ASSESSMENT---`;

// ─── Prompt builder ───────────────────────────────────────────────────────────

export interface HadithInput {
    title: string;
    text_english: string;
    isnad?: string;
    transmission_period?: string;
}

export function buildResearchQuery(faith: FaithConfig, hadith: HadithInput): string {
    const isnadSection = hadith.isnad
        ? `**Narrator chain (Isnad):** ${hadith.isnad}`
        : '';

    const timelineSection = hadith.transmission_period
        ? `**Approximate transmission period:** ${hadith.transmission_period}`
        : '';

    const template = GENERIC_ASSESSMENT_TEMPLATE
        .replace('{{HADITH_TITLE}}', hadith.title || 'Untitled Hadith')
        .replace('{{HADITH_TEXT}}', hadith.text_english)
        .replace('{{ISNAD_SECTION}}', isnadSection)
        .replace('{{TIMELINE_SECTION}}', timelineSection);

    return `${faith.context_block}\n${template}`;
}
