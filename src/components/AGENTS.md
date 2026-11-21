# Shared interface components

Display rules every public screen follows, and why. Standard: `C:/Users/atooz/.gemini/UI-UX-guidance.md`.

## Arabic

- All Arabic goes through `ArabicText` (`lang="ar"`, `dir`, Amiri). `globals.css` gives `:lang(ar)` and
  `[dir="rtl"]` a line height of 2 and forces `letter-spacing: 0`, `text-align: start`: any letter-spacing
  breaks Arabic letter joining, and justified Arabic stretches words unevenly.
- Narrator names and chapter titles in the corpus often arrive as one "Latin … Arabic" string in the English
  field. `NarratorName` and `BilingualTitle` split it at the first Arabic letter (`splitLatinArabic`) so the
  Arabic run is set in Amiri. Display only: the text is never altered or re-joined.

## Integrity rules (product guide, brief-schema "Goals")

- No computed score or grade is rendered. `chainHealthScore` and the `tracesToProphet` heuristic are still
  passed by `hadith/[id]/page.tsx`, but the client ignores them.
- Grades appear only as attributed, per-tradition assessments (`hadith/[id]/components/Assessments.tsx`), or as
  "Source grade" for a grade recorded on the source row. Tradition badges for Sunni, Imami, Zaydi and Ibadi
  share one neutral style; no tradition borrows a grade colour or acts as the default.
- Narrator verdicts (`reliability_consensus`) are shown only on the narrator page, with the note that their
  tradition and critic are not yet recorded (an open owner question in `conductor/RUNBOOK.md`). They are not
  repeated in lists or on chain rows.
- A chain position with `is_link === false` is an unidentified mention: its surface is plain text, never a link.
- Unknown is written "Unknown"; empty sections are hidden, except where absence itself is the information
  (life dates, generation, "No assessment recorded" for a tradition).

## Hadith detail

One reading column (`max-w-3xl`, about 70 Arabic characters a line): header (reference, chapter), isnad
Page header, then from 1024px an 8-column reading column (text, then isnad as an ordered rail with node and basis
marks) beside a 4-column facts margin (the reference list); wide sections (timeline, tellings, assessments, variants,
parallels) follow across all 12. DESIGN.md §Report reading column. `loading.tsx` mirrors this layout with flat
placeholders so nothing shifts when data arrives.

## Narrator detail

Same rhythm as the hadith page: uppercase section labels, no nested cards, one emerald accent (the design token
`--color-accent`). The tab bar is
hidden (kept for screen readers) when Biography is the only tab. `TabaqahTimeline` is an inline five-step scale
that highlights only a recorded generation.

## Time and place (`timeline/`, `TabaqahTimeline.tsx`)

Server components, no client JavaScript. Swiss style (owner direction 2026-11-21): flat SVG geometry, hairline rules,
type carries hierarchy, one accent; every colour and spacing value on `.root` in `timeline/timeline.module.css` is a
design token, and faint is never used for text. The SVG is `aria-hidden`; every datum is repeated in
the lists below it (the accessible equivalent). Geometry is stretched (`preserveAspectRatio="none"`) with
`non-scaling-stroke` hairlines; all text is HTML.

- Drawn only what the data carries: a bar when both bounds are known (ranges and competing dates lighter), a filled
  square for a death year alone, an outlined square for a birth year alone, text otherwise ("generation only", "Not
  recorded", "Sources name different people"). A generation is never placed on the axis.
- `BasisLabel` prints the basis and leaves an empty `data-source-credit-slot` (registry code `MSD` for lexicon data,
  `SWI` for this archive's rows) as the mount point for `SourceCredit`.
- `ChainFamilyTimelineSection` is the report-page mount (props contract in the file header); `NarratorTimeline` is
  the narrator page's "Life and times". `HistoricalTimeline.tsx` is no longer imported anywhere (kept, never-delete rule).

## Route states

Every `error.tsx` renders `RouteError` and every `not-found.tsx` renders `RouteMessage` (`RouteState.tsx`): a label,
a 20px title, one reason, one primary action (the default `Button`) and one quiet link; errors carry the 2px danger
rule. `primaryActionClass` is kept empty for existing call sites. `RouteError` logs only the digest (an error message can
carry query text) and retries once after two seconds, which covers a database waking from idle.

Design system (tokens, typography, marks, diagrams): read and keep current `DESIGN.md` at the repository root before any UI change.

## Archive surfaces (`archive/`)

New surfaces (browse, report context, sources, banner, footer) follow the Swiss direction (owner, 2026-11-21): strict
column, hairline rules instead of cards, flat fills, typography for hierarchy, one accent, flat geometric SVG marks
(`Marks.tsx`, which re-exports the design-system marks). `archive.css` aliases its variables to the tokens and is
imported by `globals.css` into the components layer, so utilities override it; do not import it from components.

- `ReportTrail` / `ReportFooter` are mounted by `src/app/hadith/[id]/layout.tsx` (the page is another lane's): trail
  and canonical link above; previous/next in source order, source references, "Cite this report" and the dataset
  version below. A Thaqalayn URL is linked as "View at source" only when no other report of the work records the same
  URL: multi-volume works record URLs without the volume (al-Kafi: 14,245 rows, 9,278 distinct URLs).
- `SourceCredit` is the one short source reference (code and name linking to `/sources#<anchor>`, licence, detail).
  Mount it wherever borrowed material appears; `data-source-ref` marks it for tests.
- `SiteChrome.tsx`: `PrivatePreviewBanner` (only under `PRIVATE_PREVIEW=1`), `CrawlPolicy` (robots meta, from
  `dataset_versions`), `SiteFooter` (links `/sources` on every page). All resolve at request time.
