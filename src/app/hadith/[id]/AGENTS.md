# src/app/hadith/[id] — the report page and its family view

Standard: `C:/Users/atooz/.gemini/UI-UX-guidance.md`. Shared display rules: `src/components/AGENTS.md`. Data:
`src/db/queries/AGENTS.md` §Report families. The layout (`layout.tsx`) belongs to the browsing lane; do not edit it.

## Routes

| Route | What |
| --- | --- |
| `/hadith/[id]` | The report. A "Tellings of this report" section (summary line, tellings list) links to the full view |
| `/hadith/[id]/chains` | The full family view: summary, the report, its tellings, the combined diagram, every chain as lists |
| `/admin/correspondences/family/[id]` | Curator preview of the same view over unpublished reports (`getReportFamilyForReview`), with a review link per pair |

All three render `components/family/FamilyView.tsx` or its parts, so public and curator see one design. Public pages
work with zero curation rows: machine candidates above the display threshold show as "machine-found, unreviewed".

## Matn

`matn.ts` `ownMatn`: a stored matn is shown only when its Arabic letters occur inside the report's own text and it is
not a leading slice of a longer text (where the chain sits). Otherwise the page shows the full text as in the source
and does not also print the written sanad, so the chain appears once. The projection applies the stricter rule from
`diagnostics/report-correspondence/matn_isolation.py` before load (1,597 K6 rows carried another report's matn, 12,617
carried the chain); this guard is the second line.

## OpenITI chain span, continuation and source notes

For al-Rabi, Musnad Zayd and Sahifat al-Rida (`src/db/AGENTS.md` §OpenITI extraction fields):

- **Confident split** (`split_confidence = 'high'`, `sanad_ar` set): the matn alone under "Matn · report text"; the Arabic
  chain span as written leads the isnad section and replaces the stored `sanad` line (which would show the chain twice).
- **Low confidence**: `matn_ar` is NULL, so the page shows the whole text once under "Text as in the source", no span.
- **Continuation** ("and by this chain"): a link "Chain continues from No. N" (`chain_continues_from`, the closest earlier
  report the parser named) opens the isnad section, with or without a span. A split part reads "No. 4, part 2" (`reportPart`).
