---
type: reference
---

# Human reviews as files

Anyone may propose a review of any claim in the archive by pull request, before the site has sign-in. A review is a
named reviewer's stated view of one claim, with the citations it relies on. It is never the archive's ruling, and it
never hides or overwrites anything: it is shown beside the AI review and beside other reviewers' views.

Validate before opening a pull request:

```
npx tsx reviews/tools/validate-reviews.ts
```

The validator is standalone; the loader does not read these files yet. When it does, every review is credited to
its reviewer like any other source.

## Layout

| Path | One file per |
| --- | --- |
| `reviewers/<handle>.json` | Reviewer (handle = GitHub handle) |
| `endorsements/<id>.json` | Endorsement of one reviewer by another, for one field |
| `entries/<handle>/<review id>.json` | Review |

## Reviewer (`shura-reviewer/1`)

```json
{
  "format": "shura-reviewer/1",
  "handle": "first-reviewer",
  "display_name": "Name as it should appear beside the review",
  "affiliation": "optional",
  "tradition_context": "Ibadi | Imami | Sunni | Zaydi | null",
  "profile_url": "optional",
  "orcid": "optional",
  "permissions": [
    { "capability": "review", "fields": ["identity", "biography"], "granted_by": "owner", "granted_on": "2026-11-21", "basis": "owner" }
  ]
}
```

- `capability`: `review` (post a human review), `discuss` (comment), `propose` (propose new data), `endorse`
  (endorse another reviewer in a field). `fields`: `identity`, `text`, `translation`, `grading`, `biography`,
  `history`, `quran`, or `["all"]`.
- A permission is granted by the owner (`basis: "owner"`, `granted_by: "owner"`) or by an endorsement
  (`basis: "endorsement"`, `granted_by: <endorser>`, `endorsement_id`), which grants only its own field.
- **The grant is the merge.** You may open a pull request adding your own profile, but a permission counts only once
  a maintainer merges it; git history records who merged it and when. Permissions are dated: a review is valid only
  if the reviewer held the permission on its `submitted` date. Retiring a reviewer sets `retired_on` and
  `retired_reason`; nothing is deleted.
- `tradition_context` is what the reviewer declares about their own standpoint. It is shown beside their reviews,
  never used to sort or weigh them.

## Endorsement (`shura-endorsement/1`)

```json
{ "format": "shura-endorsement/1", "id": "en-first-second-identity", "endorser": "first-reviewer",
  "endorsee": "second-reviewer", "field": "identity", "statement": "Why I vouch for this reviewer.", "endorsed_on": "2026-11-22" }
```

The endorser must hold `endorse` for that field on that date, and cannot endorse themselves. This records that one
reviewer vouches for another's competence; it is not an ijaza (which licenses transmission) and the archive does not
call it one.

## Review (`shura-review/1`)

```json
{
  "format": "shura-review/1",
  "id": "rv-2026-11-21-first-reviewer-001",
  "reviewer": "first-reviewer",
  "claim": {
    "kind": "identity",
    "key": "identity|mention:k6:19122:0001:0001|narrator:rawi:20031",
    "content_sha256": "<the hash shown with the claim>"
  },
  "stance": "agrees | qualifies | disagrees | cannot_decide",
  "note": "Why, in a few sentences.",
  "language": "en",
  "tradition_context": "Sunni",
  "citations": [ { "...": "one citation per the standard in docs/review/citations.md" } ],
  "ai_assistance": null,
  "supersedes": null,
  "submitted": "2026-11-21"
}
```

- **Claim keys** name what is asserted, not the machine row that proposed it, so a review survives a change of
  method (`src/lib/review/claim-key.ts` has the grammar per kind). `content_sha256` binds the review to the exact
  texts it was made on; if a text changes, the review is shown as a review of an earlier text and not counted.
- **Stances.** `agrees`; `qualifies` (right in substance with a correction or condition: right person, wrong reason;
  same report, different relation); `disagrees`; `cannot_decide` (examined, and the evidence does not decide). There
  is no "abstain": a review is a view, not a vote.
- **Citations** follow the one archive standard (`docs/review/citations.md`). `agrees`, `qualifies` and `disagrees`
  need at least one; `cannot_decide` needs a note.
- **Changing your mind**: add a new review with `supersedes` pointing at your earlier one. Never edit or delete the
  old file. One live review per reviewer per claim.
- **AI assistance**: if a model helped draft or translate, name it (`{"model": "<model registry id>", "role":
  "drafting | translation | search"}`). The review stays yours and is shown as AI-assisted drafting. It is never
  counted as an AI review, and an AI review is never counted as a human one.

Not in this format yet: discussion threads and data proposals. Until sign-in exists, discuss on the pull request.
