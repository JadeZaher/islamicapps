# Taḥwīl-Aware Isnad Annotation Guide

**Version:** 1.0.0
**Audience:** Islamic studies students, fellow scholars, and other careful readers helping grow the project's taḥwīl-aware isnad gold set.
**File this guide governs:** `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl`
**Companion files:** `docs/annotation/calibration-test.md` (the entry exam) and `docs/annotation/iaa-tooling.md` (inter-annotator agreement reference).


## §1 — What we're annotating and why

The project maintains an automated extractor that walks the chain of narrators (the isnad) of every ḥadīth in a large corpus and writes that chain into a database for later analysis. For the overwhelming majority of rows the chain is a single column — one person hands a report to the next, and so on down to the Companion. But thousands of Sunni K6 rows use the scribal mark **ح** (called **taḥwīl**) to splice two or more chains into a single textual block. The extractor's job is to recover those branches faithfully. Our job, as annotators, is to give the extractor a reliable answer key it can be measured against.

That answer key is `tahweel-gold.jsonl`. Each row in the file is one ḥadīth with one field — `expected_branches` — that you fill in. The field is a list of lists of narrator names, one inner list per branch, top to bottom. When the extractor runs against the same row, it produces its own list of lists; the bake-off compares the two. If your annotation is wrong, the extractor "passes" a test it should have failed. So the gold set is only as good as the care taken on every single row.

This is the single most important sentence in this guide:

> **This is a "what does the text say" exercise, not a "who is this person" exercise.**

The `text_ar` field on every row is the source of truth. You record narrators **exactly as they appear** in `text_ar`. If the text says `سفيان`, you write `سفيان`, not `سفيان بن عيينة`. If the text says `أبي` ("my father"), you write `أبي`, not the inferred father's name. If a name has a kunya, an honorific, or a partial form that you happen to know expands to a fuller form, you still record the surface form the scribe wrote.

There is a downstream component — the **resolver** — whose job is to look at `سفيان` in context and conclude "this is Sufyān ibn ʿUyayna", or to read `أبي` and conclude "given the chain father is `عبيد الله بن معاذ`, the referent is `معاذ`". That resolver has its own tests, its own gold set, and its own evaluation harness. **It is not your job to do the resolver's work.** In fact, when you pre-resolve a surface into its canonical referent, you actively break the resolver's tests — because the resolver can only be measured against what the *text* literally said, not against what an annotator already inferred.

Why does this distinction matter so much? Because the extractor and the resolver have different failure modes, and we measure each one against a faithful representation of the source. The extractor's failure mode is "I missed a branch" or "I dropped a narrator at the branch head." The resolver's failure mode is "I conflated two people with the same name." Mixing the two by pre-resolving inside the gold set means we can no longer tell which component failed when something goes wrong.

So when you are reading a row's `text_ar`, your inner monologue should be: *I am a transcriber. I am writing down who the scribe said handed this to whom. I am not deciding who any of them really were.* If you find yourself wanting to "fix" or "clarify" a name, stop and recheck — that is almost always the resolver's job, not yours.


## §2 — The annotation contract

Each row in `tahweel-gold.jsonl` is a JSONL object. Some of its fields come pre-populated by the pull script (`pull_next_candidates.py`) and must not be edited. Others are blank and waiting for you. Knowing which is which is the single hardest mechanical rule of the kit, and the validator (`validate_annotation.py`) refuses any row that breaks it.

**Fields you fill:**

| Field | Type | What it means |
|---|---|---|
| `expected_branches` | `list[list[str]]` | The ground-truth chain. Each inner list is one branch; each string inside is one narrator surface form. Order matters — write narrators top to bottom (from the compiler down to the Companion). |
| `notes` | `string` | Your reasoning for hard cases. Mandatory whenever `difficulty == 5`. Otherwise optional, but very welcome — your reasoning is what lets a later reviewer follow your thinking. |
| `annotator` | `string` | Your identifier. Initials are fine (`JZ`) or a username (`jzaher`). Whatever you put here, the gold set treats as the person who vouches for the row. |
| `annotated_at` | `string` | ISO-8601 timestamp, e.g. `2026-06-14T15:30:00Z`. Most editors can insert this for you. |
| `difficulty` | `integer` | 1 (trivial — single chain) through 5 (genuinely ambiguous; see §4 point 5). Be honest. Difficulty 5 unlocks a documentation requirement — see §5. |

**Fields you must NOT modify:**

| Field | Why it is locked |
|---|---|
| `hadith_id` | Anchors the row to the corpus. Touching it breaks every downstream join. |
| `source` | Identifies the collection (e.g., `Sahih Muslim`). |
| `hadith_no` | Identifies the ḥadīth's number within the collection. |
| `tahweel_count` | The number of ح marks the pull script detected in `text_ar`. The validator uses this to check that the number of branches you wrote matches reality. |
| `text_ar` | The source of truth. If you find a typo in `text_ar`, that's a corpus-level fix — file an issue separately. Do not silently correct it. |
| `sanad` | The cleaned chain segment from the upstream pipeline, when present. Leave it as is. |

