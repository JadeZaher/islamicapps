# Insight 03 — Narrator Entity-Resolution Playbook (for THIS data)

**Role:** Emergent-Insight Agent 3 (Entity Resolution Playbook)
**Date:** 2026-05-16
**Inputs:** 06_archaeological, 04_systems, 08_negative_space, 02_contrarian, crucible_01, crucible_02 (in full); 01/03/05/07 skimmed.
**Repo assets sampled directly:** `datasets/narrator-data/all_rawis.csv` (24,326 data rows), `datasets/hadith-data/sunni_isnad.jsonl` (34,440 rows), `datasets/hadith-data/all_hadiths_unified.csv` (Bukhari + Al-Kāfi rows), `datasets/classify_attribution.py` (`_norm`).

> This is a *concrete* playbook keyed to the actual columns on disk, not a literature survey. The literature ceilings (06) and the schema mandates (crucible C1/C4/C5/C8, R1/R3/R7) are treated as hard constraints, not options. Where the crucible audit (crucible_02) corrected a persona, the corrected fact is used (e.g. brownfield; live UUID-per-run MERGE bug; 78.9k not 69k rows).

---

## 0. The single most important fact the other reports missed about THIS data

`all_rawis.csv` is **not just an authority list — it is already the controlled vocabulary AND a pre-built isnad graph with stable integer IDs.** Sampled rows prove:

- Column 1 `scholar_indx` = a stable editorial integer key (`1` = Prophet, `2` = Abu Bakr, `5` = ʿAlī …). Sparse/large IDs (`10500`, `19291`) confirm it is *not* row-order — it survives regen. This is exactly the `RAWI:scholar_indx` anchor Systems §3 / crucible C8 / R7 demand, and it **already exists on disk**.
- `name` carries **both scripts in one cell**: `"'Umar ibn al-Khattab ( عمر بن الخطاب بن نفيل ( رضي الله عنه"` — a transliterated form *and* the Arabic *and* an honorific, pre-joined. This single column is simultaneously the English-transliteration lexicon (for Thaqalayn chains) and the Arabic lexicon (for al-Kāfi / sunni_isnad).
- `teachers` / `students` are **name-with-embedded-id lists**: `"'Umar ibn al-Khattab [3] , 'Uthman ibn 'Affaan [4] ..."` and `teachers_inds`/`students_inds` are the same as **pure id lists** (`"1, 2"`, `"1, 2, 3"`). This is a ready-made `:NARRATED_FROM` edge set keyed by `scholar_indx` — no name resolution needed for the curated backbone.
- `death_date_hijri` / `birth_date_hijri` / `grade` (e.g. `"Comp.(RA) [1st Generation]"`, `"Rasool Allah"`) exist per narrator — the tabaqa/temporal-plausibility inputs (R4/R5) are present.
- **The unified CSV already half-resolves the Sunni side itself.** Bukhari row 1 has `chain_indx = "30418, 20005, 11062, 11213, 11042, 3"` — a column of `scholar_indx` IDs aligned to the regex `sanad` tokens. Resolution for a large slice of the Sunni corpus is *already a join, not an ML problem*. The hard ML problem is the residual where `chain_indx` is empty or wrong, plus the entire Imami/transliterated side.

**Consequence for the playbook:** the pipeline is not "resolve names from scratch." It is (1) **trust and stabilize the existing `scholar_indx` backbone**, (2) **reconcile the regex tokens that already have a `chain_indx`** (cheap audit, not ML), (3) **resolve the residual + the Imami/Thaqalayn side** with the tiered pipeline, (4) **never merge across traditions**.

---

## 1. The authority-file strategy

### 1.1 Primary controlled vocabulary = `all_rawis.csv` (`scholar_indx`)

`scholar_indx` is the **stable identity key for the whole graph**. Every `:Narrator` identity node MERGEs on:

```
narrator_key = "RAWI:" + scholar_indx        # resolved into all_rawis.csv
narrator_key = "EXT:"  + uuid5(NS_NARRATOR, norm_ar_name)   # unresolved residual
```

