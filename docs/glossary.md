# Glossary

<!-- Generated from src/lib/glossary/terms.ts by `npx tsx src/lib/glossary/generate-doc.ts`. Do not edit by hand. -->

Definitions of the terms used in the Shura wa Istehsan app, its documentation and its data. The same entries render at `/glossary`.

**Transliteration.** Arabic terms are written in a simple scheme: no long-vowel or dot marks; ʿ for ʿayn and ʾ for hamza (not written at the start of a word); th, dh, kh, sh and gh for single Arabic letters; doubled letters written twice; the article always as al-; ta marbuta as -a. Words already common in English (hadith, isnad, Sunni, Imami, Zaydi, Ibadi) keep their usual spelling.

## Sections

- [Traditions](#section-traditions) (4)
- [Names](#section-names) (7)
- [Transmission](#section-transmission) (33)
- [Narrator criticism](#section-narrator-criticism) (11)
- [Report grading](#section-report-grading) (16)
- [Works and genres](#section-works) (10)
- [Comparative study and history](#section-comparative) (13)
- [Archive terms](#section-archive) (57)
- [Needs the owner’s review](#owner-review)
- [Enum values without an entry](#enum-values-without-an-entry)

<a id="section-traditions"></a>

## Traditions

<a id="ibadi"></a>

### Ibadi · الإباضية

A Muslim tradition that traces its origins to scholars of early Basra and is found today mainly in Oman and parts of North Africa.

- **In this archive:** Its reports here come from al-Jamiʿ al-Sahih, the Musnad of al-Rabiʿ ibn Habib. The archive holds no per-report gradings for Ibadi works.
- **Related:** [Ibadi acceptance of reports](#ibadi-report-acceptance), [jamiʿ](#jami), [sahih (collection)](#sahih-collection)
- **Data values:** `hadith_tradition.Ibadi`

<a id="imami"></a>

### Imami (Twelver Shiʿi) · الإمامية

The Shiʿi tradition that recognises twelve Imams from the Prophet’s family and transmits their sayings as hadith alongside the Prophet’s.

- **In this archive:** Imami reports come chiefly from the Four Books and related works. Their gradings are rulings by named later scholars, such as al-Majlisi, each with a citation.
- **Related:** [al-kutub al-arbaʿa](#four-books), [Imami grading](#imami-grading), [Report from an Imam](#imam-report)
- **Data values:** `hadith_tradition.Imami`

<a id="sunni"></a>

### Sunni · أهل السنة والجماعة

The tradition of Ahl al-Sunna wa al-Jamaʿa, the largest body of Muslims, whose best-known hadith collections are the Six Books.

- **In this archive:** Gradings shown are statements by a named compiler or critic. The archive does not compute a grade of its own.
- **Related:** [al-kutub al-sitta](#six-books), [Sunni grading](#sunni-grading)
- **Data values:** `hadith_tradition.Sunni`

<a id="zaydi"></a>

### Zaydi · الزيدية

The Shiʿi tradition named after Zayd ibn ʿAli ibn al-Husayn, historically centred in Yemen.

- **In this archive:** Its reports here come from Musnad al-Imam Zayd ibn ʿAli. The archive holds no per-report gradings for Zaydi works.
- **Related:** [Zaydi acceptance of reports](#zaydi-report-acceptance), [musnad](#musnad), [amali](#amali)
- **Data values:** `hadith_tradition.Zaydi`

<a id="section-names"></a>

## Names

<a id="ism"></a>

### ism (given name) · اسم

A person’s own given name, such as Muhammad, ʿAli or ʿAʾisha.

- **In this archive:** A given name on its own is shared by many narrators, so the archive never identifies a person from it alone.
- **Related:** [kunya](#kunya), [nasab](#nasab), [nisba](#nisba), [laqab](#laqab), [Kunya-only and single-name mentions](#single-name-mention)

<a id="kunya"></a>

### kunya (teknonym) · كنية

A name of the form “father of” (Abu) or “mother of” (Umm) followed by another name, such as Abu Hurayra or Umm Salama, used as a respectful way of naming someone.

- **In this archive:** Many narrators share the same kunya. A chain that names someone only by kunya is never treated as identified by itself; an automatic match on a kunya alone is labelled “matched by kunya only”.
- **Across traditions:** In Imami chains, Abu ʿAbd Allah and Abu Jaʿfar usually refer to particular Imams (Jaʿfar al-Sadiq and Muhammad al-Baqir), while in other chains the same kunyas refer to many different people. Context, not the kunya, settles who is meant.
- **Related:** [Kunya-only and single-name mentions](#single-name-mention), [Matched by kunya only](#matched-by-kunya-only), [ism](#ism), [mushtarak](#mushtarak)

<a id="nasab"></a>

### nasab (lineage) · نسب

The chain of “son of” (ibn) or “daughter of” (bint) that names a person’s father and earlier ancestors.

- **In this archive:** A name with a nasab is more specific than a single name, which is why the archive’s narrator matching allows some spelling folds only for names that carry one.
- **Related:** [ism](#ism), [kunya](#kunya), [Kunya-only and single-name mentions](#single-name-mention)

<a id="nisba"></a>

### nisba (relational name) · نسبة

A name ending in -i that ties a person to a place, tribe, trade or school, such as al-Kufi (of Kufa) or al-Zuhri (of the Zuhra clan).

- **In this archive:** A nisba alone, like a single name, can point to more than one narrator.
- **Related:** [ism](#ism), [laqab](#laqab), [mushtarak](#mushtarak)

<a id="laqab"></a>

### laqab (epithet) · لقب

A descriptive title or nickname, such as al-Sadiq (the truthful) or al-Aʿmash (the bleary-eyed).

- **In this archive:** Identity decisions based only on a laqab require a citation before a curator may record them.
- **Related:** [ism](#ism), [kunya](#kunya), [nisba](#nisba)

<a id="single-name-mention"></a>

### Kunya-only and single-name mentions

A place in a chain where a narrator is named only by a kunya, a single given name or a single epithet, which many different people share.

- **In this archive:** Such a mention does not identify a person. The archive shows it as written and leaves it unidentified unless a curator records a cited decision; lexicon entries that are only a kunya or a single word are never used as match targets.
- **Across traditions:** Critics in every tradition resolve such names from context: who the narrator heard from, who heard from him, and his generation.
- **Related:** [kunya](#kunya), [ism](#ism), [mushtarak](#mushtarak), [Not yet identified](#not-yet-identified), [Placeholder entry](#placeholder-entry)

<a id="mushtarak"></a>

### mushtarak (shared name) · المشترك

A name borne by two or more narrators; telling them apart (tamyiz al-mushtarakat) is a recognised branch of narrator study.

- **In this archive:** Because the same name can mean different people depending on teacher and student, identity decisions are recorded for a name in its context, not for the name everywhere.
- **Related:** [Kunya-only and single-name mentions](#single-name-mention), [Review unit](#review-unit), [Identity decision](#identity-decision)

<a id="section-transmission"></a>

## Transmission

<a id="hadith"></a>

### hadith · حديث

A report of what the Prophet said, did or approved, carried by a chain of named narrators; the word is also used for the whole body of such reports.

- **Across traditions:** Sunni, Zaydi and Ibadi usage centres on reports from the Prophet. Imami usage also includes the sayings of the twelve Imams (and of Fatima), regarded in that tradition as authoritative teachers.
- **Related:** [khabar](#khabar), [athar](#athar), [isnad](#isnad), [matn](#matn), [Report from an Imam](#imam-report)

<a id="khabar"></a>

### khabar (report) · خبر

A report; some scholars use it as another word for hadith, while others reserve it for reports about people other than the Prophet.

- **Across traditions:** Imami writing commonly uses khabar (plural akhbar) for reports from the Prophet and the Imams.
- **Related:** [hadith](#hadith), [athar](#athar), [riwaya](#riwaya)

<a id="athar"></a>

### athar (report, trace) · أثر

A transmitted report; many scholars use it especially for sayings of Companions and Followers, while others apply it to any report, including the Prophet’s.

- **Related:** [hadith](#hadith), [khabar](#khabar), [mawquf](#mawquf), [maqtuʿ](#maqtu)

<a id="riwaya"></a>

### riwaya (transmission) · رواية

The act of passing on a report, or one particular transmitted version of it.

- **In this archive:** Different versions of a report kept in the archive are shown under “Variant texts”.
- **Related:** [rawi](#rawi), [hadith](#hadith), [isnad](#isnad)

<a id="isnad"></a>

### isnad (chain of transmission) · إسناد

The list of narrators through whom a report reached the compiler, each said to have received it from the next; sanad is usually used as a synonym.

- **In this archive:** The isnad is always shown as written in the Arabic source. Narrators are linked to their profiles only where the identification meets the archive’s rules; every other name stays plain text.
- **Related:** [matn](#matn), [rawi](#rawi), [Chain status](#chain-status), [Mention](#mention), [tahwil](#tahwil)

<a id="matn"></a>

### matn (report text) · متن

The content of a report itself, the words that follow the chain of narrators.

- **In this archive:** Shown as “Matn · report text” when the source text can be split from its chain, otherwise as “Text as in the source”.
- **Related:** [isnad](#isnad), [hadith](#hadith)

<a id="rawi"></a>

### rawi (narrator) · راوٍ

A person who passes on a report they received; one link in an isnad.

- **In this archive:** Narrator pages collect what the archive knows about one person, with each claim attributed to its source.
- **Related:** [isnad](#isnad), [tabaqa](#tabaqa), [al-jarh wa al-taʿdil](#jarh-wa-tadil)
- **Data values:** `narrator_authority.rawi`

<a id="tabaqa"></a>

### tabaqa (generation) · طبقة

A generation or layer of narrators who lived and transmitted at about the same time, used to check that a student could have heard from a teacher.

- **In this archive:** Narrator pages show the generation on a short scale: the Prophet, Companions, Followers, Followers of the Followers, and later scholars. It is highlighted only when it is recorded.
- **Across traditions:** Critics divide generations differently: some use broad layers like these, others finer divisions (Ibn Hajar uses twelve). Imami narrator works often group narrators by the Imam they transmitted from instead.
- **Related:** [sahabi](#sahabi), [tabiʿi](#tabii), [atbaʿ al-tabiʿin](#atba-al-tabiin)
- **Data values:** `tabaqah_class.ATBA_ATBA`, `tabaqah_class.LATER_SCHOLAR`

<a id="sahabi"></a>

### sahabi (Companion) · صحابي

A person who met the Prophet as a believer; the Companions (sahaba) are the first generation of narrators.

- **Across traditions:** Traditions differ on how Companions are assessed as narrators: Sunni scholarship holds them collectively upright, while Imami scholarship, among others, assesses them individually. Imami works also speak of the “companions” (ashab) of each Imam.
- **Related:** [tabaqa](#tabaqa), [tabiʿi](#tabii), [ʿadalat al-sahaba](#adalat-al-sahaba)
- **Data values:** `tabaqah_class.SAHABA`

<a id="tabii"></a>

### tabiʿi (Follower) · تابعي

A person of the generation after the Companions who met and learned from at least one Companion.

- **Related:** [tabaqa](#tabaqa), [sahabi](#sahabi), [atbaʿ al-tabiʿin](#atba-al-tabiin), [maqtuʿ](#maqtu)
- **Data values:** `tabaqah_class.TABIUN`

<a id="atba-al-tabiin"></a>

### atbaʿ al-tabiʿin (Followers of the Followers) · أتباع التابعين

The generation that learned from the Followers, the third generation of narrators.

- **Related:** [tabaqa](#tabaqa), [tabiʿi](#tabii)
- **Data values:** `tabaqah_class.ATBA_TABIUN`

<a id="imam-report"></a>

### Report from an Imam

A report whose chain ends at one of the Imams rather than at the Prophet.

- **In this archive:** Recorded as the narration level “imam”.
- **Across traditions:** In Imami usage such a report is a hadith in the full sense. Sunni terminology classifies a saying by the speaker’s generation, so the same words would be mawquf (from ʿAli, a Companion) or maqtuʿ (from a later Imam).
- **Related:** [hadith](#hadith), [marfuʿ](#marfu), [mawquf](#mawquf), [maqtuʿ](#maqtu), [Imami](#imami)
- **Data values:** `narration_level.imam`

<a id="mudmar"></a>

### mudmar (with the source unnamed) · مضمر

A report in which the narrator refers to the Imam he asked only by a pronoun, such as “I asked him”, without naming him.

- **In this archive:** The term appears in Imami gradings carried by the data.
- **Across traditions:** An Imami term. Imami scholars discuss when such a report can be relied on, for example when the narrator is known to have put questions only to an Imam.
- **Related:** [mursal](#mursal), [Report from an Imam](#imam-report), [Imami grading](#imami-grading)

<a id="haddathana"></a>

### haddathana (“he narrated to us”) · حدّثنا

A transmission formula stating that the teacher narrated the report to the speaker, ordinarily meaning it was heard directly.

- **Across traditions:** The same formulas appear in chains of all four traditions. Conventions for reading them were set by critics and are not identical between them.
- **Related:** [akhbarana](#akhbarana), [samiʿtu](#samitu), [ʿan](#an), [qala](#qala)

<a id="akhbarana"></a>

### akhbarana (“he informed us”) · أخبرنا

A transmission formula stating that the teacher informed the speaker of the report.

- **Across traditions:** Usage differs: some critics treat it as equivalent to haddathana, while others reserve it for a text read aloud to the teacher and confirmed by him.
- **Related:** [haddathana](#haddathana), [samiʿtu](#samitu), [ʿan](#an)

<a id="an"></a>

### ʿan (“from”) · عن

A formula saying only that the report came “from” a narrator, without stating how it was received; a chain linked this way is called muʿanʿan.

- **Across traditions:** Critics differ on when ʿan counts as direct transmission: some require that the two narrators are known to have met, others accept that they lived at the same time. For a narrator known for tadlis it is not taken as proof of hearing.
- **Related:** [tadlis](#tadlis), [samiʿtu](#samitu), [haddathana](#haddathana), [qala](#qala)

<a id="samitu"></a>

### samiʿtu (“I heard”) · سمعت

A formula in which the narrator states that he heard the report directly from the person named.

- **In this archive:** The formula records the narrator’s claim; it does not by itself verify who the person named is.
- **Related:** [haddathana](#haddathana), [ʿan](#an)

<a id="qala"></a>

### qala (“he said”) · قال

A formula attributing words to a narrator without stating how they were received; like ʿan, it does not on its own show direct hearing.

- **Related:** [ʿan](#an), [muʿallaq](#muallaq), [Compiler’s statement](#compiler-statement)

<a id="tahwil"></a>

### tahwil (switch of chain) · تحويل (ح)

A switch from one chain to another partway through an isnad, marked by the letter ح, so that two or more chains share their later part.

- **In this archive:** The archive follows each branch at a ح and joins branches only where the Arabic shows where they meet; where it cannot tell, the branches stay separate rather than being guessed together.
- **Related:** [isnad](#isnad), [mutabaʿa](#mutaba)

<a id="mutaba"></a>

### mutabaʿa (corroborating transmission) · متابعة

A second transmission of the same report through another narrator who shares a teacher, or a teacher higher up, with the first.

- **Across traditions:** Some critics separate mutabaʿa from shahid by whether the same Companion is involved, others by whether the wording or only the meaning agrees.
- **Related:** [shahid](#shahid), [gharib](#gharib)

<a id="shahid"></a>

### shahid (supporting report) · شاهد

A separate report, usually from a different Companion, that supports the meaning of another report.

- **Related:** [mutabaʿa](#mutaba), [gharib](#gharib)

<a id="mursal"></a>

### mursal (with a link omitted) · مرسل

A report whose chain leaves out a narrator, classically a Follower quoting the Prophet without naming the Companion.

- **In this archive:** Appears both as a description of a chain and as a grade in Imami gradings.
- **Across traditions:** In Imami usage the term is broader: any report whose chain drops a narrator or names one only vaguely (“from a man”). Whether mursal reports can be accepted is disputed within each tradition, and some scholars accept those of particular narrators.
- **Related:** [munqatiʿ](#munqati), [muʿdal](#mudal), [muʿallaq](#muallaq), [mubham](#mubham), [Imami grading](#imami-grading)
- **Data values:** `grade_canonical.mursal`

<a id="munqati"></a>

### munqatiʿ (broken) · منقطع

A report whose chain is broken by one or more missing narrators; some critics use it for any break, others only for a single missing link.

- **Related:** [mursal](#mursal), [muʿdal](#mudal), [muʿallaq](#muallaq)

<a id="mudal"></a>

### muʿdal (doubly broken) · معضل

A report whose chain is missing two or more narrators in succession.

- **Related:** [munqatiʿ](#munqati), [mursal](#mursal)

<a id="muallaq"></a>

### muʿallaq (suspended) · معلق

A report whose chain is cut at the compiler’s end, with one or more of the compiler’s own authorities left out; al-Bukhari’s Sahih contains many.

- **Related:** [munqatiʿ](#munqati), [qala](#qala)

<a id="mubham"></a>

### mubham (unnamed narrator) · مبهم

A narrator referred to without a name, such as “a man” or “a shaykh”.

- **In this archive:** Recorded as an anonymous link: it is part of the chain, but it never identifies a person.
- **Related:** [Collective mention](#collective-mention), [mursal](#mursal), [majhul](#majhul)
- **Data values:** `link_kind.anonymous`, `surface_decision_kind.anonymous`

<a id="marfu"></a>

### marfuʿ (raised (to the Prophet)) · مرفوع

A report attributed to the Prophet himself, whatever the state of its chain.

- **In this archive:** Recorded as the narration level “marfu”.
- **Across traditions:** In some Imami grading notes, marfuʿ instead describes a chain in which a narrator “raised” the report to the Imam with the intermediate narrators left out.
- **Related:** [mawquf](#mawquf), [maqtuʿ](#maqtu), [Report from an Imam](#imam-report), [mursal](#mursal)
- **Data values:** `narration_level.marfu`

<a id="mawquf"></a>

### mawquf (stopped (at a Companion)) · موقوف

A report whose chain stops at a Companion, giving the Companion’s own words or deeds rather than the Prophet’s.

- **In this archive:** Recorded as the narration level “mawquf”.
- **Across traditions:** Imami works on hadith terms define it relative to the Prophet or an Imam: a report that stops at someone other than them.
- **Related:** [marfuʿ](#marfu), [maqtuʿ](#maqtu), [athar](#athar)
- **Data values:** `narration_level.mawquf`

<a id="maqtu"></a>

### maqtuʿ (ending at a Follower) · مقطوع

A report whose chain stops at a Follower or someone later, giving that person’s own words.

- **In this archive:** Recorded as the narration level “maqtu”. Not to be confused with munqatiʿ, which describes a broken chain.
- **Related:** [mawquf](#mawquf), [marfuʿ](#marfu), [munqatiʿ](#munqati)
- **Data values:** `narration_level.maqtu`

<a id="mutawatir"></a>

### mutawatir (mass-transmitted) · متواتر

A report carried by so many independent narrators at every stage that their agreement on a falsehood is considered impossible.

- **Across traditions:** All four traditions use the distinction, but scholars differ on how many narrators are needed and on which reports qualify.
- **Related:** [ahad](#ahad)

<a id="ahad"></a>

### ahad (solitary reports) · آحاد

A report that does not reach the level of mutawatir; most reports are ahad.

- **Across traditions:** Traditions and schools within them differ on what weight an ahad report carries in belief and in law.
- **Related:** [mutawatir](#mutawatir), [gharib](#gharib)

<a id="illa"></a>

### ʿilla (hidden defect) · علة

A hidden flaw in a report that looks sound on the surface, such as an unnoticed break or a misattribution, found by comparing its transmissions.

- **Related:** [sahih](#sahih), [tadlis](#tadlis)

<a id="tadlis"></a>

### tadlis (concealment) · تدليس

Transmitting in a way that hides a gap or a weak narrator, for example using ʿan for something not heard directly; a narrator who does this is a mudallis.

- **Related:** [ʿan](#an), [ʿilla](#illa)

<a id="section-narrator-criticism"></a>

## Narrator criticism

<a id="jarh-wa-tadil"></a>

### al-jarh wa al-taʿdil (criticism and praise) · الجرح والتعديل

The assessment of narrators, recording critics’ judgements that weaken (jarh) or support (taʿdil) a narrator’s reliability.

- **In this archive:** Each verdict is meant to be shown with its critic and tradition. Terms and their weight differ between critics and between traditions, so the archive does not convert one critic’s word into another’s.
- **Related:** [ʿadala](#adala), [dabt](#dabt), [thiqa](#thiqa), [daʿif](#daif), [Narrator verdict](#narrator-verdict), [rijal](#rijal)
- **Data values:** `narrator_assessment_kind.critic_ruling`

<a id="adala"></a>

### ʿadala (probity) · عدالة

A narrator’s religious and moral integrity, one of the two qualities critics require before trusting a report.

- **Across traditions:** What ʿadala requires differs: in the Imami scheme a fully sound (sahih) chain needs narrators who are Imami as well as upright, while Sunni critics do not make school membership a condition in the same way.
- **Related:** [dabt](#dabt), [al-jarh wa al-taʿdil](#jarh-wa-tadil), [ʿadalat al-sahaba](#adalat-al-sahaba)

<a id="dabt"></a>

### dabt (accuracy) · ضبط

A narrator’s precision in preserving a report, from memory or in writing, the second quality critics require.

- **Related:** [ʿadala](#adala), [thiqa](#thiqa), [saduq](#saduq)

<a id="thiqa"></a>

### thiqa (trustworthy) · ثقة

A narrator judged both upright and accurate; “thiqa thabt” (ثقة ثبت) adds that he is especially firm and precise.

- **Across traditions:** Used by critics of every tradition, but a critic’s thiqa vouches for a narrator by that critic’s own standards, which differ.
- **Related:** [saduq](#saduq), [la baʾsa bihi](#la-basa-bihi), [al-jarh wa al-taʿdil](#jarh-wa-tadil)
- **Data values:** `narrator_verdict.thiqa`, `narrator_verdict.thiqa_thabt`

<a id="saduq"></a>

### saduq (truthful) · صدوق

A narrator judged honest, with accuracy a little below that of a thiqa.

- **Across traditions:** Its exact rank differs between critics, as with most grading words.
- **Related:** [thiqa](#thiqa), [la baʾsa bihi](#la-basa-bihi), [hasan](#hasan)
- **Data values:** `narrator_verdict.saduq`

<a id="la-basa-bihi"></a>

### la baʾsa bihi (“no harm in him”) · لا بأس به

A mild positive verdict: the narrator is acceptable.

- **Across traditions:** Its weight depends on the critic; by a widely cited report, Yahya ibn Maʿin used it as close to thiqa.
- **Related:** [saduq](#saduq), [thiqa](#thiqa)
- **Data values:** `narrator_verdict.la_basa_bihi`

<a id="majhul"></a>

### majhul (unknown) · مجهول

A narrator whose identity or reliability is not established in the critics’ sources; for a report, a chain that contains such a narrator.

- **In this archive:** Appears both as a narrator verdict and as a grade in Imami gradings. It records missing knowledge, not a finding of unreliability.
- **Across traditions:** Sunni critics distinguish a narrator unknown in person from one unknown in reliability. Imami critics use majhul for a narrator described as unknown, and some separate this from a narrator not mentioned at all (muhmal).
- **Related:** [mubham](#mubham), [daʿif](#daif), [Imami grading](#imami-grading), [al-jarh wa al-taʿdil](#jarh-wa-tadil)
- **Data values:** `narrator_verdict.majhul`, `grade_canonical.majhul`

<a id="matruk"></a>

### matruk (abandoned) · متروك

A narrator so seriously criticised that his reports are set aside entirely, not used even as support.

- **Related:** [daʿif](#daif), [kadhdhab](#kadhdhab)
- **Data values:** `narrator_verdict.matruk`

<a id="kadhdhab"></a>

### kadhdhab (liar) · كذّاب

The gravest verdict: a narrator accused of lying in his reports.

- **Related:** [matruk](#matruk), [mawduʿ](#mawdu)
- **Data values:** `narrator_verdict.kadhab`

<a id="mukhtalaf-fihi"></a>

### mukhtalaf fihi (disputed) · مختلف فيه

Said of a narrator, or a grading, on which critics disagree.

- **In this archive:** The archive keeps disagreeing verdicts side by side rather than choosing one.
- **Related:** [al-jarh wa al-taʿdil](#jarh-wa-tadil), [Narrator verdict](#narrator-verdict)
- **Data values:** `narrator_verdict.mukhtalaf_fihi`, `grade_canonical.mukhtalaf`

<a id="adalat-al-sahaba"></a>

### ʿadalat al-sahaba (probity of the Companions) · عدالة الصحابة

The position that every Companion is upright as a narrator and need not be individually assessed.

- **In this archive:** Where the data records no verdict for a Companion because of this position, it stores “not applicable”, and the narrator page currently displays this label.
- **Across traditions:** A Sunni position. Imami scholarship assesses Companions individually, and Zaydi and Ibadi scholarship also hold their own views; the archive does not rule between them.
- **Related:** [sahabi](#sahabi), [ʿadala](#adala), [Narrator verdict](#narrator-verdict)
- **Data values:** `narrator_verdict.not_applicable`

<a id="section-report-grading"></a>

## Report grading

<a id="sunni-grading"></a>

### Sunni grading

Sunni critics grade a report mainly as sahih, hasan or daʿif, and a fabricated report as mawduʿ, judging the continuity of the chain, the narrators, and the absence of hidden defects.

- **In this archive:** Sunni grades here are statements by a named compiler, such as al-Tirmidhi’s remarks after each report, or a compiler’s stated criterion; they are never computed.
- **Across traditions:** Individual critics often disagree about the same report.
- **Related:** [sahih](#sahih), [hasan](#hasan), [daʿif](#daif), [mawduʿ](#mawdu), [hasan sahih](#hasan-sahih), [Compiler’s statement](#compiler-statement)

<a id="imami-grading"></a>

### Imami grading

The Imami four-part scheme grades a chain as sahih, hasan, muwaththaq or daʿif according to the school and standing of its narrators.

- **In this archive:** Imami grades here are rulings by named scholars, mostly al-Majlisi, with Behbudi, Mohseni and al-Najafi, each with a citation; entries such as “not included” or “silent” are not shown as grades.
- **Across traditions:** The scheme was formalised by Imami scholars in the 7th/13th century. Many Imami scholars, earlier and later, also accept a report on other evidence, so a chain grade is not the only measure.
- **Related:** [sahih](#sahih), [hasan](#hasan), [muwaththaq](#muwaththaq), [daʿif](#daif), [daʿif ʿala al-mashhur](#daif-ala-al-mashhur), [muʿtabar](#mutabar), [majhul](#majhul), [mursal](#mursal)

<a id="sahih"></a>

### sahih (sound) · صحيح

The highest grade: a report whose chain and narrators meet the grader’s full standard.

- **Across traditions:** Sunni: an unbroken chain of upright, accurate narrators, free of irregularity and hidden defect. Imami: an unbroken chain to the Imam or Prophet of narrators who are Imami and declared upright. The same word therefore names different tests.
- **Related:** [hasan](#hasan), [sahih (collection)](#sahih-collection), [ka-al-sahih](#kal-sahih), [Sunni grading](#sunni-grading), [Imami grading](#imami-grading)
- **Data values:** `grade_canonical.sahih`

<a id="hasan"></a>

### hasan (good) · حسن

An acceptable grade below sahih.

- **Across traditions:** Sunni: the narrators are upright but somewhat less accurate. Imami: the narrators are Imami and at least one is praised without being explicitly declared trustworthy.
- **Related:** [sahih](#sahih), [hasan sahih](#hasan-sahih), [hasan gharib](#hasan-gharib), [saduq](#saduq)
- **Data values:** `grade_canonical.hasan`

<a id="muwaththaq"></a>

### muwaththaq (reliable) · موثق

An Imami grade for a chain that includes a narrator from outside the Imami school who is declared trustworthy.

- **Related:** [Imami grading](#imami-grading), [sahih](#sahih), [thiqa](#thiqa)
- **Data values:** `grade_canonical.muwaththaq`

<a id="daif"></a>

### daʿif (weak) · ضعيف

Weak: said of a report whose chain or narrators fall short of the grader’s standard, or of a narrator whose reliability critics doubt.

- **In this archive:** A weak grade is a judgement on the chain as assessed by that grader. It is not a statement that the content is false.
- **Across traditions:** Sunni and Imami critics both use it, under their own standards; whether and how weak reports may be used differs between scholars.
- **Related:** [daʿif ʿala al-mashhur](#daif-ala-al-mashhur), [matruk](#matruk), [mawduʿ](#mawdu), [sahih](#sahih)
- **Data values:** `grade_canonical.da_if`, `narrator_verdict.daif`

<a id="mawdu"></a>

### mawduʿ (fabricated) · موضوع

A report judged to be invented and falsely attributed.

- **Related:** [kadhdhab](#kadhdhab), [daʿif](#daif)
- **Data values:** `grade_canonical.mawdu`

<a id="hasan-sahih"></a>

### hasan sahih · حسن صحيح

A compound grade used by al-Tirmidhi after many reports in his Jamiʿ.

- **In this archive:** Shown as al-Tirmidhi’s own statement, in his words.
- **Across traditions:** Scholars differ on what he meant: among the explanations are that the report has two chains, one of each grade, or that critics hesitated between the two grades.
- **Related:** [hasan gharib](#hasan-gharib), [gharib](#gharib), [Compiler’s statement](#compiler-statement), [Sunni grading](#sunni-grading)

<a id="hasan-gharib"></a>

### hasan gharib · حسن غريب

A compound grade used by al-Tirmidhi for a report he considers hasan that is known through a single line of transmission; he also writes hasan sahih gharib.

- **In this archive:** Shown as al-Tirmidhi’s own statement, in his words.
- **Related:** [hasan sahih](#hasan-sahih), [gharib](#gharib), [Compiler’s statement](#compiler-statement)

<a id="gharib"></a>

### gharib (singular) · غريب

A report transmitted by only one narrator at some point in its chain; it describes how the report travelled, not by itself its strength.

- **Related:** [ahad](#ahad), [hasan gharib](#hasan-gharib), [mutabaʿa](#mutaba)

<a id="daif-ala-al-mashhur"></a>

### daʿif ʿala al-mashhur (weak on the prevailing view) · ضعيف على المشهور

An Imami grading phrase meaning the chain is weak according to the prevailing view of one of its narrators, signalling that other scholars judge him better.

- **In this archive:** It appears in al-Majlisi’s gradings in the data and is kept in his words.
- **Related:** [daʿif](#daif), [Imami grading](#imami-grading), [muʿtabar](#mutabar)

<a id="mutabar"></a>

### muʿtabar (considered reliable) · معتبر

A grading word for a report that a scholar considers reliable enough to act on, whatever its formal chain grade.

- **In this archive:** Appears in Imami gradings in the data and is kept in the grader’s words.
- **Related:** [Imami grading](#imami-grading), [daʿif ʿala al-mashhur](#daif-ala-al-mashhur)
- **Data values:** `grade_canonical.mu_tabar`

<a id="kal-sahih"></a>

### ka-al-sahih (like sahih) · كالصحيح

A qualifier in Imami gradings, as in “hasan ka-al-sahih”, meaning the grader treats the report as close to sahih while giving it a lower formal grade.

- **In this archive:** Kept in the grader’s words.
- **Related:** [sahih](#sahih), [hasan](#hasan), [Imami grading](#imami-grading)

<a id="thabit"></a>

### thabit (established) · ثابت

A word meaning “established”, which some critics use for an accepted report.

- **In this archive:** One upstream dataset puts ثابت on every one of its rows, including whole collections, so it carries no information about any single report. The archive keeps it as a collection label and never shows it as a grade.
- **Related:** [Collection label](#collection-label)

<a id="ibadi-report-acceptance"></a>

### Ibadi acceptance of reports

Ibadi scholars treat the Musnad of al-Rabiʿ ibn Habib, transmitted through Abu ʿUbayda and Jabir ibn Zayd, as their most authoritative collection, and weigh other reports by their chains and by agreement with the Qurʾan.

- **In this archive:** The archive holds no per-report gradings for Ibadi works. A report with none shows “No assessment recorded”.
- **Related:** [Ibadi](#ibadi), [jamiʿ](#jami), [No assessment recorded](#no-assessment-recorded)

<a id="zaydi-report-acceptance"></a>

### Zaydi acceptance of reports

Zaydi scholars give particular weight to reports transmitted through the Prophet’s family, use reports from other collections as well, and assess them by criteria set out in their own works on legal theory.

- **In this archive:** The archive holds no per-report gradings for Zaydi works. A report with none shows “No assessment recorded”.
- **Related:** [Zaydi](#zaydi), [musnad](#musnad), [No assessment recorded](#no-assessment-recorded)

<a id="section-works"></a>

## Works and genres

<a id="sahih-collection"></a>

### sahih (collection) · صحيح

A collection whose compiler set out to include only reports meeting his own standard of soundness, such as the Sahihs of al-Bukhari and Muslim.

- **In this archive:** A compiler’s criterion applies to his collection as a whole and is shown as such, not as a grade on each report.
- **Across traditions:** The title records the compiler’s aim; other traditions, and some critics within the same tradition, do not accept every report in it. The Ibadi al-Jamiʿ al-Sahih also bears the title.
- **Related:** [Compiler’s criterion](#compiler-criterion), [al-kutub al-sitta](#six-books), [jamiʿ](#jami)

<a id="sunan"></a>

### sunan · سنن

A collection arranged by legal topic, such as purification and prayer, like the Sunan of Abu Dawud or al-Nasaʾi.

- **Related:** [al-kutub al-sitta](#six-books), [jamiʿ](#jami), [musnad](#musnad)

<a id="musnad"></a>

### musnad · مسند

A collection arranged by the Companion or authority who narrates each report, like the Musnad of Ahmad ibn Hanbal; the word is also used in some titles for a collection with chains.

- **In this archive:** Musnad al-Imam Zayd ibn ʿAli and the Musnad of al-Rabiʿ ibn Habib use the word in their titles but are arranged by topic.
- **Related:** [sunan](#sunan), [jamiʿ](#jami), [Zaydi](#zaydi), [Ibadi](#ibadi)

<a id="muwatta"></a>

### muwattaʾ (the smoothed path) · موطأ

A collection combining reports with legal opinions and local practice, best known through Malik ibn Anas’s Muwattaʾ.

- **Related:** [sunan](#sunan), [al-kutub al-sitta](#six-books)

<a id="jami"></a>

### jamiʿ (comprehensive collection) · جامع

A collection covering every subject, from belief and law to manners and history, such as the Jamiʿ of al-Tirmidhi.

- **Related:** [sunan](#sunan), [sahih (collection)](#sahih-collection), [Ibadi](#ibadi)

<a id="amali"></a>

### amali (dictations) · أمالي

A work recording reports a scholar dictated to students in sessions, often arranged by session rather than topic.

- **In this archive:** Several works share the title al-Amali (for example those of al-Saduq, al-Mufid and al-Tusi), so the archive identifies the work by its compiler, not by the title.
- **Across traditions:** The genre is found in Imami, Zaydi and Sunni literature.
- **Related:** [Source work](#source-work), [Zaydi](#zaydi), [Imami](#imami)

<a id="six-books"></a>

### al-kutub al-sitta (the Six Books) · الكتب الستة

The six Sunni collections most widely relied on: the Sahihs of al-Bukhari and Muslim, and the Sunan of Abu Dawud, al-Tirmidhi, al-Nasaʾi and Ibn Maja.

- **Across traditions:** Some Sunni scholars list Malik’s Muwattaʾ or al-Darimi’s Sunan in place of Ibn Maja.
- **Related:** [Sunni](#sunni), [sahih (collection)](#sahih-collection), [sunan](#sunan), [al-kutub al-arbaʿa](#four-books)

<a id="four-books"></a>

### al-kutub al-arbaʿa (the Four Books) · الكتب الأربعة

The four principal Imami collections: al-Kafi of al-Kulayni, Man la yahduruhu al-faqih of al-Saduq, and Tahdhib al-ahkam and al-Istibsar of al-Tusi.

- **Across traditions:** Imami scholars hold different views on whether every report in them is reliable.
- **Related:** [Imami](#imami), [Imami grading](#imami-grading), [al-kutub al-sitta](#six-books)

<a id="rijal"></a>

### rijal (narrator studies) · رجال

The study of narrators’ lives and reliability (ʿilm al-rijal), and the books that record it, giving each narrator’s name, teachers, students, dates and critics’ verdicts.

- **In this archive:** Narrator data comes partly from a narrator lexicon (the Muslim Scholars Database). Its dates and places are shown on narrator pages labelled “narrator lexicon, not yet cited”; a death year that Ibn Hajar’s Taqrib contradicts is held back until reviewed, and its prose biographies stay hidden.
- **Across traditions:** Each tradition has its own rijal works, such as those of al-Najashi and al-Tusi for Imami narrators and those of Ibn Abi Hatim and Ibn Hajar for Sunni narrators.
- **Related:** [al-jarh wa al-taʿdil](#jarh-wa-tadil), [rawi](#rawi), [Narrator verdict](#narrator-verdict)
- **Data values:** `narrator_authority.imami_rijal`

<a id="sharh"></a>

### sharh (commentary) · شرح

A commentary that explains a collection report by report, covering language, chains, rulings and disputes.

- **In this archive:** Commentary shown in the archive is attributed to its author and source.
- **Related:** [sahih (collection)](#sahih-collection), [Citation](#citation)

<a id="section-comparative"></a>

## Comparative study and history

<a id="israiliyyat"></a>

### Israʾiliyyat · الإسرائيليات

Reports and stories that entered Muslim literature from Jewish and Christian sources, especially about earlier prophets, creation and the end of time.

- **In this archive:** The comparative pages classify such material as muwafiq, mukhalif or maskut ʿanhu; “Not classified” means no classification has been recorded.
- **Across traditions:** The three-part classification is set out by Sunni exegetes such as Ibn Kathir; scholars of every tradition have debated how far such material may be used.
- **Related:** [muwafiq](#muwafiq), [mukhalif](#mukhalif), [maskut ʿanhu](#maskut-anhu), [Parallel](#parallel)
- **Data values:** `isra_iliyyat_status.NONE`

<a id="muwafiq"></a>

### muwafiq (consistent) · موافق

Earlier-scripture material whose content agrees with what Islamic sources affirm.

- **Related:** [Israʾiliyyat](#israiliyyat), [mukhalif](#mukhalif), [maskut ʿanhu](#maskut-anhu)
- **Data values:** `isra_iliyyat_status.MUWAFIQ`

<a id="mukhalif"></a>

### mukhalif (contrary) · مخالف

Earlier-scripture material whose content contradicts what Islamic sources affirm.

- **Related:** [Israʾiliyyat](#israiliyyat), [muwafiq](#muwafiq), [maskut ʿanhu](#maskut-anhu)
- **Data values:** `isra_iliyyat_status.MUKHALIF`

<a id="maskut-anhu"></a>

### maskut ʿanhu (left unaddressed) · مسكوت عنه

Earlier-scripture material that Islamic sources neither confirm nor deny, so it is neither affirmed nor rejected.

- **Related:** [Israʾiliyyat](#israiliyyat), [muwafiq](#muwafiq), [mukhalif](#mukhalif)
- **Data values:** `isra_iliyyat_status.MASKUT_ANHU`

<a id="parallel"></a>

### Parallel

A recorded resemblance between a hadith and a passage in another religious tradition’s literature.

- **In this archive:** Each parallel has a type: condemnation (the hadith rejects the other text), cultural crossover (shared surroundings), shared source, direct borrowing, apologetic (answering the other tradition), or disputed. A recorded parallel is a reading for discussion, not a finding about origin.
- **Related:** [Israʾiliyyat](#israiliyyat), [Confidence](#confidence), [Machine-proposed](#machine-proposed)
- **Data values:** `parallel_type.CONDEMNATION`, `parallel_type.CULTURAL_BLEED`, `parallel_type.SHARED_SOURCE`, `parallel_type.DIRECT_BORROWING`, `parallel_type.APOLOGETIC`, `parallel_type.DISPUTED`

<a id="confidence"></a>

### Confidence

How strongly the person who recorded a parallel judges the resemblance: high, medium or low.

- **In this archive:** It describes the recorded comparison only; it is not a grade of the hadith.
- **Related:** [Parallel](#parallel)
- **Data values:** `confidence_level.HIGH`, `confidence_level.MEDIUM`, `confidence_level.LOW`

<a id="madhhab"></a>

### madhhab (school) · مذهب

A school of thought, either of law (such as the Hanafi or Jaʿfari schools) or of theology.

- **In this archive:** Schools are grouped as Sunni or Shiʿi legal schools and Sunni, Shiʿi or Ibadi theological schools.
- **Related:** [Sunni](#sunni), [Imami](#imami), [Zaydi](#zaydi), [Ibadi](#ibadi)
- **Data values:** `school_category.SUNNI_THEOLOGICAL`, `school_category.SHIA_THEOLOGICAL`, `school_category.IBADI_THEOLOGICAL`, `school_category.SUNNI_MADHHAB`, `school_category.SHIA_MADHHAB`

<a id="rashidun"></a>

### Rashidun (the first four caliphs) · الراشدون

The period of the first four caliphs after the Prophet, Abu Bakr, ʿUmar, ʿUthman and ʿAli (11–40 AH).

- **In this archive:** Used as a period label on historical events.
- **Across traditions:** The name, “rightly guided”, is Sunni usage; Imami, Zaydi and Ibadi historians assess these caliphates differently, and the archive uses the label only to name the period.
- **Related:** [Umayyad](#umayyad), [hijri](#hijri)
- **Data values:** `event_category.RASHIDUN`

<a id="umayyad"></a>

### Umayyad · الأمويون

The dynasty that ruled the caliphate from Damascus from 41 to 132 AH (661–750 CE).

- **In this archive:** Used as a period label on historical events.
- **Related:** [Rashidun](#rashidun), [Abbasid](#abbasid), [hijri](#hijri)
- **Data values:** `event_category.UMAYYAD`

<a id="abbasid"></a>

### Abbasid · العباسيون

The dynasty that ruled the caliphate, mostly from Baghdad, from 132 AH (750 CE), the period in which the major hadith collections were compiled.

- **In this archive:** Used as a period label on historical events.
- **Related:** [Umayyad](#umayyad), [hijri](#hijri)
- **Data values:** `event_category.ABBASID`

<a id="hijri"></a>

### hijri (AH) · هجري

The Islamic lunar calendar, counted from the Prophet’s emigration to Medina in 622 CE; dates in it are marked AH.

- **In this archive:** Narrator life dates are hijri years, often uncertain, so they may be shown as ranges.
- **Related:** [tabaqa](#tabaqa)
- **Data values:** `calendar.hijri`

<a id="era"></a>

### Era

A named stretch of years, such as a caliphate or the lifetimes of the Imams, used to place a narrator’s life in its time.

- **In this archive:** Eras have neutral descriptive names; a tradition’s own name for a period is listed beside it with who uses it. A disputed start or end is kept as a range of years. Eras loaded from the seed are unverified until a curator cites them.
- **Across traditions:** Traditions divide and name the past differently: Sunni writers speak of the rightly guided caliphs, Imami writers of the presence and the occultation of the Imams, Zaydi and Ibadi writers of their own imamates. The archive shows each tradition’s periods in its own reckoning and makes none the default.
- **Related:** [hijri](#hijri), [ghayba](#ghayba), [Chronological note](#chronological-gap)

<a id="ghayba"></a>

### ghayba (occultation) · غيبة

In Imami belief, the hiddenness of the twelfth Imam, divided into a Lesser Occultation (260–329 AH) with four successive deputies and a Greater Occultation from 329 AH.

- **In this archive:** Shown as eras in Imami reckoning.
- **Related:** [Era](#era), [Imami](#imami)

<a id="section-archive"></a>

## Archive terms

<a id="chronological-gap"></a>

### Chronological note

A note that two consecutive narrators in a chain, as their dates or generations are recorded, do not seem to have overlapped.

- **In this archive:** Shown when one narrator’s earliest recorded birth is after the other’s latest recorded death, or when their recorded generations are more than one step apart. Each note names where each date comes from. It is information about the records, which may themselves be wrong or may name the wrong person, and never a ruling on the chain.
- **Related:** [tabaqa](#tabaqa), [Era](#era), [Basis](#basis), [munqatiʿ](#munqati)

<a id="unverified-seed"></a>

### Seed, unverified

A starting record (an event, place or era) entered before any curator review, with no citation yet.

- **In this archive:** Seed records are labelled “seed, unverified” and are never public. Once a curator edits or reviews one, later reloads of the seed leave it alone.
- **Related:** [Unreviewed](#unreviewed), [Citation](#citation), [Era](#era)

<a id="source-work"></a>

### Source work

The book a report is taken from, identified by its compiler and title, such as al-Kulayni’s al-Kafi.

- **In this archive:** Where one title names several works (al-Amali, Kitab al-Ghayba), the archive keeps them apart by compiler and never guesses which one a bare title means.
- **Related:** [Edition](#edition), [Citation](#citation), [amali](#amali)

<a id="edition"></a>

### Edition

A particular printing or digital text of a source work, whose volume and page numbers a citation refers to.

- **Related:** [Source work](#source-work), [Citation](#citation)

<a id="citation"></a>

### Citation

A pointer to the exact place, by work, edition, volume and page, that supports a claim shown in the archive.

- **In this archive:** Verdicts, biographies, dates and identity decisions without a citation are not published.
- **Related:** [Edition](#edition), [Source work](#source-work), [Published](#published)

<a id="locator-bound"></a>

### Traced to source page

Said of an Arabic text that is tied to a specific record and page or address in its source.

- **In this archive:** It shows the text can be checked against its source; it is not a review of the text.
- **Related:** [Citation](#citation), [Source work](#source-work)
- **Data values:** `source_text_status.present_locator_bound`

<a id="mention"></a>

### Mention

One name exactly as written at one position in one chain.

- **In this archive:** Every mention is kept as written. A mention may later be linked to a person, recorded as a relation, a group or an unnamed narrator, or marked as not a narrator at all when the text-reading picked up a word that is not a name.
- **Related:** [isnad](#isnad), [Basis](#basis), [Identity decision](#identity-decision), [Not yet identified](#not-yet-identified)
- **Data values:** `link_kind.person`, `link_kind.not_a_narrator`, `surface_decision_kind.not_a_narrator`, `decision_scope.mention`

<a id="basis"></a>

### Basis

The reason the archive gives for connecting a name in a chain to a particular narrator.

- **In this archive:** The labels are: verified by a reviewer; machine-reviewed (matches the source’s index and the text); source index; matched by name; matched by kunya only; and not yet identified. When candidates disagree, all of them are kept. A kunya-only match is shown as a note beside other candidates and never counts as a disagreement.
- **Related:** [Machine-reviewed](#confirmed-by-source-and-text), [Identity decision](#identity-decision), [Source index](#source-index), [Matched by name](#matched-by-name), [Matched by kunya only](#matched-by-kunya-only), [Not yet identified](#not-yet-identified)

<a id="confirmed-by-source-and-text"></a>

### Machine-reviewed (matches the source’s index and the text)

A machine check found that the source’s own narrator index names this person at this position and that the name written in the Arabic agrees with it.

- **In this archive:** The archive’s top automatic tier, shown as “machine-reviewed”, never as verified: a sample found about one in twenty of these wrong where two people share a name. It rests on one of: the six-books source index, hadith-kg’s index, or Thaqalayn’s annotation carried by the Riwayat corpus, each confirmed by the Arabic; two independent sources agreeing; or an Imam’s conventional kunya in an Imami chain. Riwayat’s own automatic links never count. It stands only when no other source names someone else (a kunya-only match does not count against it). Teacher-to-student links built from it are machine-reviewed too. Only a reviewer’s decision is called verified.
- **Related:** [Basis](#basis), [Source index](#source-index), [Two sources agree](#two-sources-agree), [Imam’s conventional kunya](#imam-kunya), [Identity decision](#identity-decision)
- **Data values:** `mention_candidate_basis.source_index_confirmed_by_text`, `mention_candidate_basis.source_hadith_kg_confirmed_by_text`, `mention_candidate_basis.source_riwayat_confirmed_by_text`

<a id="two-sources-agree"></a>

### Two sources agree

Two independent compilations name the same person at the same place in the chain: the six-books source index and hadith-kg.

- **In this archive:** Counts toward the machine-reviewed tier under its own label (owner, 2026-11-21). The two records are taken as one person only through a machine-proposed link between them, which is shown as a candidate. The Riwayat corpus’s ids for Sunni chains are hadith-kg’s own, so Riwayat agreeing with hadith-kg is not a second source.
- **Related:** [Machine-reviewed](#confirmed-by-source-and-text), [External source record](#external-source-record)

<a id="imam-kunya"></a>

### Imam’s conventional kunya (e.g. Abu ʿAbd Allah (ʿa) for al-Sadiq)

In Imami chains the Imams are often named by kunya alone, followed by the honorific: Abu ʿAbd Allah (ʿa) is Jaʿfar al-Sadiq, Abu Ibrahim (ʿa) is Musa al-Kazim.

- **In this archive:** In an Imami chain, a kunya with the honorific identifies the Imam and counts toward the machine-reviewed tier (owner, 2026-11-21). A kunya several Imams share (Abu Jaʿfar, Abu al-Hasan, Abu Muhammad) is decided only when a word after it names one Imam (al-Rida, al-Thani); otherwise every Imam who shares it is shown as an undecided candidate. The rule is a reviewable file, never applied outside Imami chains.
- **Related:** [kunya](#kunya), [Matched by kunya only](#matched-by-kunya-only), [Machine-reviewed](#confirmed-by-source-and-text)
- **Data values:** `mention_candidate_basis.imam_kunya_convention`, `mention_candidate_basis.imam_kunya_candidate`, `narrator_authority.imam_register`

<a id="opening-isnad"></a>

### Named in the opening isnad (e.g. «عن أبيه عن جده» in Musnad Zayd)

A work often writes its full chain once, in its first report, and later writes only «from his father, from his grandfather». The first report says who they are.

- **In this archive:** In Musnad Zayd, a chain of exactly the shape «Zayd b. ʿAli, from his father, from his grandfather, from ʿAli» is read through the work’s own report No. 1, which names ʿAli b. al-Husayn and al-Husayn b. ʿAli. In Musnad al-Rabiʿ, «Abu ʿUbayda» is the man the work’s report No. 1 names in full, Abu ʿUbayda Muslim b. Abi Karima al-Tamimi; he has his own record credited to the work, and Riwayat’s record for the name stays an unconfirmed candidate. The words stay as written; the identity names that report as its basis and counts toward the machine-reviewed tier. Any other shape gets nothing. The rule is a reviewable file.
- **Related:** [Imam’s conventional kunya](#imam-kunya), [Machine-reviewed](#confirmed-by-source-and-text)
- **Data values:** `mention_candidate_basis.named_in_opening_isnad`

<a id="compiler-of-the-work"></a>

### Compiler of the work (e.g. al-Bukhari heading every chain of his Sahih)

The compiler is the last transmitter of every report in his book: he heard it from the first name of the chain and wrote it down. Most texts do not write his name, because the book is his.

- **In this archive:** Every chain of a work with a known compiler is headed by him, marked as derived from the work and never as written in the text (owner, 2026-11-22). He forms a teacher link with the first name only when the chain opens with his own hearing («حدثنا», or the work’s fixed opening) and does not rely on another chain. His record is the archive’s existing record where a standing rule of that tradition already identifies him (Malik, Ahmad, al-Darimi, Abu Dawud, al-Kulayni, al-Husayn b. Saʿid); otherwise a record credited to the work. Not done for works whose compiler is not a transmitter (Sahifat al-Rida, the modern Muʿjam, Nahj al-Balagha). The list is a reviewable file.
- **Related:** [Named in the opening isnad](#opening-isnad)
- **Data values:** `narrator_authority.work_register`

<a id="edition-identification"></a>

### Named by a printed edition (e.g. «عمر، هو ابن عبد الواحد الدمشقي»)

An editor of a printed edition sometimes says in a note who a short name in the chain is. The note is cited with its book, volume and page.

- **In this archive:** Five Sunni chain positions carry such an identification, found by the chain audit and cited to the edition; it counts toward the machine-reviewed tier and stands over the source index it corrects. It is never called verified: a reviewer has not confirmed it. Other proposals of the audit stay as notes for review.
- **Related:** [Source index](#source-index), [Machine-reviewed](#confirmed-by-source-and-text)
- **Data values:** `mention_candidate_basis.edition_identification`

<a id="external-source-record"></a>

### External source record

A narrator as another open dataset describes it, under that dataset’s own id: hadith-kg (narrator ids for the Sunni and some Ibadi and Zaydi chains) or the Riwayat corpus (Sunni and Shiʿi chains).

- **In this archive:** Such a record has its own narrator page, credited to its dataset, listing what the dataset records (never its grading words) and every chain it is named in. Its claims at a chain position are shown with their source: an id confirmed by the Arabic, or only aligned. A record is never merged with a lexicon entry automatically; a proposed link is shown as a candidate.
- **Related:** [Source index](#source-index), [Label id](#label-id), [Riwayat automatic link](#riwayat-automatic-link), [Two sources agree](#two-sources-agree)
- **Data values:** `narrator_authority.hadith_kg`, `narrator_authority.riwayat`, `mention_candidate_basis.source_hadith_kg`, `mention_candidate_basis.source_riwayat`

<a id="riwayat-automatic-link"></a>

### Riwayat automatic link

An identification the Riwayat corpus made with its own matching software, rather than taking it from Thaqalayn’s or hadith-kg’s annotation.

- **In this archive:** Shown, labelled as such, and never counted toward the machine-reviewed tier: a sample read one in eight wrong, against none of 52 taken from Thaqalayn’s annotation.
- **Related:** [External source record](#external-source-record), [Machine-reviewed](#confirmed-by-source-and-text)

<a id="label-id"></a>

### Label id

A source id that names a name as it is written in chains rather than an established person: a name several men share, one word, a kunya alone, or a group.

- **In this archive:** Its narrator page says so plainly, and its claims never carry the machine-reviewed tier, because matching the text cannot tell which man a shared label means.
- **Related:** [External source record](#external-source-record), [mushtarak](#mushtarak), [Kunya-only and single-name mentions](#single-name-mention)

<a id="latin-name"></a>

### Name in Latin letters

Every name in a chain is shown with a Latin form beside the Arabic, so a reader without Arabic can follow the chain. It renders the name as written; it does not say who the person is.

- **In this archive:** Taken, in order, from the source’s own English for that name (Thaqalayn’s English chains), the English name of the record the name is identified with, a transliteration of the vowelled Arabic, or a transliteration assembled only from common name parts whose reading is fixed. Where none applies the name is shown in Arabic alone rather than guessed. Each form shows how it was obtained and its source.
- **Related:** [Mention](#mention), [Not yet identified](#not-yet-identified), [External source record](#external-source-record)
- **Data values:** `name_latin_basis.provider_english`, `name_latin_basis.identity_name`, `name_latin_basis.transliteration_vocalized`, `name_latin_basis.transliteration_table`

<a id="source-index"></a>

### Source index

An identification taken from the source’s own list of narrator IDs for a report, without confirmation from the Arabic text.

- **In this archive:** A source index is the source’s claim, not the archive’s; it is shown as such and is neither machine-reviewed nor verified.
- **Related:** [Basis](#basis), [Machine-reviewed](#confirmed-by-source-and-text), [Candidate](#candidate)
- **Data values:** `mention_candidate_basis.source_index`, `mention_resolution.source_index`, `resolution_basis.source_index`

<a id="matched-by-name"></a>

### Matched by name

The name as written matches exactly one entry in the narrator lexicon, either letter for letter or after fixed spelling rules.

- **In this archive:** The match says the spelling agrees; it does not say a scholar has confirmed the person.
- **Related:** [Basis](#basis), [Matched by kunya only](#matched-by-kunya-only), [mushtarak](#mushtarak)
- **Data values:** `mention_candidate_basis.name_exact`, `mention_candidate_basis.name_spelling_fold`, `mention_resolution.exact_registry`, `resolution_basis.mention_exact`, `resolution_basis.report_atomic`

<a id="matched-by-kunya-only"></a>

### Matched by kunya only

The only match is on a kunya, which many narrators share, so the identification is uncertain.

- **In this archive:** Shown as a labelled note beside any other match, never as a disagreement, and ignored when deciding which identity stands and in every analysis, including the teacher-to-student network.
- **Related:** [kunya](#kunya), [Kunya-only and single-name mentions](#single-name-mention), [Basis](#basis)
- **Data values:** `mention_candidate_basis.name_kunya_only`

<a id="not-yet-identified"></a>

### Not yet identified

No identification of this name meets the archive’s rules, so it is shown as written, without a link.

- **In this archive:** Not identified is not the same as unknown to scholarship. A curator may also record that the evidence cannot decide between candidates.
- **Related:** [Mention](#mention), [Basis](#basis), [Kunya-only and single-name mentions](#single-name-mention), [Review unit](#review-unit)
- **Data values:** `mention_resolution.unresolved`, `mention_resolution.undecidable`, `surface_decision_kind.undecidable`

<a id="identity-decision"></a>

### Identity decision (verified by a reviewer)

A curator’s recorded judgement of who a name in a chain refers to, in a given context, with the reviewer named.

- **In this archive:** A decision applies to every mention of the same name with the same teacher (and, where needed, the same student) in the same work. Decisions about kunya-only, epithet-only or cross-tradition names need a citation.
- **Related:** [Review unit](#review-unit), [Basis](#basis), [Curator](#curator), [mushtarak](#mushtarak)
- **Data values:** `mention_candidate_basis.reviewer_decision`, `mention_resolution.human_verified`, `resolution_basis.human_decision`, `surface_decision_kind.same_as`

<a id="derived-relation"></a>

### Derived relation

A name given only by relation to the previous narrator, such as “his father” (abihi) or “his grandfather” (jaddihi).

- **In this archive:** It can be identified only once the narrator it depends on is identified.
- **Related:** [Mention](#mention), [Identity decision](#identity-decision), [nasab](#nasab)
- **Data values:** `link_kind.derived_relation`, `mention_resolution.derived_relation_verified`, `surface_decision_kind.derived_relation`

<a id="collective-mention"></a>

### Collective mention

A link that names a group rather than a person, such as “a number of our companions” (ʿidda min ashabina).

- **In this archive:** It is part of the chain but never resolves to one narrator.
- **Across traditions:** Where a compiler states who such a group means, as al-Kulayni does for some of his, that statement is a cited claim within that tradition.
- **Related:** [mubham](#mubham), [Mention](#mention)
- **Data values:** `link_kind.collective`, `surface_decision_kind.collective`

<a id="placeholder-entry"></a>

### Placeholder entry

A narrator-lexicon entry that cannot name one person, because it is only a single word, only a kunya, has no Arabic name, or is marked as an unidentified shaykh.

- **In this archive:** Placeholder entries are never used as match targets; they remain for review. An external source’s record of the same kind (a kunya alone, a relation, a group, or a hadith-kg stub) is shown when the source names it, as a label that never contests another identity.
- **Related:** [Kunya-only and single-name mentions](#single-name-mention), [Matched by name](#matched-by-name), [Label id](#label-id)
- **Data values:** `narrator_placeholder_reason.unidentified_shaykh_marker`, `narrator_placeholder_reason.no_arabic_name`, `narrator_placeholder_reason.bare_single_token_name`, `narrator_placeholder_reason.kunya_only_name`, `narrator_placeholder_reason.relational_name`, `narrator_placeholder_reason.collective_or_anonymous_name`, `narrator_placeholder_reason.hadith_kg_stub_narrator`

<a id="review-unit"></a>

### Review unit

A group of mentions that one identity decision can settle together: the same name, with the same teacher (and where needed the same student), in the same work.

- **In this archive:** Curators review units in order of how many reports one decision would complete.
- **Related:** [Identity decision](#identity-decision), [Candidate](#candidate), [mushtarak](#mushtarak)
- **Data values:** `decision_scope.teacher_context`, `decision_scope.teacher_and_student_context`

<a id="candidate"></a>

### Candidate

A machine-produced suggestion, of an identity, a translation or a grading, kept for review and never shown to readers as fact.

- **Related:** [Machine-proposed](#machine-proposed), [Unreviewed](#unreviewed), [Review unit](#review-unit)
- **Data values:** `evidence_review_state.candidate_only`

<a id="report-correspondence"></a>

### Telling (corresponding report)

Another report, in this or another work or tradition, whose wording overlaps this one closely enough that it may be the same report told again.

- **In this archive:** Found by a machine comparison of the report texts with the chains removed (shared five-letter sequences), then shown as machine-found and unreviewed unless a reviewer confirmed it. A reader sees same wording, variant wording at 40 percent shared wording or more, and a shared passage covering 70 percent or more of the shorter text; a reviewer’s confirmation shows a pair at any score and a rejection hides it. It is evidence that two reports correspond, not a ruling that they are one hadith, and it says nothing about which telling is earlier or more authentic. Each telling keeps its own chains, tradition and work.
- **Related:** [Same wording](#same-wording), [Variant wording](#variant-wording), [Shares a passage](#shared-passage), [Correspondence decision](#correspondence-decision), [matn](#matn), [isnad](#isnad)
- **Data values:** `report_correspondence_basis.textual_overlap`

<a id="same-wording"></a>

### Same wording

Two report texts that are nearly identical letter for letter, once the chains are set aside.

- **In this archive:** At least 80 percent of their letter sequences are shared.
- **Related:** [Telling (corresponding report)](#report-correspondence), [Variant wording](#variant-wording)
- **Data values:** `report_correspondence_class.same_wording`, `report_correspondence_reviewed_relation.same_wording`

<a id="variant-wording"></a>

### Variant wording

Two texts that tell what appears to be the same report with differences of wording, order or length.

- **In this archive:** Shown to readers from 40 percent shared wording; lower scores are kept for reviewers.
- **Related:** [Telling (corresponding report)](#report-correspondence), [Same wording](#same-wording), [Shares a passage](#shared-passage)
- **Data values:** `report_correspondence_class.same_report_variant_wording`, `report_correspondence_reviewed_relation.same_report_variant_wording`

<a id="shared-passage"></a>

### Shares a passage

One text contains a passage of the other, for example a saying quoted inside a longer report.

- **In this archive:** Shown to readers when the passage covers 70 percent or more of the shorter text.
- **Related:** [Telling (corresponding report)](#report-correspondence), [Variant wording](#variant-wording)
- **Data values:** `report_correspondence_class.partial_overlap`, `report_correspondence_reviewed_relation.partial_overlap`

<a id="correspondence-decision"></a>

### Correspondence decision

A reviewer’s judgement on a machine-found pair of reports: confirmed, rejected, or uncertain.

- **In this archive:** A decision is tied to the exact Arabic the reviewer read; if either text changes, the pair goes back for review. Earlier decisions are kept, never deleted.
- **Related:** [Telling (corresponding report)](#report-correspondence), [Curator](#curator), [Human verified](#human-verified)
- **Data values:** `report_correspondence_decision.confirmed`, `report_correspondence_decision.rejected`, `report_correspondence_decision.uncertain`

<a id="shared-formula-only"></a>

### Shared formula, verse or ruling

A reviewer’s reading that two texts overlap only in a common formula (such as the shahada), a Quran verse, or the same ruling attributed to a different speaker, so they are not one report.

- **In this archive:** Recorded with a rejection or an uncertain decision, never with a confirmation.
- **Related:** [Correspondence decision](#correspondence-decision), [Telling (corresponding report)](#report-correspondence)
- **Data values:** `report_correspondence_reviewed_relation.shared_formula_only`, `report_correspondence_reviewed_relation.shared_quran_quotation`, `report_correspondence_reviewed_relation.same_ruling_different_attribution`

<a id="chain-status"></a>

### Chain status

How much of a report’s chain the archive has identified.

- **In this archive:** Complete: every name has an identity (machine-reviewed or verified by a reviewer). Partial: some do. Unresolved: none are yet. No chain in source: the work gives none (for example the sermons of Nahj al-Balagha). Not extracted: the chain could not be read from the text. In every case the chain is shown as written.
- **Related:** [isnad](#isnad), [Mention](#mention), [Basis](#basis)
- **Data values:** `chain_status.complete`, `chain_status.partial`, `chain_status.unresolved`, `chain_status.absent_in_source`, `chain_status.extraction_failed`

<a id="assessment"></a>

### Assessment

A grade for a report, attributed to a named scholar within one tradition and kept in that scholar’s words.

- **In this archive:** Hadith pages list assessments by tradition. There is no single computed grade for a hadith, and different traditions’ assessments are never combined.
- **Related:** [Compiler’s statement](#compiler-statement), [Compiler’s criterion](#compiler-criterion), [No assessment recorded](#no-assessment-recorded), [Sunni grading](#sunni-grading), [Imami grading](#imami-grading)
- **Data values:** `grading_status.cited_assessments`, `assessment_kind.cited_ruling`

<a id="compiler-statement"></a>

### Compiler’s statement

A grade the compiler wrote into the work beside a report, such as al-Tirmidhi’s remark after it.

- **In this archive:** Quoted from the Arabic text where it appears.
- **Related:** [Assessment](#assessment), [hasan sahih](#hasan-sahih), [Compiler’s criterion](#compiler-criterion)
- **Data values:** `assessment_kind.compiler_statement`

<a id="compiler-criterion"></a>

### Compiler’s criterion

The standard a compiler set for the whole collection, such as the conditions of the two Sahihs, rather than a ruling on one report.

- **In this archive:** Shown as the collection’s criterion, not as a grade of the individual report.
- **Related:** [sahih (collection)](#sahih-collection), [Assessment](#assessment), [Compiler’s statement](#compiler-statement)
- **Data values:** `grading_status.compiler_criterion`, `assessment_kind.compiler_criterion`

<a id="collection-label"></a>

### Collection label

A label an upstream dataset applied to every row of a collection, which says nothing about any one report.

- **In this archive:** Kept for the record and never shown as a grade.
- **Related:** [thabit](#thabit), [Assessment](#assessment)
- **Data values:** `assessment_kind.collection_label`

<a id="source-grade"></a>

### Source grade

A grade recorded in the source the report was taken from, shown as that source gives it.

- **Related:** [Assessment](#assessment), [Source work](#source-work)

<a id="no-assessment-recorded"></a>

### No assessment recorded

The archive holds no grade for this report in this tradition.

- **In this archive:** This says nothing about the report’s strength: it may never have been graded, or a grading may exist that the archive does not yet hold.
- **Related:** [Assessment](#assessment), [Ibadi acceptance of reports](#ibadi-report-acceptance), [Zaydi acceptance of reports](#zaydi-report-acceptance)
- **Data values:** `grading_status.none_recorded`, `grade_canonical.ungraded`

<a id="narrator-verdict"></a>

### Narrator verdict

A summary judgement on a narrator’s reliability, such as thiqa or daʿif.

- **In this archive:** A verdict belongs to a critic and a tradition. For the verdicts currently shown, the critic and tradition are not yet recorded, and the narrator page says so.
- **Related:** [al-jarh wa al-taʿdil](#jarh-wa-tadil), [thiqa](#thiqa), [daʿif](#daif), [mukhtalaf fihi](#mukhtalaf-fihi)
- **Data values:** `narrator_assessment_kind.consensus_summary`

<a id="dataset-version"></a>

### Dataset version

One numbered load of the archive’s data, recorded with its inputs so any figure can be traced to the load it came from.

- **In this archive:** A release version has passed the release checks; any other version is shown publicly only as a preview.
- **Related:** [Preview](#preview), [Retired](#retired)
- **Data values:** `release_class.release`

<a id="preview"></a>

### Preview

Data from a dataset version that has not passed the release checks, shown publicly only because the owner has recorded approval to do so.

- **In this archive:** While the preview notice is shown, identities, gradings and translations may be incomplete or unverified, and may change with the next load. A preview is not a reviewed release.
- **Related:** [Dataset version](#dataset-version), [Unreviewed](#unreviewed), [Publication status](#publication-status)
- **Data values:** `release_class.non_release`

<a id="rights-status"></a>

### Rights status

Whether the archive has permission to publish a source work’s text: cleared, pending or restricted.

- **In this archive:** Only cleared works publish text or English. A work with no recorded status counts as pending.
- **Related:** [Source work](#source-work), [Publication status](#publication-status)
- **Data values:** `rights_status.cleared`, `rights_status.pending`, `rights_status.restricted`

<a id="publication-status"></a>

### Publication status

Where a curated item stands on its way to readers: proposed, verified, then published, or retired.

- **In this archive:** A row is public when every claim it displays is verified; completeness is tracked, not required.
- **Related:** [Proposed](#proposed), [Published](#published), [Retired](#retired), [Unreviewed](#unreviewed)

<a id="unreviewed"></a>

### Unreviewed

Not yet checked by a person against its source.

- **In this archive:** Unreviewed material, including lexicon biographies, seed historical events and English of unknown origin, is kept for curators and labelled wherever it appears.
- **Related:** [Machine-proposed](#machine-proposed), [Candidate](#candidate), [Proposed](#proposed), [Human verified](#human-verified)
- **Data values:** `evidence_review_state.lexicon_unverified`, `event_verification.unverified`, `event_verification.unverified_seed`, `translation_state.unknown_provenance`

<a id="machine-proposed"></a>

### Machine-proposed

Produced by software, such as a translation model or an automated comparison, and not yet reviewed by a person.

- **In this archive:** Always labelled. A machine translation is shown only for works whose recorded English policy allows it, as “Unreviewed machine translation” with the model that produced it, or “model not recorded”. No identity, grade, date or translation is asserted by a machine.
- **Related:** [Candidate](#candidate), [Unreviewed](#unreviewed), [Parallel](#parallel)
- **Data values:** `translation_state.machine_unreviewed`, `record_origin.ai_research`, `english_policy.source_provided_and_machine_allowed`

<a id="proposed"></a>

### Proposed

Entered by a curator or a tool and awaiting review before it can be published.

- **Related:** [Publication status](#publication-status), [Published](#published), [Unreviewed](#unreviewed)
- **Data values:** `curation_status.proposed`

<a id="source-provided"></a>

### Source provided

Supplied with the source data, such as an English translation from the provider, but not yet checked by the archive.

- **In this archive:** Source-provided English is shown only for works whose recorded English policy allows it, labelled “Source-provided English, not reviewed here” and credited to its source and translator.
- **Related:** [Source verified](#source-verified), [Human verified](#human-verified), [Unreviewed](#unreviewed)
- **Data values:** `translation_state.source_provided`, `evidence_review_state.source_provided`, `english_policy.source_provided_allowed`, `english_policy.reviewed_only`

<a id="source-verified"></a>

### Source verified

Checked against a published source, such as a printed translation or edition, and found to match it.

- **Related:** [Human verified](#human-verified), [Source provided](#source-provided), [Citation](#citation)
- **Data values:** `translation_state.source_verified`, `evidence_review_state.source_verified`, `event_verification.source_verified`

<a id="human-verified"></a>

### Human verified

Reviewed and accepted by a named person.

- **Related:** [Source verified](#source-verified), [Curator](#curator), [Identity decision](#identity-decision)
- **Data values:** `translation_state.human_verified`, `evidence_review_state.human_verified`, `event_verification.human_verified`, `curation_status.verified`

<a id="published"></a>

### Published

Reviewed, cited where required, and visible to readers.

- **Related:** [Publication status](#publication-status), [Proposed](#proposed), [Retired](#retired), [Citation](#citation)
- **Data values:** `curation_status.published`

<a id="retired"></a>

### Retired

Withdrawn from display but kept, with who retired it and when; nothing in the archive is deleted.

- **In this archive:** A corrected decision or record replaces the old one, which stays in the history.
- **Related:** [Publication status](#publication-status), [Published](#published), [Dataset version](#dataset-version)

<a id="curator"></a>

### Curator

A named, invited person who may record decisions and publish material; every change they make is logged under their name.

- **Related:** [Contributor](#contributor), [Identity decision](#identity-decision), [Human verified](#human-verified)

<a id="contributor"></a>

### Contributor

A person who submits material, such as commentary, a translation or a correction, for curators to review.

- **In this archive:** Planned: the contribution system is designed but not yet built.
- **Related:** [Curator](#curator), [Endorsement (ijaza)](#endorsement)

<a id="endorsement"></a>

### Endorsement (ijaza) · إجازة

In the archive, a record that one contributor vouches for another’s expertise in a field, named after the ijaza, the classical licence by which a teacher authorised a student to transmit.

- **In this archive:** Planned with the contribution system.
- **Related:** [Contributor](#contributor), [Curator](#curator)

<a id="owner-review"></a>

## Needs the owner’s review

Entries written conservatively where a tradition-specific usage or a data mapping is uncertain.

- [Ibadi](#ibadi): Check the one-line description of the tradition and its present-day regions.
- [Zaydi](#zaydi): Check the one-line description, and whether other Zaydi works (such as amali collections) should be named.
- [hadith](#hadith): Check whether the Zaydi and Ibadi notes need more: the weight Zaydis give to reports from ʿAli and the Prophet’s family, and the Ibadi inclusion of reports from Jabir ibn Zayd.
- [khabar](#khabar): Confirm the Imami usage note, and whether Zaydi or Ibadi usage differs.
- [Report from an Imam](#imam-report): Confirm whether the data’s narration level “imam” is also used for reports ending at Zaydi imams.
- [mudmar](#mudmar): The grade mapping in src/lib/constants/grade-taxonomy.ts groups مضمر with mursal. Confirm whether that grouping is acceptable or should be kept separate.
- [akhbarana](#akhbarana): Check the summary of the difference in usage, and whether any tradition-specific note should be added.
- [mutabaʿa](#mutaba): Confirm whether the Imami, Zaydi or Ibadi literature uses these two terms differently from the description given.
- [mursal](#mursal): Check the summary of the Imami sense and of the dispute over acceptance.
- [marfuʿ](#marfu): Confirm the Imami sense. The grade mapping in src/lib/constants/grade-taxonomy.ts maps مرفوع to mursal, which fits only that Imami sense.
- [mawquf](#mawquf): Confirm the Imami definition.
- [maqtuʿ](#maqtu): Confirm whether Imami usage differs.
- [majhul](#majhul): Confirm the Imami distinction between majhul and muhmal.
- [ʿadalat al-sahaba](#adalat-al-sahaba): The narrator page (ConsensusBadge) shows “ʿadalat al-sahaba” for every “not applicable” verdict regardless of tradition. Confirm the wording and how Zaydi and Ibadi positions should be summarised.
- [daʿif ʿala al-mashhur](#daif-ala-al-mashhur): Confirm the reading. The grade mapping also turns “ضعيف على المشهور معتبر عند ي” into muʿtabar; check that this is the intended reading.
- [muʿtabar](#mutabar): Confirm what al-Majlisi and the other graders in the data mean by معتبر.
- [ka-al-sahih](#kal-sahih): src/lib/constants/grade-taxonomy.ts maps every “… كالصحيح” to the canonical bucket sahih, which states more than the grader did. Confirm the reading and whether the mapping should change.
- [Ibadi acceptance of reports](#ibadi-report-acceptance): Describe Ibadi criteria for accepting reports correctly, in that tradition’s own terms; this entry is written cautiously and may be incomplete.
- [Zaydi acceptance of reports](#zaydi-report-acceptance): Describe Zaydi criteria for accepting reports correctly, in that tradition’s own terms; this entry is written cautiously and may be incomplete.
- [Israʾiliyyat](#israiliyyat): Confirm the attribution of the three-part classification and whether a tradition-specific note is needed for Imami, Zaydi or Ibadi treatments.
- [Parallel](#parallel): The one-line glosses of the six parallel types are inferred from their labels; confirm them.
- [madhhab](#madhhab): The school categories have no Ibadi legal or separate Zaydi entries, and group Imami and Zaydi together as Shiʿi. Confirm whether that is acceptable.
- [Rashidun](#rashidun): The period label carries a Sunni name. Confirm the wording, or choose a neutral label such as “early caliphate”.
- [Matched by kunya only](#matched-by-kunya-only): The runbook records this treatment of kunya-only matches as a reading of your answer that is still to be confirmed.
- [Preview](#preview): Confirm that this wording matches the preview notice and your approval.
- [Endorsement (ijaza)](#endorsement): A classical ijaza licenses transmission; the planned endorsement vouches for expertise. Confirm you want the word ijaza used for it.

## Enum values without an entry

Every other value in `src/db/schema/enums.ts` is explained by an entry above (see its “Data values”).

| Value | Kind | Reason |
| --- | --- | --- |
| `grade_scheme.*` | not user-facing | Storage key for which tradition’s scale a grade belongs to; the tradition itself is what the app shows. The tier counts in the key names are design labels, not scholarly claims. |
| `load_status.*` | not user-facing | Loader bookkeeping for a dataset version (loading, complete, failed). |
| `link_kind.unclassified` | not user-facing | Default before a mention is classified; the reader sees the name as written. |
| `record_origin.manual` | not user-facing | Provenance bookkeeping; curator-entered rows carry the curator’s name instead. |
| `record_origin.seed` | not user-facing | Provenance bookkeeping for seeded rows. |
| `record_origin.neo4j_migration` | not user-facing | Provenance bookkeeping for rows migrated from the earlier graph store. |
| `source_text_status.present` | plain language | Arabic text is present. |
| `source_text_status.missing` | plain language | Arabic text is missing; such rows are not published. |
| `narration_level.unknown` | plain language | Shown as “Unknown”. |
| `tabaqah_class.PROPHET` | plain language | Shown as “The Prophet”. |
| `calendar.gregorian` | plain language | The common-era calendar. |
| `location_relation.born` | plain language | Born. |
| `location_relation.died` | plain language | Died. |
| `location_relation.resided` | plain language | Resided. |
| `event_category.PROPHETIC_ERA` | plain language | The lifetime of the Prophet. |
| `event_category.SCHOLARLY` | plain language | Plain topic label. |
| `event_category.MILITARY` | plain language | Plain topic label. |
| `event_category.POLITICAL` | plain language | Plain topic label. |
| `event_category.SOCIAL` | plain language | Plain topic label. |
| `event_category.RELIGIOUS` | plain language | Plain topic label. |
| `event_category.SCIENTIFIC` | plain language | Plain topic label. |
| `event_category.CULTURAL` | plain language | Plain topic label. |
| `event_category.ECONOMIC` | plain language | Plain topic label. |
| `motif_category.ESCHATOLOGY` | plain language | Plain topic label (the end of time). |
| `motif_category.CREATION` | plain language | Plain topic label. |
| `motif_category.PROPHETIC_STORIES` | plain language | Plain topic label (stories of earlier prophets). |
| `motif_category.LEGAL` | plain language | Plain topic label. |
| `motif_category.WISDOM` | plain language | Plain topic label (wisdom literature). |
| `motif_category.PERSIAN_INFLUENCE` | plain language | Plain topic label. |
| `motif_category.COSMOLOGY` | plain language | Plain topic label. |
| `report_correspondence_scope.same_work` | plain language | Shown as “within one work”. |
| `report_correspondence_scope.cross_work_same_tradition` | plain language | Shown as “across works of one tradition”. |
| `report_correspondence_scope.cross_tradition` | plain language | Shown as “across traditions”. |