**The hard rule:** *no row enters `tahweel-gold.jsonl` without passing the validator.* The annotation workflow is staged: you receive a `staging-<date>.jsonl` from the pull script, you fill in your fields, you run `validate_annotation.py` against your file, and only after every row passes do you (or a reviewer) run the `--promote` step that appends to the gold. If a row fails, you fix the annotation; you do not bypass the check.

This staging-then-promote dance exists for one reason: an unchecked bad annotation can quietly corrupt the canonical fixtures, and a corrupted gold set silently changes whether the extractor's tests pass or fail. The validator is the gate. Treat its complaints as a friend, not a friction.


## §3 — The seven canonical case types

Almost every taḥwīl-marked row in the corpus falls into one of seven shapes. The next seven subsections walk through each one with: a verbatim Arabic example, the actual JSON `expected_branches` an annotator wrote, two or three sentences of reasoning, and a chain diagram drawn with box-drawing characters so the topology is visible at a glance.

Cases 2 through 6 use the fixtures already in `tahweel-gold.jsonl` — those are the worked examples a future annotator can compare their own work against. Case 1 uses an illustrative single-chain pattern from Ṣaḥīḥ al-Bukhārī (no Bukhari row is in the gold yet — a follow-up track will add one). Case 7 uses Ṣaḥīḥ Muslim hadith no. 1565, a four-branch pathological example identified in Phase 0; its annotation here is a *draft* for the guide, and a follow-up annotation pass will ratify it before it enters gold.

### §3.1 — Case 1: Single chain, no taḥwīl

This is by far the most common shape in the corpus — about 98 percent of all rows. There is no ح. There is one straight line from the compiler down to the Companion. The annotator's job is to walk that line once.

*Illustrative Bukhari example (not yet in the fixture set; a future track will add a real Bukhari row to gold):*

> حدثنا عبد الله بن يوسف، قال: أخبرنا مالك، عن نافع، عن عبد الله بن عمر، أن رسول الله صلى الله عليه وسلم قال…

```json
{
  "expected_branches": [
    ["عبد الله بن يوسف", "مالك", "نافع", "عبد الله بن عمر"]
  ]
}
```

```
عبد الله بن يوسف
        │
        ▼
      مالك
        │
        ▼
      نافع
        │
        ▼
عبد الله بن عمر
        │
        ▼
   (matn — "أن رسول الله ...")
```

The annotator reads top to bottom, stops at the matn cue (`أن رسول الله صلى الله عليه وسلم قال`), and writes a single inner list of four narrator surfaces. There is no branching to reason about; the difficulty here is just stopping at the right place. Difficulty: 1.

### §3.2 — Case 2: Classic two-branch convergence (Tirmidhi #1)

The textbook taḥwīl: the compiler quotes one chain, then writes ح to signal a second chain, then writes the second chain. The two chains rejoin partway down and share a common tail leading to the Companion.