`uuid5` is deterministic → survives dataset regen (Systems §3, crucible R7). The `EXT:` namespace is a *holding pen*, never a permanent identity — every `EXT:` node is a HITL queue item (§2d).

This authority file is **Sunni/companion-leaning** (it is the muslimscholars.info / +24K-style table). It is authoritative for: Companions, the six-books transmitter pool, and any narrator with a `scholar_indx`. It is **structurally thin** for: Imami-only companions of the Imams (e.g. Zurāra, Muḥammad b. Muslim, al-ʿAlāʾ b. Razīn — note Muḥammad b. Muslim *does* appear because he is cross-tradition), and almost entirely absent for Zaydi/Ibadi-only transmitters.

### 1.2 Supplements (separate key spaces, joined only by SAME_AS)

| Supplement | Fills the gap for | How it attaches |
|---|---|---|
| **AR-Sanad 280K-v2** (`somaia02/Narrator-Disambiguation`) | Sunni surface-form lexicon ("appearance forms" صور الورود), Ibn-Ḥajar Taqrīb rank, Sunni narrated-from/to | New `:AuthorityRef {scheme:'AR-Sanad'}` + appended `appearanceForms[]` on the matching `RAWI:` node via human-confirmed `SAME_AS`. AR-Sanad is **never** an identity key here — `scholar_indx` is. AR-Sanad supplies *aliases and the Sunni Assessment*, not identity. |
| **al-Khūʾī, *Muʿjam Rijāl al-Ḥadīth*** (via Thaqalayn / Dirāyat) | The Imami transmitter pool `all_rawis` lacks (15,000+ Shia narrators) | A **separate Imami authority key space**: `narrator_key = "KHUI:" + khui_entry_id`. Imami-only narrators get a `KHUI:` identity node, *not* a `RAWI:` one. Cross-tradition persons (a Companion in both) get one identity node + a `SAME_AS` to the other scheme (§3.4). |
| **AR-Sanad artificial-sanad generator** | Distant-supervision training pairs for the Imami side (none exist) | Run the generator over the `teachers_inds`/`students_inds` graph + the Imami `chain_indx` graph to mint training chains; HITL-audit a sample before training (06f). |
| OpenITI / Wikidata P13870 | Interop hub only | `:AuthorityRef {scheme:'Wikidata'|'OpenITI'}`, confidence-scored, never a merge. |

### 1.3 Identity node vs tradition-tagged Assessment (the hard separation — crucible C1 / R1)

This is non-negotiable and the most-corroborated finding in the whole corpus (7/8 personas). The `all_rawis.csv` `grade` column (`"Comp.(RA) [1st Generation]"`, `"Rasool Allah"`) is itself a *Sunni-tradition tabaqa/status label* — it must **not** be stored as a scalar on the identity node.

```cypher
(:Narrator {                          // PHYSICAL IDENTITY — tradition-neutral, one per person
   id, narrator_key,                  // "RAWI:5" | "KHUI:..." | "EXT:uuid5..."
   scholar_indx,                      // null for KHUI/EXT
   canonical_name_ar, canonical_name_en,
   components,                        // {ism,[nasab],kunya,laqab,nisba} — §2a
   appearanceForms[],                 // surface strings seen, all scripts
   death_year_hijri, birth_year_hijri, tabaqa,  // from all_rawis date cols (nullable)
   identity_confidence,               // distinct from sanad_confidence (08a)
   resolution_method,                 // 'rawis_chain_indx'|'exact'|'blocked'|'rerank'|'human'
   first_seen_version, last_seen_version })

(:Narrator)<-[:ASSESSES]-(:Assessment {
   tradition:'Sunni'|'Imami'|'Zaydi'|'Ibadi'|'Rida',
   grade, grade_scheme:'IbnHajar-Taqrib'|'Khui'|'rawis-status'|...,
   critic, source_work, edition, sect_tag, confidence,
   license:'public_domain_classical'|'modern_critical_edition_restricted' })  // R6

(:Narrator)-[:SAME_AS {confidence, asserted_by:'human', evidence}]->(:AuthorityRef|:Narrator)
```

