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