- **Source notes** (`components/SourceNotes.tsx`): its own section "Notes in the source edition" below the isnad, each note
  labelled by author (compiler's remark, arranger's note, editor's footnote), credited once to OITI with `SourceCredit`.
  Never inside the text. Flow tests: `src/db/queries/__tests__/openiti-extraction-flows.test.ts`.

## Report family

- **Wording.** Neutral across traditions; nothing calls one telling the original or more authentic. A correspondence is
  "Same wording", "Variant wording" or "Shares a passage", then "machine-found, unreviewed", "machine-found; a reviewer
  was unsure" or "confirmed by a reviewer", then a plain measure ("62% shared wording", "78% of the shorter text").
- **Order.** The report first; then tellings grouped by tradition (alphabetical: Ibadi, Imami, Sunni, Zaydi — no
  default), then by work; each row names the report within its work (see References below).
- **All chains** reuse `components/IsnadChain.tsx` (not forked) with a `chainLabel` so each list has a unique accessible
  name. They are the diagram's accessible equivalent; the diagram canvas is `aria-hidden` and says so in its caption,
  with a link to the lists.
- **Identity tiers (owner 2026-11-21).** `IsnadChain` leads a standing identity with what made it machine-reviewed
  (`STANDING_BASIS_LABEL`: the source's index and the text, two sources agree, hadith-kg, the annotation via Riwayat, the
  Imam's kunya); "verified by a reviewer" is reserved for a reviewer's decision. Candidates group by person key
  (`src/db/queries/identity-groups.ts`): records linked to one another show as one person ("Same person in hadith-kg"),
  "Sources differ" only when one registry's records are known to name different people. Kunya-only matches and an
  undecided shared Imam kunya are notes, never a disagreement. Riwayat's automatic link is labelled "not counted".
- **Latin names.** Each row shows `name_latin` beside the Arabic with its basis and source code (DESIGN.md §Latin names).
- **English.** The report text, the family view's report and every telling show their public English through
  `components/archive/ReportEnglish.tsx`; `correspondence.ts` reads each telling's English from `public_translations`.
- **Merge rule.** The combined diagram merges a standing identity only within one tradition (`mergeKey(node, tradition)`).

### Chain timeline

The history lane's `ChainFamilyTimelineSection` (server component) is passed in as a `timeline` slot: after the isnad on
`/hadith/[id]`, after the diagram on `/chains`, with the family's other tellings as `relatedHadithIds` (it reads 12 at
most) and the request visibility. It renders nothing on a failed read.

### Combined diagram (`TransmissionDiagram.tsx`, graph from `src/db/queries/family-graph.ts`)

- Originator at the top, works at the bottom (one node per work, with its number of tellings). Merge only on a standing identity
  (`chain_mentions.narrator_id`, machine-reviewed or reviewer-verified); every other name is one node per mention even
  when the text is identical, so nothing merges on name text or across traditions without an identity.
- Readability at size: a deterministic Sugiyama-style layout (longest-path layers, barycentre ordering, key
  tie-breaks). "Shared narrators only" (on by default above 12 chains) keeps just the identities several chains pass
  through, counts the names left out on each line (+N) and says how many chains share no narrator; a browser check of a
  61-telling family showed one-node-per-chain views shrink to specks, which is why. Highlight one tradition, one chain
  (select) or every chain through a clicked node; zoom and Fit buttons sit outside the canvas; the opening view stops
  at a readable zoom (0.55), Fit shows everything; the canvas height follows the number of layers; parallel edges of
  one tradition are drawn once and thicken when shared.
- Design system (DESIGN.md §Transmission graph): faint 1px edges in the tradition's `TRADITION_DASH` pattern (from
  `src/components/marks/`), legible in black and white; node shapes from `NarratorNodeShape`: filled square =
  identified narrator, framed square = several chains pass through, outline square = name as written, ink rule =
  work. A highlight draws the chosen chains in 2px accent and puts nodes on an accent-wash square; nothing fades.
- Every value on `.family` in `components/family/family.module.css` is a design token.

### Source credit (owner's top priority)

`components/family/SourceCredits.tsx` wraps the shared `SourceCredit` (`src/components/archive/SourceCredit.tsx`,
registry `src/lib/sources/registry.ts`): `TextCredit` beside every telling, the report's own text and each chain
("Chain as written"), from `sourceCodeForHadithId`; `IdentityCredit` under every identity claim in `IsnadChain`, one
per distinct source among its bases (`sourceForIdentityBasis`: K6I for the source index, MSD for name and kunya
matches, HKG and RWY for the external datasets, plus THQ or HKG when Riwayat's id comes from their annotation
(`sourcesForIdentityClaim`), SWI for a reviewer or the Imam register); `ChainSourceCredits` lists each source of a
chain's identities and Latin names once; `GradingCredit` under each tradition's grades in `Assessments`. `SourceCredit` renders a
block `<p>`: place it beside a paragraph, never inside one. `switches-http.test.ts` asserts a Text credit on the
report and chains routes.

### References and visibility

- References go through `src/lib/citation/reference.ts` (`reportNumber`, `reportReference`): Thaqalayn's stored
  `hadith_no` is the chapter number, its own number is the last segment of the provider URL. Works in
  `UNCITABLE_NUMBERING_WORKS` (Musnad Ahmad, Musnad al-Shafi'i) show the stable record id instead.
- Links use `hadithPath` (`src/lib/hadith-address.ts`): `/hadith/k6/10008`, `/hadith/k6/10008/chains`.
- `data.ts` reads under `requestVisibility()`; `getChainGraph`, `getVisibleReportFamily` take that visibility and
  resolve relations through `hadithRelationsFor` / `chainRelationsFor`. Curator visibility is never constructed here.
