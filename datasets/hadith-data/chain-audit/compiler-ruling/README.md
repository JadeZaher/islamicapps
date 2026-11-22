---
type: audit
---
# Owner rulings of 2026-11-22: the compiler as first transmitter, Abu ʿUbayda, the bare kunya rule

Projection `2026.11.22.12` against `2026.11.22.11` (production before). Rules: `pg_export/AGENTS.md` §Compiler as first
transmitter, §Bare kunya rule; data `pg_export/work_register.json`. Logs, projection and the database snapshots:
`development/compiler-chain-fix-2026-11-22/` (local).

| File | What |
| --- | --- |
| `diff_projections.py` | Identities and compiler heads, one projection against another; draws the three reading samples (seed 20261122) |
| `summary.json`, `row_diff.json` | Standing identities per tradition, changes by cause, heads per work; which columns changed in which table |
| `kunya_gained.tsv`, `kunya_lost.tsv`, `compiler_pairs.tsv` | The 30-item readings, each with a verdict and a note |
| `rows_hash.cjs` | Hash of every chain, mention and candidate row with the 0019 columns removed (before and after the migration) |
| `q.cjs`, `dev_align_0019.cjs` | A read-only query helper; the one-off alignment of the development database to the final 0019 |

## 1. Compiler heads

Every chain of 28 works is headed by its compiler; 6 works have none (Sahifat al-Rida, the modern Muʿjam, Nahj al-Balagha,
Kitab al-Duafa, Risalat al-Huquq, al-Shafiʿi: no transmitting compiler, or no chains). 1,862 chains get no head because the text
already writes him (Muwatta 1,780: «مالك» or «يحيى عن مالك»; al-Kafi 9, Zuhd 18, ...), by the reader tool's own alias rule
(`v3/work_profiles_v3.json`). `direct` (a pair can form) against `indirect` (head shown, no pair): `summary.json`
`compiler_heads_by_work` (for example Bukhari 7,682 / 358, al-Faqih 995 / 3,896, al-Rabiʿ 712 / 129).

Records: reused where a standing rule of the tradition already identifies the person: Malik (`narrator:rawi:20001`, 1,070 standing
Sunni mentions), Ahmad (`30007`, 130), al-Darimi (`30025`, 87), Abu Dawud (`30002`, 38), al-Kulayni (Riwayat N0156750, 7 Imami),
al-Husayn b. Saʿid (Riwayat N0152734, 242). Created under `work_register`, credited to the work: al-Bukhari, Muslim, al-Tirmidhi,
al-Nasaʾi, Ibn Majah (their lexicon rows 30001, 30003-30006 have no standing mention, so they were not reused; listed on the
record as not reused), al-Saduq (ten works), al-Mufid, al-Tusi, al-Nuʿmani, Ibn Qulawayh, al-Rabiʿ b. Habib (rabi_0001), Abu Khalid
al-Wasiti (zayd_0001, owner ruling). 12 compiler records and the Abu ʿUbayda record: 13 new narrators.

**Reading, 30 compiler pairs** (`compiler_pairs.tsv`, distinct compiler-teacher pairs drawn at random from the 2,584 the direct,
checked chains make): 30 of 30 right: the report opens with the compiler's own hearing from that shaykh (Bukhari from Musaddad,
Qabisa, Mahmud b. Ghaylan; al-Saduq from Ibn al-Walid; Ahmad from Ibn ʿUyayna, Muʾammal; al-Nasaʾi from Wasil b. ʿAbd al-Aʿla ...).
The shaykh's identity is the existing tier's, not re-judged here.

## 2. Abu ʿUbayda in Musnad al-Rabiʿ

«أبو عبيدة» / «أبي عبيدة» in al-Rabiʿ's chains: 712 mentions (664 written, the rest repeated by continuations) now stand as
`narrator:work:abu-ubayda-muslim-ibn-abi-karima`, "Abu ʿUbayda Muslim ibn Abi Karima al-Tamimi", basis `named_in_opening_isnad`
citing rabi_0001 «حدثني أبو عبيدة مسلم بن أبي كريمة التميمي عن جابر بن زيد الأزدي». Riwayat N0013779 «مسلم بن أيمن» stays on
each of them as an unconfirmed candidate (272 claims). Generalised as `named_in_full` in `work_register.json`: a transmitter the
work's own opening report names in full, where no source identity stands. Searched in al-Rabiʿ and Musnad Zayd: Jabir b. Zayd
(named in full in rabi_0001) already stands on Riwayat N0001547, so no record; no other entry this round.

## 3. Bare kunya rule

Standing identities (mentions), before -> after: Sunni 136,549 -> 132,215; Imami 28,489 -> 28,467; Ibadi 525 -> 1,303; Zaydi 2,566
-> 2,566. By cause (`summary.json`): Sunni lost 4,357 to the kunya rule and gained 4; Imami lost 22; Ibadi gained 66 (Abu Hurayra 60,
Abu Saʿid 4, Umm Salama 1, Abu Waʾil 1) and 712 Abu ʿUbayda; Sunni 25 gained and 6 lost by the chronology guard re-deciding pairs next to a withheld kunya.