Rules (crucible C1, C4, R1, R3, R6):
1. **Identity pass and Assessment pass are separate ETL stages.** Resolve who the person is; *then* attach gradings, each stamped tradition/critic/work/scheme.
2. **Never a scalar `reliability`/`grade` on `:Narrator`.** The `all_rawis.grade` value becomes an `:Assessment {tradition:'Sunni', grade_scheme:'rawis-status'}`.
3. **Absence is explicit:** a narrator with no Imami verdict gets *no* Imami `:Assessment`; a query for Imami reliability returns null + `reason:'no_extant_evaluation_in_tradition'`, **never** an inherited Sunni grade.
4. The al-Kāfi `gradings_full` cell already carries proper provenance (`"Allamah Baqir al-Majlisi: صحيح (Mirʾāt al-ʿUqūl ...)"`) — parse it into per-critic `:Assessment` nodes; this is a *hadith*-level grading but the pattern (critic+work+edition) is the same and must be preserved (R6 copyright trap: store citation, flag restricted editions).

---

## 2. The tiered resolution pipeline

### (a) Tier 0 — normalization + name decomposition

**Reuse `classify_attribution._norm` verbatim** (it is already battle-tested on the fully-vocalized Imami corpus):

```python
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")   # tashkīl + tatwīl
_ALEF = re.compile(r"[آأإٱ]")
def _norm(s):                       # strip tashkīl/tatwīl; آأإٱ→ا; ى→ي
    s = _DIACRITICS.sub("", s or ""); s = _ALEF.sub("ا", s)
    return s.replace("ى", "ي")
```