*Verbatim from `tahweel-gold.jsonl` (Tirmidhi #1):*

> حدثنا قتيبة بن سعيد، حدثنا أبو عوانة، عن سماك بن حرب، ح وحدثنا هناد، حدثنا وكيع، عن إسرائيل، عن سماك، عن مصعب بن سعد، عن ابن عمر، عن النبي صلى الله عليه وسلم قال "لا تقبل صلاة بغير طهور ولا صدقة من غلول".

```json
{
  "expected_branches": [
    ["قتيبة بن سعيد", "أبو عوانة", "سماك بن حرب", "مصعب بن سعد", "ابن عمر"],
    ["هناد", "وكيع", "إسرائيل", "سماك", "مصعب بن سعد", "ابن عمر"]
  ]
}
```

```
   قتيبة بن سعيد       هناد
         │              │
         ▼              ▼
      أبو عوانة       وكيع
         │              │
         ▼              ▼
   سماك بن حرب       إسرائيل
         │              │
         │              ▼
         │           سماك   <- same person as سماك بن حرب
         │              │
         └──────┬───────┘
                ▼
         مصعب بن سعد
                │
                ▼
            ابن عمر
                │
                ▼
        (matn — "عن النبي ﷺ قال ...")
```

Reasoning: Branch A is the chain before the ح; Branch B is the chain after it. The matn-attaching cue `عن النبي صلى الله عليه وسلم قال` tells us the chain ends and the report begins, so both branches converge on a shared tail (`مصعب بن سعد → ابن عمر`) that comes from the Branch B segment. This is also a Case 5 row (note that `سماك بن حرب` and `سماك` are the same person under two surface forms; we record both as written).

### §3.3 — Case 3: Co-transmitter at branch head (Muslim #2)

A single branch can begin with **two** compiler-narrators who jointly handed the chain down. The text writes both names side by side, often with `و` joining them. Each one is its own narrator surface, and both stay in the branch.

*Verbatim from `tahweel-gold.jsonl` (Muslim #2):*

> وحدثنا أبو بكر بن أبي شيبة، حدثنا غندر، عن شعبة، ح وحدثنا محمد بن المثنى، وابن، بشار قالا حدثنا محمد بن جعفر، حدثنا شعبة، عن منصور، عن ربعي بن حراش، أنه سمع عليا

```json
{
  "expected_branches": [
    ["أبو بكر بن أبي شيبة", "غندر", "شعبة", "منصور", "ربعي بن حراش", "علي"],
    ["محمد بن المثنى", "ابن بشار", "محمد بن جعفر", "شعبة", "منصور", "ربعي بن حراش", "علي"]
  ]
}
```

```
أبو بكر بن أبي شيبة      محمد بن المثنى     ابن بشار
         │                     │                 │
         │                     └────────┬────────┘
         │                              │ (co-transmitters)
         ▼                              ▼
       غندر                       محمد بن جعفر
         │                              │
         └──────────────┬───────────────┘
                        ▼
                      شعبة
                        │
                        ▼
                     منصور
                        │
                        ▼
                  ربعي بن حراش
                        │
                        ▼
                       علي
                        │
                        ▼
                  (matn — "أنه سمع علياً ...")
```

Reasoning: Branch B opens with two co-transmitters (`محمد بن المثنى` and `ابن بشار`), both written before the verb `قالا` ("the two of them said"), and they both feed into `محمد بن جعفر`. Both names belong in Branch B's narrator list. After that, both branches converge at `شعبة` and share the tail down to `علي`. (The cleaned-up corpus text has a spurious comma after `وابن`; the surface form to record is `ابن بشار`.)

### §3.4 — Case 4: Parallel-but-no-convergence (Muslim #1)

Two branches can share their **head** (the compiler-narrator prefix) but tail through entirely different downstream narrators. This is the case that breaks the naive intuition "if the heads match, the chains must merge." They do not. The shared prefix is just the compiler repeating themselves; the actual chains diverge after the first divergence point.

*Verbatim from `tahweel-gold.jsonl` (Muslim #1):*

> حدثنا أبو بكر بن أبي شيبة حدثنا وكيع عن شعبة عن الحكم عن عبد الرحمن بن أبي ليلى عن سمرة بن جندب. ح وحدثنا أبو بكر بن أبي شيبة أيضا حدثنا وكيع عن شعبة وسفيان عن حبيب عن ميمون بن أبي شبيب عن المغيرة بن شعبة قالا قال رسول الله صلى الله عليه وسلم ذلك.

```json
{
  "expected_branches": [
    ["أبو بكر بن أبي شيبة", "وكيع", "شعبة", "الحكم", "عبد الرحمن بن أبي ليلى", "سمرة بن جندب"],
    ["أبو بكر بن أبي شيبة", "وكيع", "شعبة", "حبيب", "ميمون بن أبي شبيب", "المغيرة بن شعبة"]
  ]
}
```

```
أبو بكر بن أبي شيبة     أبو بكر بن أبي شيبة   <- same person, written twice
         │                       │
         ▼                       ▼
       وكيع                    وكيع
         │                       │
         ▼                       ▼
       شعبة                    شعبة
         │                       │
         ▼                       ▼
      الحكم                    حبيب           <- here the chains diverge
         │                       │
         ▼                       ▼
عبد الرحمن بن أبي ليلى    ميمون بن أبي شبيب
         │                       │
         ▼                       ▼
   سمرة بن جندب            المغيرة بن شعبة
         │                       │
         ▼                       ▼
        (matn — both Companions, then "قال رسول الله ﷺ ذلك")
```

Reasoning: After the ح, the compiler-narrator `أبو بكر بن أبي شيبة` literally re-quotes himself ("`أيضا`", "also"). Both branches travel through `وكيع → شعبة` — but then Branch A continues through `الحكم → عبد الرحمن بن أبي ليلى → سمرة بن جندب` while Branch B continues through `حبيب → ميمون بن أبي شبيب → المغيرة بن شعبة`. The two Companions (`سمرة بن جندب` and `المغيرة بن شعبة`) are different people. Do not force a shared suffix — the chains do not converge.

### §3.5 — Case 5: Surface-form drift (Muslim #31 and Tirmidhi #1)

The same person can appear under different surface forms in different branches: short form versus full form, kunya versus laqab, with or without a patronymic. The annotator records each surface form as the text wrote it; unifying them ("ah, `سفيان` here means `سفيان بن عيينة`") is the resolver's job downstream.

*Verbatim from `tahweel-gold.jsonl` (Muslim #31):*

> حدثنا محمد بن أبي عمر المكي، حدثنا سفيان، ح وحدثني أبو بكر بن خلاد الباهلي، - واللفظ له - قال سمعت سفيان بن عيينة، عن مسعر، قال سمعت سعد بن إبراهيم، يقول لا يحدث عن رسول الله صلى الله عليه وسلم إلا الثقات.

```json
{
  "expected_branches": [
    ["محمد بن أبي عمر المكي", "سفيان", "مسعر", "سعد بن إبراهيم"],
    ["أبو بكر بن خلاد الباهلي", "سفيان بن عيينة", "مسعر", "سعد بن إبراهيم"]
  ]
}
```

```
محمد بن أبي عمر المكي      أبو بكر بن خلاد الباهلي
          │                            │
          ▼                            ▼
       سفيان                     سفيان بن عيينة   <- same person, two surfaces
          │                            │
          └──────────────┬─────────────┘
                         ▼
                      مسعر
                         │
                         ▼
                 سعد بن إبراهيم
                         │
                         ▼
              (matn — "يقول لا يحدث عن رسول الله ﷺ إلا الثقات")
```

Reasoning: Both branches reach `سعد بن إبراهيم → matn`. Branch A names the convergence narrator as `سفيان`; Branch B names him as `سفيان بن عيينة`. They are the same scholar. We record what each branch said. Tirmidhi #1 (§3.2) shows the same kind of drift between `سماك بن حرب` and `سماك` — also recorded as written. The downstream resolver knows that `سفيان` in this context means `سفيان بن عيينة` and that `سماك` means `سماك بن حرب`; we do not pre-bake that knowledge into the gold.

### §3.6 — Case 6: Pronoun / elided reference (Muslim #102)

Arabic isnads sometimes name a narrator through a pronoun or a kin term whose referent must be inferred from context. The most common is `أبي` ("my father"), where the speaker's identity makes the father identifiable. Other patterns include `أخبرني` with no name and `عنه` ("from him") referring back to a previously named person. **The annotator records the pronoun verbatim.** Pre-resolving the pronoun is the resolver's job.

*Verbatim from `tahweel-gold.jsonl` (Muslim #102):*

> حدثني أبو خيثمة، زهير بن حرب حدثنا وكيع، عن كهمس، عن عبد الله بن بريدة، عن يحيى بن يعمر، ح وحدثنا عبيد الله بن معاذ العنبري، - وهذا حديثه - حدثنا أبي، حدثنا كهمس، عن ابن بريدة، عن يحيى بن يعمر

```json
{
  "expected_branches": [
    ["أبو خيثمة زهير بن حرب", "وكيع", "كهمس", "عبد الله بن بريدة", "يحيى بن يعمر"],
    ["عبيد الله بن معاذ العنبري", "أبي", "كهمس", "ابن بريدة", "يحيى بن يعمر"]
  ]
}
```

```
أبو خيثمة زهير بن حرب      عبيد الله بن معاذ العنبري
         │                            │
         ▼                            ▼
       وكيع                          أبي   <- pronoun, refers to معاذ (resolver's job)
         │                            │
         └──────────────┬─────────────┘
                        ▼
                      كهمس
                        │
                        ▼
              عبد الله بن بريدة         ابن بريدة   <- same person, two surfaces
                        │                  │
                        └────────┬─────────┘
                                 ▼
                          يحيى بن يعمر
                                 │
                                 ▼
                              (matn ...)
```

Reasoning: Branch B has `أبي` immediately after `عبيد الله بن معاذ العنبري`. The Arabic literally says "his father" — and because the previous narrator is `عبيد الله ibn معاذ`, classical scholarship reads the father as `معاذ`. **But the gold records `أبي`, not `معاذ`.** The resolver knows how to expand the kin term using the parent relationship. Likewise, Branch A's `عبد الله بن بريدة` and Branch B's `ابن بريدة` are the same person; both are recorded as written. This row is therefore Case 6 (pronoun) plus Case 5 (surface drift) plus Case 2 (convergence at `كهمس`) — composite cases are common.

### §3.7 — Case 7: Three-or-more-branch pathological (Ṣaḥīḥ Muslim #1565)

Some rows pile up three or four ح splitters, with all branches converging at a single distant narrator and the rest of the chain abbreviated by a stock phrase. These are rare (around 49 such rows in Ṣaḥīḥ Muslim per the corpus audit) but they are the rows the extractor most often gets wrong — they are where the gold set earns its keep.

*Verbatim from the corpus (Ṣaḥīḥ Muslim #1565). Not yet ratified into `tahweel-gold.jsonl` — the JSON below is a **draft for this guide**, deferred to a follow-up annotation pass for ratification:*

> حدثنا أبو كريب، حدثنا أبو معاوية، ح وحدثنا إسحاق، أخبرنا جرير، وأبو معاوية ح وحدثنا الأشج، حدثنا ابن فضيل، ح وحدثنا ابن أبي عمر، حدثنا سفيان، كلهم عن الأعمش، بهذا الإسناد مثله.

```json
{
  "expected_branches": [
    ["أبو كريب", "أبو معاوية", "الأعمش"],
    ["إسحاق", "جرير", "الأعمش"],
    ["إسحاق", "أبو معاوية", "الأعمش"],
    ["الأشج", "ابن فضيل", "الأعمش"],
    ["ابن أبي عمر", "سفيان", "الأعمش"]
  ]
}
```

```
أبو كريب     إسحاق         إسحاق        الأشج       ابن أبي عمر
   │           │             │            │              │
   ▼           ▼             ▼            ▼              ▼
أبو معاوية   جرير      أبو معاوية    ابن فضيل         سفيان
   │           │             │            │              │
   └───────────┴─────────────┼────────────┴──────────────┘
                             ▼
                         الأعمش         <- "كلهم عن الأعمش"
                             │
                             ▼
              (the rest of the chain is taken from the preceding ḥadīth —
               "بهذا الإسناد مثله" = "with this isnad, similar [in matn]")
```

Reasoning: The text contains three ح marks, which means there are four block-level branches in the literal scribal structure (`tahweel_count = 3` and `len(expected_branches) = 4` would be the naive expectation). However, the second block — `إسحاق، أخبرنا جرير، وأبو معاوية` — is itself a Case 3 co-transmitter pattern: `جرير` and `أبو معاوية` are both transmitters from `إسحاق`. So that block decomposes into two branches sharing `إسحاق` at the head. The full annotation therefore has **five** branches, not four — illustrating that Cases 3 and 7 compose, and that `tahweel_count` is a count of scribal ح marks, not always a count of true narrator-branches.

The closing idiom `كلهم عن الأعمش، بهذا الإسناد مثله` is worth a sidebar:

> **Sidebar — chain-summary idioms.** *`كلهم عن X`* literally means "all of them from X" and tells the annotator that every preceding branch converges at the named narrator `X`. *`بهذا الإسناد مثله`* means "with this isnad, similar [in matn]" and tells the reader that the *rest* of the chain (from X down to the Companion) is identical to the preceding ḥadīth — the scribe has elided it to save ink. For annotation purposes, the chain you record stops at the convergence narrator named in the `كلهم عن` phrase. The post-convergence tail does not enter `expected_branches` because the text does not actually state it on this row.

Because this row is genuinely a hard case and because the annotation above is a draft, we would mark it `difficulty: 4` (not 5 — there is no Ibn al-Salah ambiguity here, just structural complexity) and put the reasoning in `notes`.

### §3.8 — Tradition coverage: why this guide is Sunni-K6-centric

The seven case types and all the worked examples above come from Sunni K6 collections (Tirmidhi, Muslim, illustrative Bukhari). This is deliberate. The Phase 0 audit (`conductor/tracks/tahweel_annotation_kit_20260612/verification.md`, T-0.2) ran the ح-detector against every non-Sunni source in the corpus — Imami (sixteen sources including Al-Kāfī, ~33,225 rows), Zaydi (Musnad al-Imām Zayd, 698 rows), Ibadi (al-Rabīʿ ibn Ḥabīb, 1,004 rows), and Rida (Ṣaḥīfat al-Imām ʿAlī al-Riḍā, 35 rows). The result was decisive: **zero ح-splitter rows across all 34,962 non-Sunni rows.**

The Imami, Zaydi, Ibadi, and Rida sources in our corpus either repeat the matn with a fresh isnad, use co-transmission syntax (`روي عن X و Y`), or reference a prior ḥadīth by chain summary — none of them use ح as an isnad splitter. The annotation kit therefore covers only Sunni K6 taḥwīl until and unless non-Sunni branching grammar is added to the extraction pipeline as part of a future track. If you encounter a non-Sunni row in your candidate file, double-check that the pull script meant to include it (perhaps for case-type 1 single-chain coverage); annotate it the same way as any other single-chain row.


## §4 — Decision tree for hard cases

When a row resists easy classification, walk through these five named decision points in order. Each one is a single rule of thumb plus a one-sentence example showing the rule in action.

**4.1 — Where does the matn start?**

Look for the first matn-attaching cue in `text_ar`. The cues are: `قال`, `قال رسول الله`, `قال أبو عبد الله`, `قال أبو جعفر`, `عن النبي`, `عن رسول الله`, `أن النبي`, `أن رسول الله`, `يقول`, `يخطب قال`, `يخطب يقول`, `سمعت رسول الله`, `سمعت النبي`, `قال رضي الله عنه`, and a handful of close variants. When you hit one of these, the chain ends and the matn (the report itself) begins. Stop adding narrators to your branch at that point. — *Example:* in Tirmidhi #1, the chain ends at `ابن عمر` because the next phrase is `عن النبي صلى الله عليه وسلم قال` — and `لا تقبل صلاة بغير طهور` is the matn, not the chain.

**4.2 — Two branches genuinely don't share narrators (Case 4).**

If both branches arrive at the matn through entirely different downstream chains, write them as two parallel inner lists with no overlap below the first divergence point. Do not force a shared suffix just because they end at "the Prophet" — every isnad ends at the Prophet, that is not convergence. — *Example:* in Muslim #1, both branches pass through `وكيع → شعبة`, but Branch A ends at `سمرة بن جندب` while Branch B ends at `المغيرة بن شعبة`. Two different Companions, two different chains; no shared suffix.

**4.3 — Same narrator, different surface forms (Case 5).**

If the same scholar appears under two different written forms across branches — short name in one, full name in the other; kunya in one, ism in the other — record each surface form *as the text writes it* in that branch. The downstream resolver normalizes them to the same person. — *Example:* in Muslim #31, the convergence narrator is written as `سفيان` in Branch A and `سفيان بن عيينة` in Branch B. We record both. Both are correct surface forms.

**4.4 — Pronouns and elided references (Case 6).**

If a branch uses `أبي` ("my father"), `أخي` ("my brother"), `عنه` ("from him"), `أخبرني` with no name, or any other reference whose target you would only know from outside context, record the pronoun or elision verbatim. The resolver handles inference using the surrounding chain. **Do not expand to the inferred name.** — *Example:* Muslim #102's Branch B has `أبي`. The annotation records `أبي`. It does **not** record `معاذ` — even though the previous narrator's name (`عبيد الله بن معاذ`) gives that inference away.

**4.5 — Genuinely ambiguous text (the Ibn al-Salah problem).**

Classical scholarship (notably Ibn al-Ṣalāḥ in his *Muqaddima* and later al-Suyūṭī in *Tadrīb al-Rāwī*) documents that the mark ح has two valid readings. The dominant reading is **تحويل** (taḥwīl — a *chain switch*), which is what this entire guide is built around. But there is a secondary scholarly reading where ح stands for **الحديث** (an abbreviation for "the ḥadīth itself" — i.e., a marker meaning "continue from here as a single ḥadīth") and is **not** a chain switch. The two readings cannot always be distinguished by surface form alone; sometimes the only way to know is to consult parallel transmissions in other collections or rely on a senior commentator's verdict. The Phase 0 research finding (`.omc/research/uniform-isnad/research-session/report.md`) was that this scholarly ambiguity is structurally unreachable by any automated algorithm — and equally unreachable by an honest annotator working only from a single row's `text_ar`. — *Rule:* if you cannot tell which reading applies, flag the row with `difficulty: 5`, write a short paragraph in `notes` explaining what the two readings would imply, and **do not guess**. Genuinely ambiguous rows are a documented out-of-band class. They are not a failure on your part; they are a documented limit of working from text alone.


## §5 — Annotation quality checklist

Run this self-review before submitting any row. The checks mirror what the validator will run automatically — catching mistakes here saves you a validator round-trip. Each bullet shows what failure looks like, so you can recognize the mistake quickly.

1. **Every surface in `expected_branches` is in `text_ar` literally.** Open `text_ar` in your editor; for each name in each inner list, confirm you can find it as written. — *Failure looks like:* you wrote `سفيان بن عيينة` in Branch A but the text in Branch A only says `سفيان`. The resolver was supposed to do the expansion; the validator will hard-fail this row.

2. **No matn text in the chain.** The cues in §4.1 mark the boundary. Anything after them is the matn (the report itself), not the isnad. — *Failure looks like:* including `قال رسول الله` as a narrator. That phrase is the start of the matn, not a name.

3. **Branch count matches `tahweel_count + 1`.** The pull script counts ح marks; the number of branches should be exactly one more than that. The only exception is `difficulty: 5` with reasoning in `notes`, where you are allowed to flag the row as genuinely ambiguous. — *Failure looks like:* `tahweel_count` is 1 (one ح in the text) but you wrote three branches, and `difficulty` is not 5.

4. **Order is top to bottom.** Each inner list starts with the compiler-narrator (the person closest to the compiler — usually the first name after `حدثنا` or `حدثني`) and ends with the Companion (or whoever appears just before the matn cue). — *Failure looks like:* putting `ابن عمر` first and `قتيبة بن سعيد` last.

5. **Convergence narrators appear in both branches, when applicable.** If your chain diagram shows the two branches merging at a shared narrator, that shared narrator must appear in both inner lists. — *Failure looks like:* in Muslim #2, writing `شعبة` in Branch A but forgetting it in Branch B, even though both branches pass through `شعبة`.

6. **Pronouns preserved.** If the text writes `أبي`, `عنه`, `أخبرني` (no name), or any other pronoun or elision, your inner list contains that exact word. — *Failure looks like:* writing `معاذ` in Muslim #102's Branch B because you "know" the referent.

7. **`notes` filled when `difficulty ≥ 4`.** Difficulty 4 is "structurally hard" (e.g., the four-branch Muslim #1565). Difficulty 5 is "Ibn al-Salah ambiguous." Both deserve a written explanation so a later reviewer can follow your thinking. — *Failure looks like:* marking a row `difficulty: 5` with `notes: ""`. The validator will hard-fail this and the IAA tooling will treat your annotation as unmoored.

If a check fails, fix the annotation and re-run your self-review. The cost of a re-check is tiny compared to the cost of a corrupted gold row.


## §6 — Calibration set workflow

Before contributing real annotations, every new annotator must take the calibration test. The test is described in detail in `docs/annotation/calibration-test.md`; this section is the short pointer.

**What the test is.** Five ḥadīths from the existing gold set, served back to you with `expected_branches` blanked out. Your job: fill in `expected_branches` for each row following this guide, save the file as `<your-id>-calibration.jsonl`, and run the scorer:

```
python score_calibration.py --submission <your-id>-calibration.jsonl
```

**What the scorer measures.** For each row, the scorer compares your `expected_branches` against the hidden answer key (`docs/annotation/.calibration-gold.jsonl`) and produces a per-row similarity number between 0 (no overlap) and 1 (exact match). It then averages those numbers across all five rows to produce an aggregate score.

**Admission threshold.** Aggregate score `≥ 0.85`. The scorer prints a plain-language gloss alongside the number, something like *"you matched 91 percent of the gold's narrators per branch on average — admitted."* If you score below 0.85, the scorer reports which rows pulled the average down; re-read this guide (especially §3 and §4), reconsider those rows, and resubmit.

**Senior scholar carve-out.** Annotators whose first attempt scores `≥ 0.95` are considered presumed-ready: they do not need to re-take the test when the guide is revised in a non-breaking way (typo fixes, clarifying examples). Anyone scoring between 0.85 and 0.95 is admitted but is asked to re-take the calibration the next time the guide undergoes a content revision. This carve-out exists because senior scholars joining the project shouldn't have to repeatedly prove themselves to a guide they helped write.

**Important rule about the answer key.** The hidden answer key lives at `docs/annotation/.calibration-gold.jsonl` — note the leading dot. **Do not open this file before you submit.** Opening it before submitting defeats the purpose of the test; it also undermines the trust the rest of the project places in your `annotator` field once you start contributing real rows. The dot-prefix is a hint to your file browser and to git tooling, not a security boundary; the honor of the project rests on every annotator's discipline here.

**What happens if you fail twice.** Two failed attempts in a row usually means one of: (a) the guide isn't clear enough on a case that tripped you up, or (b) you genuinely need more time with the material before contributing. Either is fine. Reach out to the maintainer with your submission and your scratch notes; we will either patch the guide (helping you and every future annotator) or talk through the rows that gave you trouble.


## §7 — Inter-annotator agreement (IAA)

Once two or more annotators have each annotated a meaningful overlap of rows (rule of thumb: twenty or more rows in common), it becomes useful to measure how much they actually agree. The number telling us that is called inter-annotator agreement (IAA). High IAA means the gold set is reproducible — two careful readers, working independently, reach the same answer. Low IAA means something is wrong: either the guide isn't pinning the case down, the rows are genuinely ambiguous and need the difficulty:5 flag, or one of the annotators is misreading the contract.

We measure IAA two different ways. The primary metric is the one we make decisions from; the secondary is a sanity check.

### §7.1 — Primary metric: Krippendorff's α

Krippendorff's α (alpha) is the right tool for our shape of data because it copes natively with variable-length lists, missing entries (one annotator's branch is shorter than the other's), and more than two annotators at once. We compute it over a per-position view of every annotated row: for each row, every position in every branch is a unit, the value at that unit is the normalized narrator surface, and disagreement is "0 if the surfaces match after normalization, 1 otherwise." Krippendorff's α turns that table of disagreements into a single number.

The number's range is conceptually: `-1` (worse than random), `0` (random — no meaningful agreement), `1` (perfect agreement). Anything `≥ 0.80` is the project's threshold for calling the row pair consensus-validated. Below that, we treat the row pair as needing follow-up.

### §7.2 — Secondary metric: Cohen's κ on a flattened view

Cohen's κ (kappa) is a more familiar metric in many fields, but it assumes a fixed vocabulary of labels — not a great fit for narrator surfaces that can be any Arabic name. We compute it as a sanity check on a *flattened* view of each row: for each branch, we ask "does annotator A's branch list the same *set* of narrators as annotator B's branch?" — ignoring order, ignoring positions. Cohen's κ over that flattened view gives us a second number we can compare against α. Same threshold: `≥ 0.80` is consensus, below that is follow-up.

If α and κ disagree sharply (α is high but κ is low, or vice versa), it usually means the disagreement is concentrated on one specific aspect of the annotation — for example, the annotators agree on *which* narrators are in each branch but disagree on the *order*. That's a real signal: it tells the guide author which §3 subsection or §4 decision point needs sharpening.

### §7.3 — How to run IAA

When two annotators have overlapping rows, run:

```
python compute_iaa.py --annotators ann1.jsonl ann2.jsonl
```

The output is a Markdown report (`docs/annotation/iaa-report-<date>.md`) listing the pair's α, the pair's κ, the pass rate against the 0.80 threshold, and a per-row disagreement table that puts the two annotations side by side for every row they disagreed on. The disagreement table is the most useful output for everyone involved — it is the conversation starter for the IAA review.

### §7.4 — What to do when agreement is low

If α or κ falls below 0.80, there are three honest paths forward:

1. **The guide is unclear on the case type that triggered the disagreement.** Patch the guide; both annotators re-read the patched section; in many cases their disagreement resolves on its own. This is the most common cause and the most productive outcome.
2. **The row is genuinely ambiguous in source.** Both annotators bump it to `difficulty: 5`, write their reasoning in `notes`, and the row is documented as out-of-band per §4.5. The IAA report will continue to count it as a disagreement; that is the correct accounting.
3. **One annotator made a recoverable mistake.** Usually the calibration test would have caught this earlier; if it didn't, the right response is to re-run calibration with the problem cases included as a refresher and let the offending annotator self-correct.

What we do *not* do: silently overwrite one annotator's row with the other's, or pretend a disagreement didn't happen. The IAA report is part of the gold set's audit trail.


## §8 — Scope framing

This is a structural extraction task, distinct from classical isnad evaluation. The work is **descriptive**: we are recording what the text says about who narrated from whom. It is not prescriptive: we are not issuing verdicts on ʿadāla (uprightness of character), ḍabṭ (precision of memory), or any jarḥ wa taʿdīl judgment about the narrators we record. Those evaluative judgments are deeply specialized scholarly tasks; this guide does not authorize, equip, or substitute for them.

The distinction matters for several reasons. First, our extracted chains feed downstream into a graph database where individual narrators can be linked to their biographical entries, to other ḥadīths they transmitted, to ranks assigned to them by classical critics, and so on. That graph database may eventually layer rijāl annotations on top of our extracted structure — but that's a separate scholar-led effort with its own quality bar, its own gold set, and its own contributors. Mixing the two layers at the extraction stage would conflate the question "did the scribe write *X*?" with the question "is *X* a trustworthy transmitter?" — and both questions would suffer from the conflation.

Second, the workflow is more reliable when it is bounded. An annotator who is also asked to make rijāl judgments at the extraction stage is being asked to do two cognitive jobs at once, with one of them (rijāl) requiring training that this kit does not check for. The kit checks (via the calibration test) that an annotator can faithfully extract chain structure. It does not — and could not — check for the deep familiarity with biographical encyclopedias and methodological scholarship needed to issue narrator verdicts.

For annotators with formal Islamic studies training: think of this as the data-entry step that *precedes* the analytical work. Your training is over-spec for this task by design — we want the extraction step rock-solid before any more interpretive layers go on top. The fact that you can spot which narrators are which, and which are weak versus strong, is a real asset for the rijāl layer when it lands; for now, please channel that expertise into double-checking surface accuracy and edge cases, not into pre-grading the narrators we record.

This framing is also a kindness to non-specialists who may join the project later: they can contribute meaningfully at the extraction layer without being asked to make scholarly judgments they're not equipped to make. The kit deliberately makes a low bar of entry possible at this layer, while reserving the higher-bar evaluative layers for a different track.


## §9 — LLM-assisted draft annotation (optional)

A workflow exists where an annotator can ask a large language model — typically Claude Sonnet — to produce a draft `expected_branches` for a row, and then a human reviewer accepts, corrects, or rejects the draft. This is an *optional* productivity accelerator, not a substitute for human judgment, and the rules around it are strict.

**The workflow:**

1. Pull candidates via `pull_next_candidates.py` as you would for any annotation pass. You receive a `staging-<date>.jsonl` with `expected_branches: null` on each row.
2. *(Optional)* Run an LLM-draft step. This kit does not ship an LLM-draft script; the reusable prompt baseline lives at `conductor/tracks/tier2_llm_isnad_reconciliation_20260612/prompts/draft_annotation_v1.md` in the sibling tier-2 track. The model fills in proposed `expected_branches` and a confidence note.
3. **A human reviewer reads every drafted row.** No exceptions. The reviewer either accepts the draft as-is, edits it, or rejects and re-annotates from scratch. The reviewer also sets `difficulty` based on their judgment, not the model's.
4. Run `validate_annotation.py` against the reviewed file. Fix any failures.
5. Promote to gold via the `--promote` step. The gold file gets backed up automatically before the append.

**Who gets credit in `annotator`.** The `annotator` field for an LLM-assisted row is the **human reviewer's identifier**, never the model's. Writing `claude-sonnet-4.6` in `annotator` is forbidden. The human reviewer is the responsible party for that row; their initials in `annotator` mean they read it carefully and vouched for it.

**Known LLM failure modes for this task** (from research notes and the sibling track's prompt experiments):

- *Hallucinated narrators.* The model can invent a plausible-sounding name (~3–5 percent of rows in early experiments). Always check that every surface in the draft is in `text_ar`.
- *Name normalization drift.* The model may "helpfully" expand `سفيان` to `سفيان بن عيينة` — exactly the resolver pre-empting move §3.5 warns against. Reset to the surface form.
- *Branch flattening on `و` / `أو` coordination.* The model sometimes flattens a Case 3 co-transmitter pattern into a single narrator (e.g., turning `محمد بن المثنى وابن بشار` into a single string). Split it back.
- *Silent failures on malformed output.* The model can produce JSON that parses but is semantically wrong (right shape, wrong contents). The validator catches most of this; your reading catches the rest.
- *Unreliable pronoun handling.* Pronouns like `أبي` are the highest failure-rate cell — the model loves to pre-resolve. §3.6 / §4.4 is the rule; enforce it on the draft.

**Cost note (informational).** At current Claude Sonnet pricing, a draft costs around `$0.005` per row. Negligible compared to a human's time, but not zero — and the time cost of careful review still dominates. If you find the LLM draft is consistently wrong on a particular case type, talk to the maintainer; the prompt baseline can be tuned.

**The bright line, again:** an unverified LLM draft is **not** a valid gold annotation. The kit deliberately bakes in a human-in-the-loop checkpoint precisely so that productivity gains from drafting do not come at the cost of gold-set integrity.