**Reading, 30 gained** (`kunya_gained.tsv`): 30 of 30 right (Abu Hurayra = ʿAbd al-Rahman b. Sakhr after Jabir b. Zayd in al-Rabiʿ;
Abu Saʿid al-Khudri; Abu Hasin ʿUthman b. ʿAsim from Abu Bakr b. ʿAyyash in al-Nasaʾi).

**Reading, 30 lost** (`kunya_lost.tsv`): 28 of the 30 withheld identities were right for their chain (Abu Salih al-Samman from
al-Aʿmash, Abu Ishaq al-Sabiʿi, Abu Hurayra, Abu Musa, Abu Kurayb, Abu Muʿammar ...); 1 was wrong and the rule corrects it (Ibn
Majah's «أبو بكر» at position 0 is Abu Bakr b. Abi Shayba, not Ibn Abi Uways); 1 undecided (Ahmad's «أبو عبد الرحمن», likely
al-Muqriʾ, stood as Ibn Lahiʿa). **For the owner:** as ruled, the rule costs about 28 right identities per wrong one removed in
Sunni chains, because the sources name a second person for almost every common kunya somewhere in a large work ("5 people carry
«أبي هريرة»" in Musnad Ahmad's source). Reversal is one line (`KUNYA_RULE_AUTHORITIES = {}` in `external_identity.py`), or a
narrower count (carriers among confirmed claims only, or a share threshold) can be measured on these samples.

## 3a. Bare kunya rule narrowed (projection `2026.11.22.13`)

The first form (§3) counted people per kunya over the whole work's source and withheld 4,431 Sunni and Imami identities (4,379 in the
loaded projection) that the source asserted per report; 28 of 30 read were right. Four forms were measured on the same data: every bare-kunya
mention with a standing identity before the rule, 14,942 (4,431 withheld by the first form outside OpenITI, 60 in al-Rabiʿ that stand, 10,451
that stood anyway with one carrier). `kunya_options/` holds the scripts (`instrumentation.patch` dumps the per-mention carrier counts from the
export; `analyze.py`, `draw.py`, `show.py`), `reading_135.tsv` the verdicts. The reading is stratified, not 30 per side per option: the 4,431
were split into eight strata (dominance share of the asserted person among the kunya's assertions in the work's source, at least 98, 95 to 98,
90 to 95, below 90 percent; each with and without chronology support against a neighbour), 15 read per stratum and 30 in the largest-risk
one (below 90, no chronology support), 135 in all, excluding the 30 of §3. Each option's restored and withheld sides are the union of
strata, so every side's sample is at least 30, and population figures weight the sample by stratum size (the one unclear counted half).

| Option | Restored (of 4,431) | Read right (sample) | Still withheld | Read right (sample) | Right identities withheld | Wrong identities kept out |
| --- | --- | --- | --- | --- | --- | --- |
| (a) OpenITI only | 4,431 | 129.5 / 135 | 0 | - | 0 | 0 (about 159 wrong stand) |
| (b) 90% dominance | 3,158 | 90 / 90 | 1,273 | 39.5 / 45 | about 1,114 | about 159 |
| (b) 95% | 2,605 | 60 / 60 | 1,826 | 69.5 / 75 | about 1,667 | about 159 |
| (b) 98% | 1,974 | 30 / 30 | 2,457 | 99.5 / 105 | about 2,298 | about 159 |
| (c) 90% or chronology | 3,800 | 103 / 105 | 631 | 26.5 / 30 | about 557 | about 74 |
| (c) 95% or chronology | 3,536 | 88 / 90 | 895 | 41.5 / 45 | about 821 | about 74 |
| (c) 98% or chronology | 3,119 | 73 / 75 | 1,312 | 56.5 / 60 | about 1,238 | about 74 |

The 70 gains (al-Rabiʿ and four Sunni) have one carrier, so every option keeps them. Share does not separate the wrong from the right in
the low stratum (right at 0.05 to 0.41, wrong at 0.03 to 0.59), and chronology support does not either (Abu Dawud al-Tayalisi against
al-Sijistani, Abu Salih al-Samman against Abu Salih mawla ʿUthman). Every option that withholds buys back its wrong identities at seven to
seventeen right ones each, so **(a) ships**: the rule applies only in the three OpenITI works, with the source's per-report assertion standing
everywhere else, as before `9532839`. In the three OpenITI works the rule withholds nothing today (every bare-kunya identity there has one
carrier); it is the guard for those works.

Not done, and where to look: the 5 wrong of 45 in the low-share strata could be caught by a per-kunya list (Abu Dawud, Abu Salih, Abu Burda
with two bearers) read by an owner or scholar, which is a curation task, not a count.

