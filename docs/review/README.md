---
type: design
status: proposal for the owner, 2026-11-21
---

# Review, discussion and citation: one model

Every claim a reader sees can be reviewed and discussed in the same way. Files in this directory:

| File | What |
| --- | --- |
| `README.md` | This brief: the model, a worked example, how today's tables map, the migration, decisions for the owner |
| `ai-review.md` | Generated from `src/lib/review/procedures.ts`: every AI-review procedure that exists today. Same data as `/method` |
| `citations.md` | The one citation standard, as fields; what each data lane must emit |
| `specialist-plan.md` | Which model reviews what, sampling, and the pilot ready to run |
| `schema-proposal.ts` | The tables, as Drizzle definitions that type-check (a proposal, not schema) |
| `model-registry-additions.json` | Proposed model-registry entries for the specialists |

## The model

**A claim** is anything a reader is told: an identity for a name in a chain, a correspondence between two tellings, a
translation, a grading, a verdict, a date or place, a rijal link, an event or era, a Qur'an citation, a number. It
has a **claim key** naming what is asserted (`identity|mention:k6:19122:0001:0001|narrator:rawi:20031`), not the
machine row that proposed it, so reviews survive a change of method or a second source proposing the same thing
(`src/lib/review/claim-key.ts`). Its **content hash** covers every text it depends on; when a text changes, earlier
reviews become reviews "of an earlier text": listed, never counted, never silently carried over.

**AI review**, two kinds, never blurred:

1. **Checked by rule**: deterministic code with a procedure id, version and code hash, no model. Example: "the
   source's index and the Arabic agree position by position".
2. **AI specialist review**: a fresh model given one saved system prompt (`reviews/ai/prompts/*.md`, the prompt is
   the documentation) and one packet of evidence, cut off from how the claim was produced. Recorded with model id,
   prompt hash, packet hash, UTC start and finish, outcome (`supports`, `contradicts`, `contested`,
   `insufficient_evidence`), reasons, quoted evidence (checked to occur in the packet), uncertainty.

Both link to `/method#<kind>`, which states the rule, the evidence, the measured accuracy with sample and location
(or says plainly that none exists), the failure modes and the credits. "AI-reviewed" never implies a person.

**Human reviews**, any number, one row each: reviewer, stance (`agrees`, `qualifies`, `disagrees`, `cannot_decide`),
note, citations (the one standard), optional tradition context and AI-drafting disclosure, the content hash read,
supersession without deletion. Stances are views, not votes: no "abstain", no weights, no percentage. `qualifies`
captures "right in substance, with a correction"; `cannot_decide` maps the existing `undecidable` and `uncertain`.

**How a claim is summarised** (`src/lib/review/summary.ts`, tested): one current view per reviewer, counted by
stance in a fixed order, e.g. "AI-reviewed (checked by rule) · 3 human reviews: 2 agree, 1 qualifies". Any
disagreement, or a contested AI review, makes it **Reviewers differ**: both views are shown in full, nothing is
hidden. Human reviews never remove a claim from view and never flip the AI outcome. A reader opens every review.

**What human reviews change.** Display: the summary line and the list of reviews. Analysis (the teacher-to-student
network and chain completeness): a live disagreement by a permitted reviewer marks the claim contested, and
contested claims already stay out of analysis. Publication: unchanged; AI review is enough to publish.

**Discussion anchored to context.** A thread hangs on an **anchor**: a typed reference to a report, its tellings, a
chain, one name at one position, a claim, a span of the Arabic (code-point range plus the text's hash and the quoted
words), a narrator, a rijal entry, an event, an era, a place, or one cell of a perspectives matrix. Threads are found
from every page the anchor touches, computed at read time: the report page, every narrator page a candidate for
that name points to, and one hop through correspondences to the other tellings (labelled with the telling's work and
tradition). When a text or chain changes, the anchor is never dropped: a span re-anchors automatically when its
quoted words occur exactly once in the new text, otherwise the thread is kept and marked "needs re-anchoring".
Posts keep every edit as a revision, cite in the same standard, and reply in a tree. A human review may open or join
a thread (`thread_id`); a post is never counted as a review.

