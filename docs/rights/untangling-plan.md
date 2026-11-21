---
type: plan
status: proposal-awaiting-owner-approval
prepared: 2026-11-21
depends_on: rights-register.md, collection_rights_proposal.csv
---

# Untangling plan: the rights gate

The smallest sequence of steps that gets the archive lawfully public. Evidence and reasoning are in
[rights-register.md](./rights-register.md); proposed rows in
[collection_rights_proposal.csv](./collection_rights_proposal.csv). This is not legal advice.

## Where we start

Nothing is public: `public_hadiths` shows only works whose `collection_rights.rights_status = 'cleared'`, and no
row exists. No English is public either: today's bundle holds 32,433 Thaqalayn English rows as
`source_provided` and 22,933 K6 rows as `source_status_unknown`; none is `human_verified` or
`source_verified`, and project machine translations stay in `translation_candidates`.

## The gate

A work goes public in Arabic when four things are true:

1. The terms of the copy we hold permit public display (register status `clear` or `clear_with_conditions`).
2. Every condition those terms set is met on the page: attribution, licence link, change notice, and for
   OpenITI non-commercial operation and share-alike on derived data.
3. The owner has recorded the decision in `collection_rights`, with `citation` pointing at the licence.
4. The work's identity is settled (title and compiler shown are right).

English for a work goes public only when its own rights are cleared as well. That is a second gate the schema
does not yet express (step 2).

## Steps

