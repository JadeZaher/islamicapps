/**
 * seed-narrator-bios-phase0.ts
 *
 * Phase 0 of the narrator-enrichment track: hand-craft reasoned biographies
 * for the 20 most-cited (supernode) narrators in the v2 graph, plus the
 * Prophet himself (marked is_prophet=true to opt out of jarḥ wa taʿdīl).
 *
 * Why hand-craft for Phase 0
 * --------------------------
 * Before automating extraction from al-Mizzī's Tahdhīb al-Kamāl (Phase 2),
 * we need (a) a schema that holds the classical critique structure and
 * (b) UI that renders it well. This script populates ~21 anchor narrators
 * so the schema and UI can be validated end-to-end against real data
 * before we invest in the bulk pipeline.
 *
 * Fields written (matches spec § Addendum 2026-05-24)
 * ---------------------------------------------------
 *   is_prophet                — bool; if true, bio_* fields are omitted by design
 *   is_companion              — bool; flags ṣaḥābī (relevant for Sunni ʿadālat al-ṣaḥāba)
 *   tabaqah                   — classical class: PROPHET | SAHABA | TABIUN | ATBA_TABIUN | ATBA_ATBA
 *   kunya                     — agnomen ("Abū / Umm X")
 *   nasab                     — patronymic lineage (concise)
 *   nisba                     — tribal/geographic affiliation
 *   name_arabic               — clean Arabic name (overwrites the partial one)
 *   name_english              — clean transliteration
 *   death_date_hijri          — AH year
 *   death_date_gregorian      — CE year
 *   geographic_region         — primary place of activity
 *   bio_summary               — 2-3 sentence English synopsis
 *   bio_taʿdīl                — classical tawthīq quotes (Arabic + parenthetical English gloss)
 *   bio_jarḥ                  — classical tajrīḥ quotes (often empty for Companions / major Tābiʿīn)
 *   reliability_consensus     — thiqa | thiqa_thabt | ṣadūq | majhūl | ḍaʿīf | matrūk |
 *                                 kadhāb | mukhtalaf_fīhi | not_applicable (latter = Companion or Prophet)
 *   reliability_disagreement  — true when critics conflicted
 *   critic_quote_count        — number of distinct critics surfaced in bio_taʿdīl + bio_jarḥ
 *   bio_provenance            — 'manual_phase_0' (so Phase 1-3 can detect & skip)
 *
 * Idempotent: MERGE-by-scholar_indx + SET — re-running over the same narrator
 * refreshes the bio without touching unrelated fields. Existing v2 fields
 * (`name`, `name_english`, `_raw_grade`, etc.) are NOT overwritten unless
 * the new value is explicitly different (Cypher SET overwrites).
 *
 * Provenance / sources
 * --------------------
 * Companions: bios reference the Sunni doctrine of `ʿadālat al-ṣaḥāba`
 * (all Companions are upright by collective testimony) and cite the
 * primary biographical works (Ibn Ḥajar's al-Iṣāba, Ibn ʿAbd al-Barr's
 * al-Istīʿāb, Ibn al-Athīr's Usd al-Ghāba). The Imami / Mu'tazili
 * counter-views are noted where relevant.
 *
 * Tabi'ūn / Atbā' al-Tābiʿīn: bios cite verdicts from Mizzī's Tahdhīb
 * al-Kamāl, Ibn Ḥajar's Taqrīb al-Tahdhīb, al-Dhahabī's Siyar Aʿlām
 * al-Nubalāʾ, and (for impugned narrators) Mīzān al-Iʿtidāl. All quotes
 * are well-known passages — no original interpretation.
 *
 * Run
 * ---
 *   npx tsx src/scripts/seed-narrator-bios-phase0.ts            # writes
 *   npx tsx src/scripts/seed-narrator-bios-phase0.ts --dry-run  # prints, no writes
 */

import 'dotenv/config';
import { runWrite, closeDriver } from '../lib/db/neo4j';

type ReliabilityVerdict =
    | 'thiqa'
    | 'thiqa_thabt'
    | 'ṣadūq'
    | 'lā_baʾsa_bihi'
    | 'majhūl'
    | 'ḍaʿīf'
    | 'matrūk'
    | 'kadhāb'
    | 'mukhtalaf_fīhi'
    | 'not_applicable';

type Tabaqah = 'PROPHET' | 'SAHABA' | 'TABIUN' | 'ATBA_TABIUN' | 'ATBA_ATBA';

interface NarratorBio {
    scholar_indx: number;
    is_prophet?: boolean;
    is_companion?: boolean;
    tabaqah: Tabaqah;
    name_english: string;
    name_arabic: string;
    kunya?: string;
    nasab?: string;
    nisba?: string;
    death_date_hijri?: number;
    death_date_gregorian?: number;
    geographic_region?: string;
    bio_summary: string;
    bio_taʿdīl?: string;
    bio_jarḥ?: string;
    reliability_consensus: ReliabilityVerdict;
    reliability_disagreement?: boolean;
    critic_quote_count?: number;
}