**Perspectives matrix** (`src/lib/review/perspectives.ts`). A narrator (or a report's gradings) shows rows = sources
of a view (each rijal author and work, each critic quoted by name, the compiler, the lexicon, each dataset, each AI
review, each human review), grouped by tradition alphabetically with "no tradition stated" last, and columns =
aspects (identity, reliability, death year, birth year, generation, places, teachers and students, rijal entry; for
a report: grading, tellings, English, Qur'an, number). Human and AI reviews are simply more rows, marked by kind.
Every cell carries its claim key, so a review or a thread can address one cell.

**Traditions side by side.** Threads, rows and reviews are never ordered by tradition except alphabetically within
a grouping; a reviewer's tradition context is a stated standpoint shown beside their name, never a weight.

**Etiquette and moderation.** The contribution plan's code of adab applies. No anonymous rulings: every review and
post carries a named person. Withdrawal is retirement with a stated ground (adab, off topic, personal information,
copyright, duplicate, author's request) and a visible tombstone; disagreement is never a ground. Moderation actions
are `curation_audit` rows.

**AI in discussion.** An AI post (a summary or a draft) is always marked with its model and the person who asked for
it, is never counted as a human review, and cannot hold a stance. A person who drafted with a model says so; the
review remains theirs.

**Reviewers.** Capabilities, not ranks: `review`, `discuss`, `propose`, `endorse`, `moderate`, each per field
(identity, text, translation, grading, biography, history, quran), dated, retired rather than deleted. Granted by the
owner, or by an **endorsement** from a reviewer holding `endorse` in that field. It is called an endorsement, not an
ijaza: an ijaza licenses transmission, which this does not. Reviewers are sources: each review is credited to its
reviewer like any other source. **Before sign-in exists**, reviews arrive as files by pull request (`reviews/`,
format and validator there): the merge is the grant and git history the audit. Sign-in can stay off.

## Worked example: Abu Dawud 4168 (`hadith:k6:19122`)

Real rows from production, read 2026-11-21. The two human reviews and the thread are **illustrations**: no such
reviews exist yet.

**The report.** `حدثنا أحمد بن حنبل، ومسدد، قالا حدثنا يحيى، عن عبيد الله، قال حدثني نافع، عن عبد الله، قال لعن رسول
الله صلى الله عليه وسلم الواصلة والمستوصلة والواشمة والمستوشمة`. Two chains (Ahmad b. Hanbal and Musaddad, both
"said: Yahya narrated to us").

**Its tellings** (`public_report_correspondences`): five Sunni (`k6:29550`, `k6:29551`, `k6:29706`, `k6:5750`,
`k6:5754`, variant wording, Jaccard 0.54-0.65) and two Imami, both in al-Saduq's *Maʿani al-Akhbar*:
no. 274 (`thaqalayn:77fead5f…`, J 0.61), through Jaʿfar b. Muhammad to ʿAli, with a longer list; and no. 275
(`thaqalayn:06c871a7…`, J 0.41), Abu ʿAbd Allah quoting the curse and adding a gloss: `يعني الزانية والقوادة`.

**A name and its claim.** Chain 2, position 1, `يحيى`. Claim `identity|mention:k6:19122:0001:0001|narrator:rawi:20031`
(Yahya b. Saʿid b. Farrukh al-Qattan). AI review: **checked by rule**, `identity-source-index-confirmed-by-text`
version 2026.11.21, outcome `supports` (agreement class `multi_branch_all_source_ids_aligned`), credited `K6I`,
`MSD`, `SUN`. It is in the identity pilot (`isnad-identity/pilot-1`) with a recorded answer, so it will also carry an
**AI specialist review** once the pilot runs.

The same `يحيى` in **chain 1** has no candidate and shows "Not identified": the source index aligns only Ahmad b.
Hanbal there, and the rule does not carry an identity across branches that converge (`قالا حدثنا يحيى`). This is
exactly where a person adds what the machine cannot.

**Two human reviews (illustrative).**

- *Reviewer A agrees* with the chain-2 identity, citing Ibn Hajar, *Taqrib al-Tahdhib*, ed. Awwama (Dar al-Rashid,
  1406/1986), entry 7557, vol. 1 p. 591: `يحيى بن سعيد بن فروخ … أبو سعيد القطان البصري ثقة متقن حافظ إمام قدوة من
  كبار التاسعة` (`RIJ`, CC BY-NC-SA 4.0). Notably the archive's own lexicon-to-Taqrib link missed this entry (its
  headword is cut by a vocalisation gloss), so the human citation adds evidence the rule did not have.
- *Reviewer B disagrees* with a different claim: that Maʿani al-Akhbar 275 is a variant telling of this report.
  Stance `disagrees`, reading "same ruling, different speaker", citing the Thaqalayn text of no. 275 with the span of
  `يعني الزانية والقوادة`: the Imami text is Abu ʿAbd Allah's explanation that gives the two terms another sense.
  The pair then shows **Reviewers differ**: the rule's "variant wording", B's view and its citation, side by side.
  The link is not removed.

**A thread anchored to the name.** Reviewer A opens "Is chain 1's Yahya the same as chain 2's?" on the anchor
`mention|mention:k6:19122:0000:0001` (bound to the mention's surface hash), citing the convergence `قالا حدثنا يحيى`,
and proposes the identity for chain 1 (a data proposal, needing `propose`). The thread appears:

- on Abu Dawud 4168, beside chain 1, position 1;
- on Yahya al-Qattan's narrator page, under "Discussed names in chains", because a candidate or proposal for that
  mention names him;
- on Maʿani al-Akhbar 274 and 275, under "On other tellings", labelled "Abu Dawud 4168 · Sunni", one hop through
  the correspondence, beside the Imami tellings' own threads; no tradition's threads come first.

## How today's mechanisms map (nothing loaded is lost)

| Today | Rows | Becomes |
| --- | ---: | --- |
| `chain_mention_candidates` (basis, detail) | 212,921 | Stays: the claims. Each live row gets an `ai_reviews` rule row (`basis` → procedure id) |
| `chain_mentions.narrator_id`, `resolution` | | Stays: the standing identity, derived as now |
| `narrator_surface_decisions` | 0 | Stays as the scoped *identity proposal* replayed onto a review unit; a decision becomes a proposal plus its proposer's `agrees` review |
| `report_correspondence_candidates`, `_cluster_members` | 135,825 | Stay: the claims. Rule rows in `ai_reviews` (method version) |
| `report_correspondence_decisions` | 0 | Stays empty; then a view over `human_reviews` (confirmed = agrees, rejected = disagrees, uncertain = cannot_decide, a different reading = qualifies) |
| `report_correspondence_shown_pairs` rule "a rejection hides the pair" | | Changes: a disagreement shows the pair as Reviewers differ (owner decision 3) |
| `translations.state`, `review_state_raw` | 66,776 | Stay: who supplied the English. Reviews of English live in `human_reviews` keyed by report and language, bound to both texts' hashes |
| `hadith_assessments.review_state` | 44,937 | Stays. Cited rulings get rule rows; collection labels are not claims |
| `narrator_assessments.status`, `narrator_bios.status` | 20, 21 | Stay; published only when cited, as now; reviewed as claims |
| `historical_events`, `epochs` verification and `publication_ready` | 54, 38 | Stay; the loader sets them from the history rule (`source_verified` = passes the cited-passage rule) |
| `citations`, `bibliographic_works`, `editions` | | Stay; `contribution_citations` points at them where a work is already known |
| `curation_audit` | 200 | Stays: every contribution write and every re-anchoring is a row |

The six planned contribution tables (design §5.15): `contributors` **kept** (roles move to dated
`contributor_permissions`); `contributor_endorsements` **kept, renamed in prose** from "digital ijazah" to
endorsement; `submissions` **kept, narrowed** to data proposals (commentary, translation, correction, collection);
`submission_reviews` **replaced** by `human_reviews` (a submission's content is a claim like any other);
`submission_comments` **replaced** by discussion anchored to the submission's claims; `collection_imports` **kept**.
Added: `ai_reviews`, `contributor_permissions`, `contribution_citations`, `discussion_anchors`,
`discussion_threads`, `discussion_posts`, `discussion_post_revisions`.

## Migration, first steps

1. **Now (this change, no database change):** `/method`, the procedure registry, the citation standard and
   validators, the reviews-as-files format, the specialist prompts, packets and recorder.
2. **Run the two pilots** (`specialist-plan.md`); publish measured agreement on `/method`.
3. **Migration `00NN_review_core`** (additive): the enums, `ai_reviews`, `contributors`, `contributor_permissions`,
   `contributor_endorsements`, `human_reviews`, `contribution_citations`. All empty.
4. **Loader:** emit one rule `ai_reviews` row per live claim from the existing pipeline tables in the same
   transaction; load `reviews/ai/records/*.jsonl`. New data invariants: every live candidate has exactly one live
   rule row; every procedure id is in the registry; every specialist row's prompt hash is in
   `reviews/ai/specialists.json`.
5. **Contribution loader** for `reviews/` files (validator first), then the `claim_review_summary` view, then the
   page line "AI-reviewed (checked by rule) · N human reviews" linking to `/method#<kind>`.
6. **Discussion tables and `discussion_surfaces`** with the contribution system after cutover; the perspectives view
   once rijal entries and cited assertions load.
7. Redefine the correspondence display views to read `human_reviews`; retire the empty decision table's writers.

## Decisions for the owner

1. **The word "verified".** Recommendation: stop using it for readers. Show "AI-reviewed" (rule or specialist) and
   "N human reviews: …". Keep the stored enum values. Plural review makes "verified" ambiguous.
2. **Who may review at first.** Recommendation: the owner grants `review` per field by merging a reviewer file;
   endorsement opens once there are three reviewers in a field.
3. **A human disagreement and the display rule.** Recommendation: a disagreement never hides a claim (today a
   rejected correspondence is hidden); it shows "Reviewers differ" and both views.
4. **Human agreement and analysis.** Recommendation: human reviews do not add a claim to the network or chain
   completeness by count; a person's *proposal* (chain 1's Yahya above) enters analysis only after the identity
   specialist and one permitted reviewer other than the proposer agree.
5. **Specialist models.** Recommendation: `claude-opus-5-5` by default, `claude-fable-5-2` for the hard slice and for
   history, never the producing model (`specialist-plan.md`).
6. **Which reviews appear before sign-in.** Recommendation: reviews from merged files only; discussion stays on pull
   requests until accounts exist.
