# Stage 3 — Formal grammar approaches to classical isnad

(Persisted from S3's inline reply on 2026-06-12 — agent declined to write directly due to a conflicting instruction. Verbatim below.)

## What classical hadith science says about taḥwīl (with citations)

**Ibn al-Salah, Muqaddima fi 'Ulum al-Hadith** (نوع 25, on the writing of the isnad): the ح glyph is treated as a **scribal abbreviation** whose disambiguation is itself contested. Ibn al-Salah reports two readings — (a) it stands for **تحويل** ("switching" of the isnad), (b) it stands for **الحديث** (a marker that the matn resumes after a parallel chain). He recommends pronouncing it simply as "ح" without committing. Critically for our purposes: he does **not** state that the two sub-chains must converge on a shared sub-isnad. Convergence is an *empirical* property of many ṭuruq, not a *rule* of the ح production.

**al-Suyuṭi, Tadrib al-Rawi** (شرح تقريب النواوي, the chapter on كتابة الحديث) reproduces Ibn al-Salah's two-reading position verbatim and adds al-ʿIraqi's gloss that the ح is purely a **muḥaddith's bookkeeping mark** so the reader knows a new sanad begins, *not* a semantic operator linking branches. al-Suyuṭi explicitly notes scribes who use it, scribes who substitute "صح", and scribes who repeat the entire matn instead — i.e., the surface form is variable.

**al-Khaṭib al-Baghdadi, al-Kifaya fi ʿIlm al-Riwaya** (باب كتابة الحديث): describes conventions for *writing* multiple chains for one matn (tarjamah, repetition, ح) but offers no production-rule-like statement. He warns against muddling chains and recommends a fresh "حدثنا" after the ح, which most later mutūn obey — but the recommendation is normative, not descriptive of all transmitted manuscripts.

**Takeaway:** the classical literature does **not** define ح with the rigor a CFG would need. It is an abbreviation with at least two semantic readings, used inconsistently, and the question "must branches converge?" is *not answered* by uṣūl works — it is an empirical regularity, not a grammatical constraint.

## Published formal grammars / parsers (with sources)

To the best of my knowledge through Jan 2026: **no peer-reviewed BNF/EBNF/CFG for classical isnad has been published.** Searches across ACL Anthology, LREC, WANLP, JSTOR, and Google Scholar for "isnad grammar," "isnad BNF," "isnad context-free," "sanad parser" return:

- Najeeb et al. (2014, IJCSI) "A Classifier to Detect Tampering in Arabic Sentences" — uses regex over حدثنا/أخبرنا/عن but no grammar.
- Siddiqui et al. (KAU, ~2014-2018) on isnad extraction — pattern-matching, no formal language.
- Bilal & Mohd (UTM) thesis-level work on hadith chain extraction — rule-based, not grammar-theoretic.
- Azmi & Bin Badia (2010, JKSU) "iTree" — closer to a tree-builder over isnad strings, with implicit production rules, but they do **not** claim context-freeness and do not publish a grammar.

The closest published "grammar" is a set of regex patterns in the **OpenITI** pipeline (Romanov et al.) and the **iTree** rule set — neither is a CFG in the formal sense.

## Dependency parsing on classical Arabic

**CAMeL Tools** ships MSA models; classical performance degrades on archaic morphology. The CamelParser2.0 paper (Elshabrawy et al., 2023) reports UAS drops on classical text. No published evaluation specifically scores **isnad-verb relation accuracy** for حدثنا/أخبرنا/عن. The **Quranic Arabic Corpus** (Dukes) treebank covers only Qur'an, not hadith; it has no isnad. The **Prague Arabic Dependency Treebank** is MSA news. **No hadith treebank exists publicly** — this gap is itself the answer.

## Is classical isnad context-free? (the deeper question)

A *normative* isnad — modern editor's text, well-punctuated Bukhari — is **arguably context-free** with the production sketched in the spec. But classical isnad in raw manuscript-transcribed form is **not** context-free for three reasons:

1. **The ح is non-local.** A reader must sometimes *re-enter* the parent chain after the ح to identify where the branch grafts back. That is a **context-sensitive** dependency (matching open/close across arbitrary depth, like cross-serial agreement).
2. **Embedded narration verbs without isnad reset** (e.g., "قال فلان حدثنا" inside a matn) require **semantic** disambiguation — the same surface lexeme is sometimes a sanad operator, sometimes a matn-internal quotation. A CFG cannot disambiguate without an oracle.
3. **Scribal free variation** documented by al-Suyuṭi (repeat-matn vs. ح vs. صح) means the same logical structure has surface forms a single CFG cannot enumerate without exploding into ambiguity.

Mildly context-sensitive (TAG, CCG) **could** capture (1). It cannot rescue (2) or (3) without lexical-semantic features.

## Verdict for our problem: would a grammar give GUARANTEED coverage?

**No.** A CFG over your `ISNAD ::= NARRATOR (VERB NARRATOR)* (TAHWEEL ISNAD)? MATN` shape will handle perhaps 85–95% of well-edited Sunni mutūn (Kutub Sittah print editions) but will systematically miss: (a) ح used as "الحديث" rather than تحويل, (b) Shi'i and Zaydi isnad conventions where multiple ṭuruq are listed without ح, (c) embedded narration in matn, (d) scribal idiosyncrasies in less-edited corpora (Musnad Ahmad manuscripts, Ibadi sources). A hybrid — grammar as the recall scaffold + LLM/classifier for the residual ~5–15% — is the only honest path to "guaranteed" coverage, because the classical literature itself never closed the ح semantics, so no grammar can.

The strongest finding: **the absence of a published isnad CFG is not an oversight — it is a consequence of the uṣūl literature never formalizing ح.**