Extend (do not fork) it for ER with two additions used **only for matching keys**, never for stored display (the function's own docstring already mandates verbatim storage):
- `tā' marbūṭa` ة→ه and unify `ابن/بن/ب.` (06 normalization list) — add to a `_norm_er(s)` wrapper that calls `_norm` first.
- A **transliteration bridge**: romanize the Arabic `canonical_name_ar` to a canonical ASCII scheme *and* keep the `all_rawis` English form; match Thaqalayn English chains in the romanized space (Freeman equivalence-class Levenshtein, 06). Do **not** compare scripts directly.

**Decompose every surface form into a typed bag** (06 backbone):
- kunya ← token starts `ابو/ابي/ام` (normalized) or `Abu/Abi/Umm`
- nasab ← `ابن/بن/ب.` / `bint` chain (recurse)
- nisba ← ends `-i/-iyy/-iyya` or leads `al-` and is a place/tribe (cross-check al-Thurayya for place nisbas)
- laqab ← remaining `al-`-prefixed honorific
- ism ← residual head token

`all_rawis.name` parses cleanly: `"'Umar ibn al-Khattab ( عمر بن الخطاب بن نفيل ( رضي الله عنه"` → `{ism:'Umar, nasab:[al-Khattab, Nufayl], honorific:raḍiya-llāhu-ʿanhu}` with the Arabic span captured as `canonical_name_ar`. Build the lexicon once from all 24,326 rows: `appearanceForms[]` ← {full en, full ar, ism+nasab, kunya alone, shuhra}.

### (b) Tier 1 — exact + blocked candidate lookup (target ~94% of *resolvable* tokens)

Cheapest path first (06 cost ladder; crucible C5 ~94/6 split):

1. **`chain_indx` join (THIS data's shortcut, do this first).** Where `all_hadiths_unified.csv` has a populated `chain_indx` (e.g. Bukhari `"30418, 20005, 11062, 11213, 11042, 3"`), the Sunni sanad is *already resolved to `scholar_indx`*. Zip `sanad` tokens ↔ `chain_indx` IDs positionally, MERGE `RAWI:<id>` nodes directly. This is an **audit + join, not ML** — but it is noisy: `chain_indx` length need not equal `sanad` length (Bukhari row1 sanad has 6 tokens incl. the malformed `"ه سمع علقمة بن وقاص الليثي"`; chain_indx has 6 — align by length, flag mismatches to HITL).
2. **Exact appearance-form lookup** (normalized) against the `all_rawis` lexicon for tokens with no/short `chain_indx`.
3. **Component-keyed blocking:** block on `(norm ism, norm father-ism)` or `(kunya, nisba)`.
4. **Phonetic** (Soundex+Metaphone on romanized) for Thaqalayn transliteration drift.
5. **Graph-structural blocking (highest precision, free here):** the resolved *neighbors* in the chain + the `teachers_inds`/`students_inds` adjacency in `all_rawis` collapse candidates. "أبو جعفر" whose next link resolves to al-Kulaynī's teacher generation ⇒ candidate ≠ al-Bāqir.

Honesty: the "~94%" is AR-Sanad-synthetic-Sunni (06/crucible_02 §3). On *this* data the exact-lookup coverage is **unproven and will be lower**; `chain_indx` rescues much of the Sunni side but the Imami `chain_indx` is sparse (al-Kāfi row 34443 `chain_indx` empty though the English `text_en` spells the chain out) and Thaqalayn is English. **Build the mechanism; do not promise 94% on this corpus.**

### (c) Tier 2 — the ambiguous collision core: retrieve → rerank → confidence

The ~3,477-style ambiguous-form core (06) — kunya/laqab-only, bare "Muḥammad b. …", "Sufyān", "Hishām", "Abū Jaʿfar". Two-stage (Mahmoud 2024 / Mosa 2025 blueprint, re-implementable on Neo4j GDS + HF — no proprietary code):

1. **Retrieve (graph prior):** GDS over the `:NARRATED_FROM` graph (built from `teachers_inds`/`students_inds` + resolved chains). Candidate set = narrators whose neighbor-set and **tabaqa/death-year window** (from `all_rawis` `death_date_hijri`) are consistent with the already-resolved adjacent links. PageRank/degree as the "network prominence" term.
2. **Rerank (cross-encoder):** an Arabic/classical-BERT cross-encoder over the chain window scoring each candidate's profile vs context. Domain-adapt on Sanadset 650K MLM, fine-tune on AR-Sanad + generator-minted Imami pairs.
3. **Confidence:** combine component-weighted string sim (ism/nasab high & selective; **kunya/laqab low weight, high collision**) + phonetic + cross-encoder + graph prior + **temporal feasibility hard-prune** (a narrator cannot transmit from someone who died after his own generation — cheap, very high precision, ties to R4). Emit `identity_confidence` and top1−top2 margin.

### (d) Tier 3 — mandatory human-in-the-loop queue

Route to a rijāl expert (06f, crucible R3/R8) — **non-negotiable**:
- Any candidate with small top1−top2 margin or kunya/laqab-only match.
- Every `EXT:` (unresolved) node.
- **ALL cross-tradition `SAME_AS` assertions — auto-suggest, never auto-merge.**
- `chain_indx`↔`sanad` length mismatches.
- A sample of distant-supervision training labels before training.
- Active learning: prioritize highest-uncertainty / highest-graph-centrality nodes; feed confirmations back as training data (closes the augmentation loop on real, expert-verified pairs).

---

## 3. Hard cases, concretely

### 3.1 "Abu Ja'far" = al-Kulaynī vs al-Bāqir vs al-Jawād

This collision is **literally in the sampled data**. `all_hadiths_unified.csv` row 34443 (al-Kāfi 1.1.1), `text_en`:

> "**Abu Ja'far** Muhammad b. Ya'qub (al-Kulayni) has said: A number of our people … narrated from … that **Abu Ja'far** (al-Baqir) (as) has said:"

and the Arabic `text_ar`: `أَخْبَرَنَا أَبُو جَعْفَرٍ مُحَمَّدُ بْنُ يَعْقُوبَ … عَنْ ابي جعفر (عَلَيْهِ السَّلام)`.

Two different people, same kunya, same chain. Disambiguation signals available **in this row**:
1. **Chain position.** First-position "Abū Jaʿfar" + immediately followed by `محمد بن يعقوب` (nasab) ⇒ the **collector** = al-Kulaynī (d. 329). Resolve by the *attached nasab*, not the kunya.
2. **Terminal Imam marker.** `(عليه السلام)` / `(as)` honorific + chain-terminal position + `attributed_to`/`narration_level` already computed by `classify_attribution.py` (this row: `narration_level = imam`, `school = Ahl al-Bayt`) ⇒ the Imam Abū Jaʿfar = al-Bāqir (the 5th Imam; al-Jawād is "Abū Jaʿfar al-Thānī" and is excluded here by tabaqa — al-Bāqir d.114 fits the chain generation, al-Jawād d.220 does not).
3. **Patronymic/tabaqa prune.** al-Kulaynī (collector, d.329), al-Bāqir (Imam, d.114), al-Jawād (Imam, d.220) are separated by death-year windows; the temporal-feasibility prune (Tier 2 step 3) eliminates two of three given the resolved neighbors.

Rule: **kunya alone never resolves; the engine must treat kunya as low-selectivity and require nasab / chain-position / Imam-marker / tabaqa to fire.** `classify_attribution.py`'s existing `narration_level`+`attributed_to` output is a *free feature* for this — wire it in as a Tier-2 signal.

### 3.2 English-transliterated Thaqalayn names vs Arabic `all_rawis`

al-Kāfi rows carry the chain **only in English `text_en`** ("Muhammad b. Yahya al-‘Attar", "Hasan b. Mahbub", "al-’Ala b. Razin", "Muhammad b. Muslim") — Arabic `text_ar` has it too here, but Thaqalayn export is English-primary and `chain_indx` is empty for this row. `all_rawis.name` contains the English transliteration *and* Arabic in one cell, so:
- Match Thaqalayn English tokens against the **English half** of `all_rawis.name` (romanized, equivalence-class Levenshtein for `'Ala`/`al-A'la`, `Ya'qub`/`Yaqub`, `b.`/`ibn`, ʿayn/hamza apostrophe noise).
- Where the Arabic `text_ar` is also present (al-Kāfi has both), resolve in **Arabic space via `_norm`** (higher precision) and use the English only to corroborate. Prefer Arabic when both exist.
- Imami-only transmitters (al-ʿAlāʾ b. Razīn, Ḥasan b. Maḥbūb) will frequently miss `all_rawis` → land in `KHUI:` space or `EXT:` queue (§1.2). Muḥammad b. Muslim *may* hit `all_rawis`; if so it is a cross-tradition node (§3.4), not a Sunni one.

### 3.3 Mubham (unnamed) and muhmal (unspecified)

- **Mubham**: `"عدة من أصحابنا"` ("a number of our people"), `"أبيه"` ("from his father" — sunni_isnad row 2 `companion:"أبيه"`), `"رجل"`. These are **not entities** — do **not** mint `EXT:` nodes. Model as `(:Chain)-[:LINK {order, mubham:true, surface:'عدة من أصحابنا'}]->(:UnresolvedLink)` or a typed placeholder, excluded from centrality (08b). `"أبيه"` is *relationally* resolvable: father-of(previous link) — attempt graph resolution via `all_rawis.parents`, else mark mubham.
- **Muhmal** (named but underspecified, "Muḥammad" alone): goes to Tier 2; if margin stays low → `EXT:` + HITL. Never silently bind to the most famous homonym (the over-merge failure, 08a / Contrarian).
- The malformed regex token `"ه سمع علقمة بن وقاص الليثي"` (sunni_isnad row 0 — leading `ه` is OCR/regex bleed) → normalize strips noise, but length-mismatch vs `chain_indx` flags it to HITL; **do not** create an `EXT:` node for a parse artifact.

### 3.4 Same physical narrator, Sunni vs Shia evaluation

One identity node, N tradition-tagged `:Assessment` nodes (§1.3). Worked example from sampled data — **Muḥammad b. Muslim** (al-Kāfi chain) is a Kūfan companion of al-Bāqir/al-Ṣādiq who *also* appears in Sunni transmission:
- ONE `:Narrator` identity node (whichever scheme resolves first becomes `narrator_key`; if `RAWI:` and `KHUI:` both, `RAWI:` is the key and a human-confirmed `:SAME_AS {asserted_by:'human'}` links the `KHUI:` `:AuthorityRef`).
- `(:Narrator)<-[:ASSESSES]-(:Assessment {tradition:'Imami', grade:'thiqa', critic:'al-Najāshī', source_work:'Rijāl al-Najāshī'})`
- `(:Narrator)<-[:ASSESSES]-(:Assessment {tradition:'Sunni', grade:<Ibn-Ḥajar rank>, grade_scheme:'IbnHajar-Taqrib', source_work:'Taqrīb'})`
- The two are **never reconciled into one number**. A Sunni-lens query traverses `ASSESSES {tradition:'Sunni'}`; an Imami-lens query the Imami ones; the disagreement is first-class queryable data, not a merge conflict (crucible C1, R1).
- The `all_rawis.grade` ("Narrator [ ع - صحابة ]" style) becomes a third `:Assessment {tradition:'Sunni', grade_scheme:'rawis-status'}` — provenance: this authority file. It does **not** override al-Najāshī for an Imami query.

---

## 4. Honest accuracy ceilings & where human review is non-negotiable

| Slice | Realistic ceiling | Basis |
|---|---|---|
| Sunni, has populated `chain_indx` | High (it's a join + audit) | Direct from data; *but* `chain_indx`↔`sanad` length mismatch & malformed tokens (seen in row 0) inject error — audit, don't trust blindly |
| Sunni, no `chain_indx`, in-distribution Arabic | **~83 F1 (low-to-mid 80s%)** | AR-Sanad real six-books (06); the 92.9/94.6/97.8 numbers are synthetic-leaning, do **not** quote them for this corpus (crucible_02 §1) |
| Imami al-Kāfi (Arabic `text_ar` present) | **Unmeasured, below Sunni** | No published Shia benchmark; `_norm` handles vocalization but no Imami training data exists until generator-bootstrapped |
| Thaqalayn English-transliterated chains | **Unmeasured, lowest** | Cross-script ER, no published numbers, transliteration many-to-many |
| Cross-tradition `SAME_AS` | **Unmeasured — research-grade** | *No* system reports cross-tradition linking accuracy (06, crucible_02). Treat as unsolved. |

**Human review is non-negotiable for:** (1) every cross-tradition `SAME_AS` (theological stakes — Contrarian R3/R8); (2) every `EXT:` node; (3) all kunya/laqab-only or small-margin resolutions (the ambiguous core *is* the high-value target and the lowest-accuracy slice); (4) `chain_indx`↔`sanad` mismatches; (5) distant-supervision label audit before training. Confidence-threshold auto-accept only the high-confidence resolved slice; **gate every downstream analytic on `identity_confidence` AND `sanad_confidence`**, report ranges across strata, never point values (crucible C5/C6, R2). The graph is a sound *navigational* artifact on day one; it is **not** a sound *analytical engine* until resolution + uncertainty propagation are done.

### Stable-ID scheme (survives dataset regen — crucible C8 / R7)

```
RESOLVED (in all_rawis)  →  narrator_key = "RAWI:" + scholar_indx        # editorial, regen-stable
IMAMI authority (al-Khūʾī)→  narrator_key = "KHUI:" + khui_entry_id        # separate key space
UNRESOLVED residual      →  narrator_key = "EXT:"  + uuid5(NS, _norm_er(name_ar))  # deterministic
MUBHAM / parse-artifact  →  NOT an entity — placeholder link, never a node

# Survival mechanics:
- MERGE on narrator_key, never on the regen-reassigned CSV `id` (Systems §0; live bug: import-datasets.ts:370-389 MERGEs on uuidv4()-per-run — FIX FIRST).
- narrator_aliases.csv: raw_surface → narrator_key. An OCR/spelling fix adds an alias row; key never drifts (older cluster retains ID).
- merge_history table + DatasetVersion node + old→new crosswalk (added/removed/merged/split); first_seen/last_seen_version on nodes; tombstone, never delete (project memory: never delete data).
- EXT:→RAWI:/KHUI: promotion on HITL confirmation is recorded as an alias + merge_history row, NOT a key rewrite that orphans edges.
```

This makes re-running regen a no-op for identity, keeps the isnad subgraph intact across name corrections, and keeps Sunni/Imami identity *partitioned by key space* so a naive cross-tradition merge is structurally impossible without an explicit, human-confirmed `SAME_AS`.