const BIOS: NarratorBio[] = [
    // ═══ Prophet ═══
    {
        scholar_indx: 1,
        is_prophet: true,
        tabaqah: 'PROPHET',
        name_english: 'The Prophet Muḥammad ﷺ',
        name_arabic: 'محمّد بن عبد الله ﷺ',
        kunya: 'Abū al-Qāsim',
        nasab: 'ibn ʿAbd Allāh ibn ʿAbd al-Muṭṭalib',
        nisba: 'al-Qurashī al-Hāshimī',
        death_date_hijri: 11,
        death_date_gregorian: 632,
        geographic_region: 'Makka / Madīna',
        bio_summary:
            'The final Prophet of Islam. Not a transmitter subject to jarḥ wa taʿdīl: he is the source of the ḥadīth corpus. ' +
            'Born in Makka c. 570 CE, received the Qur\'anic revelation at age 40, migrated to Madīna in 622 CE (year 1 AH), ' +
            'and died there in 11 AH. All chain analysis treats his sayings as the terminal authority; biographical fields here ' +
            'document basic identity, not narrator critique.',
        reliability_consensus: 'not_applicable',
    },

    // ═══ Companions (Ṣaḥāba) — `ʿadālat al-ṣaḥāba` ═══
    {
        scholar_indx: 2,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'Abū Bakr al-Ṣiddīq',
        name_arabic: 'أبو بكر الصدّيق - عبد الله بن أبي قُحافة',
        kunya: 'Abū Bakr',
        nasab: 'ibn Abī Quḥāfa ʿUthmān ibn ʿĀmir',
        nisba: 'al-Taymī al-Qurashī',
        death_date_hijri: 13,
        death_date_gregorian: 634,
        geographic_region: 'Madīna',
        bio_summary:
            'First Caliph of Islam (r. 11–13 AH / 632–634 CE), closest Companion of the Prophet, and one of the ten promised Paradise ' +
            '(al-ʿasharah al-mubashsharah). Among the earliest converts. Narrated 142 ḥadīth.',
        bio_taʿdīl:
            'ʿAdālat al-ṣaḥāba is taken for granted by the consensus of Sunni scholarship; specific tawthīq is therefore not recorded ' +
            'for him in the rijāl literature. The Qur\'an itself (al-Tawba 9:40) affirms his standing.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 3,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'ʿUmar ibn al-Khaṭṭāb',
        name_arabic: 'عمر بن الخطّاب',
        kunya: 'Abū Ḥafṣ',
        nasab: 'ibn al-Khaṭṭāb ibn Nufayl',
        nisba: 'al-ʿAdawī al-Qurashī',
        death_date_hijri: 23,
        death_date_gregorian: 644,
        geographic_region: 'Madīna',
        bio_summary:
            'Second Caliph (r. 13–23 AH / 634–644 CE). Among the ten promised Paradise. Established core administrative institutions ' +
            'of the early Islamic state. Narrated 537 ḥadīth.',
        bio_taʿdīl:
            'The Prophet ﷺ is reported by al-Bukhārī to have said: "إنّ الله جعل الحقّ على لسان عمر وقلبه" ' +
            '("Allah has placed truth upon ʿUmar\'s tongue and heart"). Sunni rijāl literature does not subject him to individual taʿdīl/jarḥ.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 4,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'ʿUthmān ibn ʿAffān',
        name_arabic: 'عثمان بن عفّان',
        kunya: 'Abū ʿAbd Allāh / Abū ʿAmr',
        nasab: 'ibn ʿAffān ibn Abī al-ʿĀṣ',
        nisba: 'al-Umawī al-Qurashī',
        death_date_hijri: 35,
        death_date_gregorian: 656,
        geographic_region: 'Madīna',
        bio_summary:
            'Third Caliph (r. 23–35 AH / 644–656 CE), among the ten promised Paradise, and commissioner of the standardised ' +
            'Qur\'an codex (al-muṣḥaf al-ʿuthmānī). Narrated 146 ḥadīth.',
        bio_taʿdīl:
            'ʿAdālat al-ṣaḥāba doctrine applies; no individual jarḥ on him in the classical Sunni rijāl tradition.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 5,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'ʿAlī ibn Abī Ṭālib',
        name_arabic: 'علي بن أبي طالب',
        kunya: 'Abū al-Ḥasan / Abū Turāb',
        nasab: 'ibn Abī Ṭālib ibn ʿAbd al-Muṭṭalib',
        nisba: 'al-Hāshimī al-Qurashī',
        death_date_hijri: 40,
        death_date_gregorian: 661,
        geographic_region: 'Madīna / Kūfa',
        bio_summary:
            'Fourth Caliph in Sunni tradition (r. 35–40 AH / 656–661 CE); first Imam in Twelver Shi\'i tradition. Cousin and son-in-law ' +
            'of the Prophet, raised in his household. Central to both Sunni and Shi\'i isnād — virtually all Twelver chains pass through him ' +
            'or his descendants. Narrated 586 ḥadīth in Sunni collections; far more attributed to him in Shi\'i collections.',
        bio_taʿdīl:
            'In Sunni rijāl: ʿadālat al-ṣaḥāba applies. In Imami rijāl: he is the highest authority after the Prophet (al-imām al-maʿṣūm).',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 13,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'Abū Hurayra',
        name_arabic: 'أبو هريرة - عبد الرحمن بن صخر الدوسي',
        kunya: 'Abū Hurayra',
        nasab: 'ʿAbd al-Raḥmān ibn Ṣakhr (most accepted; over 30 versions of his name recorded)',
        nisba: 'al-Dawsī al-Yamānī',
        death_date_hijri: 57,
        death_date_gregorian: 678,
        geographic_region: 'Madīna',
        bio_summary:
            'The most prolific narrator of Prophetic ḥadīth in Sunni tradition: 5,374 narrations recorded, ' +
            '325 of which are in both al-Bukhārī and Muslim. Embraced Islam in 7 AH and spent the remaining four years of the ' +
            'Prophet\'s life almost continuously in his company (mulāzama). Was among ahl al-ṣuffa.',
        bio_taʿdīl:
            'Sunni rijāl literature does not subject Companions to individual tawthīq; his prolific output is treated as authoritative by ' +
            'al-Bukhārī, Muslim, and the entire Sunni canon. ' +
            'al-Imām al-Shāfiʿī said: "أبو هريرة أحفظ من روى الحديث في دهره" ("Abū Hurayra was the most retentive ḥadīth narrator of his era").',
        bio_jarḥ:
            'Some early reports (e.g. one attributed to ʿĀʾisha) questioned the volume of his narrations, since he had less time with the ' +
            'Prophet than older Companions. Imami and Muʿtazili scholarship is more critical; al-Shaykh al-Mufīd impugned several of his narrations specifically. ' +
            'Sunni response: he himself explained the disparity (Ṣaḥīḥ al-Bukhārī #118) by his uninterrupted presence at the mosque while others were occupied with trade.',
        reliability_consensus: 'not_applicable',
        reliability_disagreement: true,
    },
    {
        scholar_indx: 17,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'ʿAbd Allāh ibn ʿAbbās',
        name_arabic: 'عبد الله بن العبّاس بن عبد المطلب — الحَبْر',
        kunya: 'Abū al-ʿAbbās',
        nasab: 'ibn al-ʿAbbās ibn ʿAbd al-Muṭṭalib',
        nisba: 'al-Hāshimī al-Qurashī',
        death_date_hijri: 68,
        death_date_gregorian: 687,
        geographic_region: 'Madīna / al-Ṭāʾif',
        bio_summary:
            'Cousin of the Prophet ﷺ, called "Ḥabr al-umma" ("the doctor of the community") and "Tarjumān al-Qurʾān" ("interpreter of the Qur\'an") ' +
            'for his exegetical authority. Was a child at the Prophet\'s death; the Prophet had specifically prayed for his understanding of religion. ' +
            'Narrated 1,660 ḥadīth — the third most prolific Companion.',
        bio_taʿdīl:
            'The Prophet ﷺ prayed: "اللهم فقّهه في الدين وعلّمه التأويل" ("O Allah, grant him understanding in religion and teach him interpretation"). ' +
            'Recorded in al-Bukhārī and Aḥmad. ʿUmar ibn al-Khaṭṭāb consulted him in council despite his youth.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 18,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'ʿAbd Allāh ibn ʿUmar',
        name_arabic: 'عبد الله بن عمر بن الخطّاب',
        kunya: 'Abū ʿAbd al-Raḥmān',
        nasab: 'ibn ʿUmar ibn al-Khaṭṭāb',
        nisba: 'al-ʿAdawī al-Qurashī',
        death_date_hijri: 73,
        death_date_gregorian: 693,
        geographic_region: 'Madīna',
        bio_summary:
            'Son of the second Caliph. Embraced Islam as a child alongside his father. Famous for meticulous emulation of the Prophet\'s practice (sunna). ' +
            'Narrated 2,630 ḥadīth, second only to Abū Hurayra. Outlived most of his peers and was a primary source for the Madīnan school.',
        bio_taʿdīl:
            'Universally regarded by Sunni scholarship as one of the most reliable Companion-narrators. Imām Mālik\'s Muwaṭṭaʾ heavily depends on him.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 19,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'Anas ibn Mālik',
        name_arabic: 'أنس بن مالك بن النضر',
        kunya: 'Abū Ḥamza',
        nasab: 'ibn Mālik ibn al-Naḍr',
        nisba: 'al-Anṣārī al-Khazrajī al-Najjārī',
        death_date_hijri: 93,
        death_date_gregorian: 712,
        geographic_region: 'Madīna / Baṣra',
        bio_summary:
            'Personal servant of the Prophet ﷺ from age 10 (when his mother Umm Sulaym presented him) until the Prophet\'s death. ' +
            'Narrated 2,286 ḥadīth — fourth most prolific Companion. Settled in Baṣra and was a foundational link in the Baṣran transmission tradition.',
        bio_taʿdīl: 'Universally trusted across all classical traditions.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 34,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'Jābir ibn ʿAbd Allāh al-Anṣārī',
        name_arabic: 'جابر بن عبد الله بن عمرو السلمي الأنصاري',
        kunya: 'Abū ʿAbd Allāh',
        nasab: 'ibn ʿAbd Allāh ibn ʿAmr',
        nisba: 'al-Anṣārī al-Khazrajī al-Salamī',
        death_date_hijri: 78,
        death_date_gregorian: 697,
        geographic_region: 'Madīna',
        bio_summary:
            'Companion who participated in the Pledge of al-ʿAqaba and most of the Prophet\'s campaigns. Narrated 1,540 ḥadīth — ' +
            'sixth most prolific. Outlived nearly all his peers; was a major teacher of the next generation\'s Tabi\'ūn. ' +
            'Of particular weight in Shi\'i traditions for his association with the Prophet\'s household.',
        bio_taʿdīl: 'Across both Sunni and Imami rijāl traditions, regarded without dispute.',
        reliability_consensus: 'not_applicable',
    },
    {
        scholar_indx: 53,
        is_companion: true,
        tabaqah: 'SAHABA',
        name_english: 'ʿĀʾisha bint Abī Bakr — Umm al-Muʾminīn',
        name_arabic: 'أمّ المؤمنين عائشة بنت أبي بكر الصدّيق',
        kunya: 'Umm ʿAbd Allāh',
        nasab: 'bint Abī Bakr al-Ṣiddīq',
        nisba: 'al-Taymiyya al-Qurashiyya',
        death_date_hijri: 58,
        death_date_gregorian: 678,
        geographic_region: 'Madīna',
        bio_summary:
            'Wife of the Prophet ﷺ and daughter of Abū Bakr. Foremost female narrator: 2,210 ḥadīth, fifth-most prolific overall. ' +
            'Foundational authority on the Prophet\'s domestic life, ritual practice, and Qur\'anic context (asbāb al-nuzūl).',
        bio_taʿdīl:
            'The Prophet ﷺ is reported in al-Bukhārī to have referred questioners to her, saying: ' +
            '"خذوا شطر دينكم عن هذه الحميراء" ("Take half of your religion from this fair one"; isnād of this specific wording is contested, ' +
            'but the principle of her authority is firmly attested). The major Tabi\'ūn — ʿUrwa ibn al-Zubayr (her nephew), al-Qāsim ibn Muḥammad (her nephew), ' +
            'and Masrūq — were her direct students.',
        bio_jarḥ:
            'In Imami rijāl her role in the Battle of the Camel (36 AH) is treated more critically; this is theological/historical critique rather than ḥadīth-methodological jarḥ.',
        reliability_consensus: 'not_applicable',
        reliability_disagreement: true,
    },

    // ═══ Tabi'ūn ═══
    {
        scholar_indx: 10511,
        tabaqah: 'TABIUN',
        name_english: 'ʿUrwa ibn al-Zubayr',
        name_arabic: 'عروة بن الزبير بن العوّام',
        kunya: 'Abū ʿAbd Allāh',
        nasab: 'ibn al-Zubayr ibn al-ʿAwwām',
        nisba: 'al-Asadī al-Qurashī al-Madanī',
        death_date_hijri: 94,
        death_date_gregorian: 713,
        geographic_region: 'Madīna',
        bio_summary:
            'One of the "Seven Fuqahāʾ of Madīna" (al-fuqahāʾ al-sabʿa) and nephew of ʿĀʾisha — his primary teacher. ' +
            'Founder of the Madīnan ḥadīth-recording tradition; widely regarded as the first systematic historian of the sīra.',
        bio_taʿdīl:
            'Ibn Ḥajar (Taqrīb): "ثقة فقيه مشهور" ("thiqa, jurist, well-known"). ' +
            'al-Dhahabī (Siyar): described him as "أحد أئمة المسلمين" ("one of the imāms of the Muslims"). ' +
            'No recorded jarḥ in the major rijāl works.',
        reliability_consensus: 'thiqa_thabt',
        critic_quote_count: 2,
    },
    {
        scholar_indx: 11013,
        tabaqah: 'TABIUN',
        name_english: 'Muḥammad ibn Muslim — Ibn Shihāb al-Zuhrī',
        name_arabic: 'محمد بن مسلم بن شهاب الزُّهْري',
        kunya: 'Abū Bakr',
        nasab: 'ibn Muslim ibn ʿUbayd Allāh ibn ʿAbd Allāh ibn Shihāb',
        nisba: 'al-Zuhrī al-Qurashī al-Madanī',
        death_date_hijri: 124,
        death_date_gregorian: 742,
        geographic_region: 'Madīna / Syria',
        bio_summary:
            'The single most cited Tabi\'ī in the Sunni canon — the foundational link between the Companions and the codified ḥadīth tradition. ' +
            'Commissioned by Caliph ʿUmar ibn ʿAbd al-ʿAzīz to undertake the first state-sanctioned compilation of Prophetic ḥadīth. ' +
            'Direct student of Anas ibn Mālik, ibn ʿUmar, ibn ʿAbbās, and ʿUrwa.',
        bio_taʿdīl:
            'Ibn Ḥajar (Taqrīb): "الفقيه الحافظ متفق على جلالته وإتقانه" ("the jurist, the ḥāfiẓ; agreed-upon for his pre-eminence and precision"). ' +
            'Sufyān al-Thawrī said: "الزهري عندنا أعلم أهل المدينة" ("al-Zuhrī, to us, was the most knowledgeable of the people of Madīna"). ' +
            'al-Layth ibn Saʿd said: "ما رأيت عالماً قط أجمع من ابن شهاب" ("I never saw a scholar more comprehensive than Ibn Shihāb").',
        bio_jarḥ:
            'A minority view (mainly from later Shi\'i scholars) treats his close ties to the Umayyad court as compromising; ' +
            'Sunni rijāl consensus does not. Some early reports note that he engaged in tadlīs (concealing a teacher in the isnād chain), ' +
            'but this was occasional and well-known to his students.',
        reliability_consensus: 'thiqa_thabt',
        reliability_disagreement: true,
        critic_quote_count: 3,
    },
    {
        scholar_indx: 11019,
        tabaqah: 'TABIUN',
        name_english: 'Qatāda ibn Diʿāma al-Sadūsī',
        name_arabic: 'قتادة بن دعامة السدوسي',
        kunya: 'Abū al-Khaṭṭāb',
        nasab: 'ibn Diʿāma ibn Qatāda',
        nisba: 'al-Sadūsī al-Baṣrī',
        death_date_hijri: 117,
        death_date_gregorian: 735,
        geographic_region: 'Baṣra',
        bio_summary:
            'Major Baṣran Tabi\'ī, blind from birth yet possessed of legendary memorisation. Direct student of Anas ibn Mālik. ' +
            'Combined ḥadīth, Qur\'anic exegesis (tafsīr), and Arabic genealogy in a single scholarly programme.',
        bio_taʿdīl:
            'Ibn Sīrīn said: "قتادة أحفظ الناس" ("Qatāda is the most retentive of people"). ' +
            'Aḥmad ibn Ḥanbal said: "قتادة عالم بالتفسير وباختلاف العلماء، كان حافظاً" ("Qatāda was learned in tafsīr and in scholarly disagreement; he was a ḥāfiẓ"). ' +
            'Ibn Ḥajar (Taqrīb): "ثقة ثبت".',
        bio_jarḥ:
            'Documented as a Qadarī (believer in human free will against predestination) — al-Dhahabī notes this openly in Siyar but treats it as a theological matter not affecting his transmission. ' +
            'Like al-Aʿmash, he engaged in tadlīs; his "ʿan-ʿan" chains are accepted only when corroborated.',
        reliability_consensus: 'thiqa',
        reliability_disagreement: true,
        critic_quote_count: 3,
    },
    {
        scholar_indx: 11060,
        tabaqah: 'TABIUN',
        name_english: 'Sulaymān ibn Mihrān — al-Aʿmash',
        name_arabic: 'سليمان بن مِهْران الأعمش',
        kunya: 'Abū Muḥammad',
        nasab: 'ibn Mihrān',
        nisba: 'al-Asadī al-Kūfī (mawlā)',
        death_date_hijri: 148,
        death_date_gregorian: 765,
        geographic_region: 'Kūfa',
        bio_summary:
            'Foremost Kūfan reciter (qārīʾ) and ḥadīth-master of his generation. The Kūfan transmission tradition pivots on him. ' +
            'Direct student of Anas, Mujāhid, and Ibrāhīm al-Nakhaʿī.',
        bio_taʿdīl:
            'Wakīʿ said: "كان الأعمش قريباً من سبعين سنة لم تفته التكبيرة الأولى" ' +
            '("For nearly seventy years al-Aʿmash never missed the opening takbīr of the prayer"). ' +
            'Ibn al-Madīnī said: "كان يحفظ نحواً من أربعة آلاف حديث" ("He memorised around 4,000 ḥadīth"). ' +
            'Ibn Ḥajar (Taqrīb): "ثقة حافظ".',
        bio_jarḥ:
            'Famous for tadlīs (omitting a weak intermediate teacher to make the chain look stronger). Ibn Ḥajar listed him in the second category ' +
            'of mudallisīn — his "ʿan" chains are not automatically accepted unless he explicitly says "samiʿtu" or "ḥaddathanā". ' +
            'This is a methodological caveat, not jarḥ on his honesty or memory.',
        reliability_consensus: 'thiqa',
        reliability_disagreement: false,
        critic_quote_count: 3,
    },

    // ═══ Atbā' al-Tābiʿīn ═══
    {
        scholar_indx: 20001,
        tabaqah: 'ATBA_TABIUN',
        name_english: 'Mālik ibn Anas — Imām Mālik',
        name_arabic: 'مالك بن أنس بن مالك بن أبي عامر الأصبحي',
        kunya: 'Abū ʿAbd Allāh',
        nasab: 'ibn Anas ibn Mālik ibn Abī ʿĀmir',
        nisba: 'al-Aṣbaḥī al-Madanī',
        death_date_hijri: 179,
        death_date_gregorian: 795,
        geographic_region: 'Madīna',
        bio_summary:
            'Eponym of the Mālikī madhhab, author of the Muwaṭṭaʾ (the earliest surviving compiled ḥadīth/fiqh work). ' +
            'Spent his entire life in Madīna, regarded as the foremost authority on the city\'s living scholarly transmission (ʿamal ahl al-Madīna). ' +
            'Direct student of Nāfiʿ (mawlā of ibn ʿUmar) and Ibn Shihāb al-Zuhrī.',
        bio_taʿdīl:
            'al-Shāfiʿī (his student): "إذا ذكر العلماء فمالك النجم، وما أحد أمنّ علي في دين الله من مالك" ' +
            '("When scholars are mentioned, Mālik is the star; no one has been more of a benefactor to me in the religion of Allah than Mālik"). ' +
            'Sufyān ibn ʿUyayna: "مالك عالم أهل الحجاز وهو حجة زمانه". ' +
            'Ibn Ḥajar (Taqrīb): "رأس المتقنين وكبير المتثبتين".',
        reliability_consensus: 'thiqa_thabt',
        critic_quote_count: 3,
    },
    {
        scholar_indx: 20005,
        tabaqah: 'ATBA_TABIUN',
        name_english: 'Sufyān ibn ʿUyayna',
        name_arabic: 'سفيان بن عُيَيْنَة',
        kunya: 'Abū Muḥammad',
        nasab: 'ibn ʿUyayna ibn Maymūn',
        nisba: 'al-Hilālī al-Kūfī thumma al-Makkī',
        death_date_hijri: 198,
        death_date_gregorian: 814,
        geographic_region: 'Kūfa → Makka',
        bio_summary:
            'Foremost ḥadīth-master of Makka in his generation. Direct student of al-Zuhrī, ʿAmr ibn Dīnār, and the major Kūfan masters. ' +
            'Teacher to al-Shāfiʿī, Aḥmad ibn Ḥanbal, and ʿAlī ibn al-Madīnī. al-Bukhārī narrates from him 158 times directly.',
        bio_taʿdīl:
            'al-Shāfiʿī: "لولا مالك وابن عيينة لذهب علم الحجاز" ("Were it not for Mālik and Ibn ʿUyayna, the knowledge of the Hijāz would be lost"). ' +
            'Ibn al-Madīnī: "ما رأيت أحداً أعلم بحديث الزهري من سفيان بن عيينة". ' +
            'Ibn Ḥajar (Taqrīb): "ثقة حافظ فقيه إمام حجة".',
        bio_jarḥ:
            'Mild caveat in the later rijāl tradition: in old age his memorisation deteriorated. Some scholars note that his very late narrations should be cross-checked. ' +
            'Not a personal jarḥ — a methodological one. He was also known to engage in tadlīs but at a much lower frequency than al-Aʿmash.',
        reliability_consensus: 'thiqa',
        critic_quote_count: 3,
    },
    {
        scholar_indx: 20012,
        tabaqah: 'ATBA_TABIUN',
        name_english: 'Sufyān al-Thawrī',
        name_arabic: 'سفيان بن سعيد الثوري',
        kunya: 'Abū ʿAbd Allāh',
        nasab: 'ibn Saʿīd ibn Masrūq',
        nisba: 'al-Thawrī al-Kūfī',
        death_date_hijri: 161,
        death_date_gregorian: 778,
        geographic_region: 'Kūfa → Baṣra (in hiding)',
        bio_summary:
            'Called "amīr al-muʾminīn fī al-ḥadīth" ("commander of the faithful in ḥadīth"). Founded his own short-lived madhhab. ' +
            'Direct student of al-Aʿmash, Ibn Shihāb, and the major Kūfan masters. Refused state office and lived in concealment under the Abbasids.',
        bio_taʿdīl:
            'Shuʿba ibn al-Ḥajjāj (himself an "amīr al-muʾminīn fī al-ḥadīth"): "سفيان أمير المؤمنين في الحديث". ' +
            'Ibn al-Mubārak: "كتبت عن ألف ومائة شيخ، فما كتبت عن أفضل من سفيان". ' +
            'Ibn Ḥajar (Taqrīb): "ثقة حافظ فقيه عابد إمام حجة".',
        bio_jarḥ:
            'Like al-Aʿmash, engaged in tadlīs. Ibn Ḥajar placed him in the second/third tier of mudallisīn. ' +
            'His "ʿan" chains require corroboration in the strict methodology.',
        reliability_consensus: 'thiqa_thabt',
        critic_quote_count: 3,
    },
    {
        scholar_indx: 20020,
        tabaqah: 'ATBA_TABIUN',
        name_english: 'Shuʿba ibn al-Ḥajjāj',
        name_arabic: 'شعبة بن الحجّاج بن الورد',
        kunya: 'Abū Bisṭām',
        nasab: 'ibn al-Ḥajjāj ibn al-Ward',
        nisba: 'al-ʿAtakī al-Wāsiṭī thumma al-Baṣrī',
        death_date_hijri: 160,
        death_date_gregorian: 776,
        geographic_region: 'Baṣra',
        bio_summary:
            'Among the very first systematic ḥadīth-critics. Travelled extensively to verify narrators, originator of much of the formal rijāl ' +
            'methodology that al-Bukhārī and later Sunni critics built on. al-Shāfiʿī called him "amīr al-muʾminīn fī al-ḥadīth".',
        bio_taʿdīl:
            'al-Shāfiʿī: "لولا شعبة لما عُرف الحديث بالعراق" ("Were it not for Shuʿba, ḥadīth would not have been known in Iraq"). ' +
            'Sufyān al-Thawrī: "شعبة أمير المؤمنين في الحديث". ' +
            'Aḥmad ibn Ḥanbal: "ما كان أحد أحسن حديثاً من شعبة كان أمة وحده في هذا الشأن وفي إخراج الرجال".',
        reliability_consensus: 'thiqa_thabt',
        critic_quote_count: 3,
    },
    {
        scholar_indx: 30201,
        tabaqah: 'ATBA_ATBA',
        name_english: 'Abū Bakr ibn Abī Shayba',
        name_arabic: 'أبو بكر بن أبي شيبة - عبد الله بن محمد',
        kunya: 'Abū Bakr',
        nasab: 'ʿAbd Allāh ibn Muḥammad ibn Abī Shayba Ibrāhīm',
        nisba: 'al-ʿAbsī al-Kūfī',
        death_date_hijri: 235,
        death_date_gregorian: 849,
        geographic_region: 'Kūfa',
        bio_summary:
            'Author of the Muṣannaf — one of the foundational works of early Sunni ḥadīth collection. Direct teacher of al-Bukhārī (who narrates ' +
            'from him 1,541 times), Muslim, Abū Dāwūd, and Ibn Mājah. Brother of ʿUthmān ibn Abī Shayba (also a major narrator).',
        bio_taʿdīl:
            'Aḥmad ibn Ḥanbal: "أبو بكر صدوق وهو أحب إليّ من أخيه عثمان". ' +
            'al-ʿIjlī: "ثقة كان حافظاً للحديث". ' +
            'Ibn Ḥajar (Taqrīb): "ثقة حافظ صاحب تصانيف".',
        reliability_consensus: 'thiqa',
        critic_quote_count: 3,
    },
    {
        scholar_indx: 30367,
        tabaqah: 'ATBA_ATBA',
        name_english: 'Qutayba ibn Saʿīd',
        name_arabic: 'قتيبة بن سعيد بن جميل البلخي البغلاني',
        kunya: 'Abū Rajāʾ',
        nasab: 'ibn Saʿīd ibn Jamīl ibn Ṭarīf',
        nisba: 'al-Thaqafī al-Balkhī al-Baghlānī',
        death_date_hijri: 240,
        death_date_gregorian: 854,
        geographic_region: 'Balkh (modern northern Afghanistan)',
        bio_summary:
            'One of the most-cited direct sources for the Six Books: appears as a direct teacher of al-Bukhārī, Muslim, Abū Dāwūd, al-Tirmidhī, and al-Nasāʾī. ' +
            'Travelled extensively (al-Hijāz, Iraq, Syria, Egypt) collecting from senior authorities. Foundational link from Khurasan to the central ḥadīth tradition.',
        bio_taʿdīl:
            'Ibn Maʿīn: "قتيبة بن سعيد ثقة". ' +
            'al-Nasāʾī: "ثقة صدوق". ' +
            'Ibn Ḥajar (Taqrīb): "ثقة ثبت".',
        reliability_consensus: 'thiqa_thabt',
        critic_quote_count: 3,
    },
];

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
    const dryRun = process.argv.includes('--dry-run');
    console.log(`[seed-narrator-bios-phase0] mode=${dryRun ? 'DRY-RUN' : 'WRITE'}`);
    console.log(`[seed-narrator-bios-phase0] ${BIOS.length} narrator bios prepared`);

    let updated = 0;
    let missing = 0;
    let errors = 0;

    for (const bio of BIOS) {
        try {
            const fields = {
                scholar_indx: bio.scholar_indx,
                is_prophet: bio.is_prophet ?? false,
                is_companion: bio.is_companion ?? false,
                tabaqah: bio.tabaqah,
                name_english_clean: bio.name_english,
                name_arabic_clean: bio.name_arabic,
                kunya: bio.kunya ?? null,
                nasab: bio.nasab ?? null,
                nisba: bio.nisba ?? null,
                death_date_hijri: bio.death_date_hijri ?? null,
                death_date_gregorian: bio.death_date_gregorian ?? null,
                geographic_region: bio.geographic_region ?? null,
                bio_summary: bio.bio_summary,
                bio_tadil: bio.bio_taʿdīl ?? null,
                bio_jarh: bio.bio_jarḥ ?? null,
                reliability_consensus: bio.reliability_consensus,
                reliability_disagreement: bio.reliability_disagreement ?? false,
                critic_quote_count: bio.critic_quote_count ?? 0,
                bio_provenance: 'manual_phase_0',
            };
            if (dryRun) {
                console.log(`  [${bio.scholar_indx}] ${bio.name_english} → ${bio.reliability_consensus}` +
                    (bio.reliability_disagreement ? '  (contested)' : ''));
                updated++;
                continue;
            }
            // Idempotent: MATCH the existing narrator (we don't create new ones — only enrich
            // ones already loaded by bulkLoadNarrators). Backfilled new clean-name fields don't
            // overwrite the source-of-truth `name` field; they sit alongside as canonical labels.
            const result = await runWrite<{ scholar_indx: number }>(
                `MATCH (n:Narrator { scholar_indx: $scholar_indx })
                 SET
                     n.is_prophet                  = $is_prophet,
                     n.is_companion                = $is_companion,
                     n.tabaqah                     = $tabaqah,
                     n.name_english_clean          = $name_english_clean,
                     n.name_arabic_clean           = $name_arabic_clean,
                     n.kunya                       = $kunya,
                     n.nasab                       = $nasab,
                     n.nisba                       = $nisba,
                     n.death_date_hijri            = coalesce(n.death_date_hijri, $death_date_hijri),
                     n.death_date_gregorian        = coalesce(n.death_date_gregorian, $death_date_gregorian),
                     n.geographic_region           = $geographic_region,
                     n.bio_summary                 = $bio_summary,
                     n.bio_tadil                   = $bio_tadil,
                     n.bio_jarh                    = $bio_jarh,
                     n.reliability_consensus       = $reliability_consensus,
                     n.reliability_disagreement    = $reliability_disagreement,
                     n.critic_quote_count          = $critic_quote_count,
                     n.bio_provenance              = $bio_provenance,
                     n.bio_updated_at              = datetime()
                 RETURN n.scholar_indx AS scholar_indx`,
                fields,
            );
            if (result.length === 0) {
                console.warn(`  [${bio.scholar_indx}] MISSING — no :Narrator node with this scholar_indx in DB`);
                missing++;
            } else {
                updated++;
            }
        } catch (err) {
            errors++;
            console.error(`  [${bio.scholar_indx}] ERROR: ${err}`);
        }
    }

    console.log('\n' + '='.repeat(60));
    console.log(`  Phase 0 seeding complete`);
    console.log(`  updated: ${updated}  missing: ${missing}  errors: ${errors}`);
    console.log('='.repeat(60));

    await closeDriver();
    if (errors > 0) process.exitCode = 1;
}

main().catch(async (err) => {
    console.error('[seed-narrator-bios-phase0] fatal:', err);
    try { await closeDriver(); } catch {}
    process.exitCode = 1;
});