| # | Step | Unblocks | Blocked on | Size |
| --- | --- | --- | --- | --- |
| 1 | Owner confirms the site is non-commercial (no ads, paywall or data sales) | OpenITI works 11, 33, 34; the rijal-derived narrator data | Owner | Decision |
| 2 | Adopt an interim English rule: a reviewer may not mark provider English `source_verified` or `human_verified` for a work whose English is not cleared in the register. Record this in the curator guide. Optionally ask the app lane for an `english_policy` value meaning "no provider English" (code change, not made here) | Lets Arabic be cleared without leaking unlicensed English | Owner; app lane for the schema value | Decision, then small code change |
| 3 | Wire attribution: carry the Thaqalayn translator per work from `shia-hadith/v2_books/BookNames.json` (the unified master drops it), and render the notices in the register's last section on hadith pages, collection pages, a credits page and every export | Thaqalayn works; OpenITI works | Interface and data lanes | Small to medium |
| 4 | Settle identity flags that touch what the page says: the Rida appendix title; Zayd 698 vs 699 rows; Rabi' `rabi_0387` duplicate | Works 11, 33, 34 rows and titles | Data-gaps lane | Small |
| 5 | Owner records `cleared`, `reviewed_only`, with the `citation` from the CSV, for the 20 classical Thaqalayn works and the 3 OpenITI works, once steps 1–4 are done for them | **23 works, 34,372 hadith, public in Arabic** | Owner | Decision |
| 6 | Send request D to Thaqalayn (translations, Mu'jam, modern gradings) | Thaqalayn English for up to 20 works (about 32k rows); Mu'jam; Bihbudi/Muhsini grades | Thaqalayn | Email |
| 7 | When Thaqalayn confirms a translation is within its grant: set that work's `english_policy = source_provided_allowed` (owner decision, design §14 q5) and show the English with the translator credit. Rows still need `quality_status = 'complete'` (750 Thaqalayn rows fail on Arabic leakage today) | Thaqalayn English, per work | Thaqalayn reply; owner | Decision per work |
| 8 | Send requests A and B (sunnah.com; translation publishers), and in parallel rebase the six books' Arabic on OpenITI if the owner chooses | Works 1–6 | sunnah.com; publishers; owner's choice of route | Email; or a re-ingest track |
| 9 | Send request C (NabiMuhammad.com); in parallel consider OpenITI's Musnad Ahmad, Muwatta', Musnad al-Shafi'i | Works 7–10 | NabiMuhammad.com; owner | Email; or re-ingest |
| 10 | Send request F (Arees Institute). Until answered, keep lexicon fields off public pages (already the design) and source public narrator facts from the CC BY-NC-SA rijal texts | Public narrator biography fields | Arees Institute | Email |
| 11 | Machine translation as replacement English (below) | English for works whose provider English stays blocked | Curator review capacity | Ongoing |

Steps 1–5 need no one outside the project. They make 23 of 34 works (34,372 of 99,283 hadith, 34.6%) lawfully
public in Arabic.

## What is blocked, and on whom

| Blocked | Rows | On whom | Fallback if the answer is no or never comes |
| --- | ---: | --- | --- |
| Thaqalayn English, 20 works | 33,141 | Thaqalayn (request D) | Reviewed project translation (step 11) |
| Risalat al-Huquq English | 49 | Chittick's publisher, via Thaqalayn (E) | Project translation, 49 rows |
| Mu'jam al-Ahadith al-Mu'tabara, everything | 555 | Thaqalayn, then the author's estate (D) | Keep unpublished; its narrations also appear in the classical works it selects from |
| Bihbudi and Muhsini gradings | about 2,800 | Thaqalayn (D) | Show al-Majlisi only |
| Six books, Arabic | 34,441 | sunnah.com (A), or the owner's choice to rebase on OpenITI | Rebase on OpenITI (CC BY-NC-SA), new identities and numbering |
| Six books, English | 33,588 present | Translation publishers (B) | Project translation of the Arabic, reviewed |
| Pure Canon four works | 29,915 | NabiMuhammad.com (C) | Rebase Ahmad, Muwatta', Shafi'i on OpenITI; Darimi needs another open source |
| Public narrator-lexicon fields | 24,326 people | Arees Institute (F) | Rijal texts (CC BY-NC-SA) with citations |

## Machine translation as a replacement

Our own translation avoids a translator's copyright, but it is an adaptation of the Arabic it translates, so:

- **Rights follow the Arabic.** A translation of OpenITI text is CC BY-NC-SA 4.0. A translation of Thaqalayn
  Arabic is fine under CC BY 4.0 with attribution and a change notice ("translated by Shura wa Istehsan").
  A translation of K6 or Pure Canon Arabic inherits their `unclear` / `permission_needed` status: rebase or
  get permission first, or the translation is no cleaner than its source.
- **No copying of the restricted translation.** A machine translation must be produced from the Arabic alone.
  Prompting a model with, or post-editing toward, a restricted English (for example a K6 translation) would
  make it a derivative of that translation. Keep candidate provenance showing no English input.
- **Model terms.** `tencent/hy-mt2-30b-a3b` is Apache-2.0 per its model card
  (`.omc/research/hy-mt2-modelcard-2026-11-21.md`). The April 2026 runs used `llama3.1:8b` (Llama 3.1 Community
  License) and OpenRouter models; their output terms were not re-checked here. Record the model per row.
- **Review before public.** Machine output stays an unreviewed candidate until a curator reviews it against the
  Arabic (RUNBOOK rule; data contract: only `human_verified` and `source_verified` publish). The label on the
  page says it is a translation by the project, reviewed by a named curator.
- **Zaydi English needs re-alignment.** It was translated from an Archive.org OCR text, not the OpenITI text now
  in use; check each pair before review.

## What clearing does not change

- Rows still pass every quality gate (`source_text_status`, `quality_status`, chain and link rules).
- `dataset_versions` must still be release-class or carry a recorded preview override (design §14 q13).
- A cleared work's provider English stays hidden under `reviewed_only` unless a reviewer verifies it; step 2 is
  what stops that path for English that is not cleared.

## Re-check triggers

- Thaqalayn changes its Terms of Use (current: 2026-10-01), or answers request D.
- OpenITI publishes a release with different terms; pin release 2025.1.9 in citations until then.
- sunnah.com publishes an offline dump or licence.
- Any re-ingest from a new source: add a source card, an evidence capture and a register row before loading.
