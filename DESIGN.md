---
type: design-system
updated: 2026-11-21
---

# Shura wa Istehsan design system

The single design reference for this app. Every change to the interface reads this file first and keeps it current
(see [Maintaining this file](#maintaining-this-file)).

- Tokens: [`src/app/design-tokens.css`](src/app/design-tokens.css)
- Geometric marks: [`src/components/marks/`](src/components/marks/)
- Static specimen: [`docs/design/preview.html`](docs/design/preview.html) (open it in a browser)
- Evidence from the two reference sites: [`docs/design/reference-study.md`](docs/design/reference-study.md)

## Standards this builds on

The owner's shared UI/UX guidance, [`C:/Users/atooz/.gemini/UI-UX-guidance.md`](file:///C:/Users/atooz/.gemini/UI-UX-guidance.md),
is the standing standard for every screen. It governs wherever this file is silent. This file adds only what is
specific to this product: the Swiss direction and the references behind it, the tokens, Arabic typography, the
tradition and basis marks, the two diagrams and source references. Where the two seem to conflict, raise it with the
owner rather than choosing.

The archive's own integrity rules (no computed grades, unidentified names never linked, every borrowed item credited)
live in [`src/components/AGENTS.md`](src/components/AGENTS.md) and `conductor/RUNBOOK.md`. Design serves them and
never overrides them.

## Principles

1. **Swiss, applied to evidence.** Strict grid, flush-left, type-led hierarchy, near-black on off-white with one
   accent, flat fills and hairline rules. No gradients, shadows, glows, rounded cards or decorative imagery.
2. **Geometry carries information, not atmosphere.** Every shape means something: a tradition, an identity basis, a
   narrator node. Nothing is drawn for mood. Taawun's lattice is the counter-example we studied and did not take.
3. **Arabic is the primary voice.** The report text is set larger than the English around it, never letter-spaced or
   justified, and always in its source spelling.
4. **Show the evidence.** Where the data is uncertain, the design shows that in form: outline instead of fill,
   dashed instead of solid, "Not identified" in place of a guess. It never hides it.
5. **Dense, not crowded.** A scholarly tool: 14px metadata, tables, compact lists, with a 4px rhythm and generous
   section breaks rather than generous padding everywhere.
6. **No tradition is the default.** The four traditions share one style. Order is alphabetical (Ibadi, Imami, Sunni,
   Zaydi) wherever no other order is meaningful.

## References

The owner gave two of their own sites as references: Neos (`https://neos.primusneo.com/`) and Taawun
(`https://taawun-production.up.railway.app/`). The measured facts are in
[`docs/design/reference-study.md`](docs/design/reference-study.md). In short:

- **Taken from Neos:** warm paper and ink, one accent used only for links, primary action and focus, Inter plus a mono
  for codes, a 72rem grid with a 42rem prose measure, flat surfaces with all shadows off, a 2px offset focus ring,
  44px touch targets, 150ms state transitions, uppercase tracked labels, and light and dark following the system.
- **Taken from Taawun:** hairline rules as the main divider, square corners, mono uppercase kickers for codes, the
  explicit reduced-motion stance, and the respectful handling of Arabic: a quotation set at about twice the Latin
  size with a line height of 2.
- **Kept from this product:** emerald as the single accent (already the app's accent, and not owned by any
  tradition), Amiri for Arabic, and the archive's rules on credit and uncertainty.

### What the references do that we deliberately do not copy

Both are marketing sites for small communities. This is a dense scholarly tool, so:

- No display type above 48px. Neos sets 115px uppercase on `/about` and Taawun sets 94px serif headlines. Page titles
  here are 32px: the reader came for the report, not the heading.
- No hero sections, full-bleed dark panels, taglines or explanatory paragraphs above the content.
- No serif display face. Taawun's Iowan/Fraunces headlines would give the Latin interface a second voice that
  competes with the Arabic.
- No decorative Islamic geometry, glow, vignette, gradient, translucent glass or canvas animation (all Taawun), and no
  "Motion" toggle, because there is no decorative motion to switch off.
- No 2px ink frames around cards (Neos). Content sits in sections divided by rules, not in boxes.
- No 900 weight. 800 is the heaviest, and only for the page title and wordmark.
- No cobalt (Neos) and no gold (Taawun). One accent only, the product's own.

## Tokens

All tokens are CSS custom properties in [`src/app/design-tokens.css`](src/app/design-tokens.css), named by role. The
file's header maps every existing variable in `globals.css`, `archive.css` and `timeline.module.css` to its
replacement.

**Themes.** Each colour token is one `light-dark(light, dark)` declaration, so the two values sit side by side and
cannot drift apart. `:root { color-scheme: light dark }` follows the operating system; `.light` or `.dark` on
`<html>` forces one theme. No JavaScript is needed to follow the system.

### Colour

Contrast is WCAG 2.x against `--color-paper` unless another background is named. The calculation script output is
recorded in the 2026-11-21 change-log entry.

| Token | Light | Dark | Role | Contrast (light / dark) |
| --- | --- | --- | --- | --- |
| `--color-paper` | `#F4F1EA` | `#0F0F0D` | page background | (ground) |
| `--color-surface` | `#FBFAF7` | `#171714` | inputs, popovers, the selected tab; never a card | (ground) |
| `--color-sunken` | `#EAE6DC` | `#1E1E1A` | row hover, code wells, timeline bands, loading placeholders | (ground) |
| `--color-band-alternate` | `#E1DCCF` | `#262622` | second era band in the timeline | (ground) |
| `--color-ink` | `#17150F` | `#F1EEE6` | text, headings, strong rules, diagram ink | 16.18 / 16.55 |
| `--color-ink-muted` | `#57524A` | `#ACA79C` | secondary text, labels, metadata | 6.87 / 8.01 (6.22 / 6.98 on sunken) |
| `--color-ink-faint` | `#76716A` | `#8C877E` | **non-text only**: ticks, dimmed edges, uncertain spans | 4.29 / 5.37 (3:1 required) |
| `--color-rule` | `#D3CDC1` | `#36342F` | hairlines between rows; decorative, never the only cue | 1.40 / 1.54 |
| `--color-rule-strong` | = ink | = ink | the rule that opens a section; table head rule | (as ink) |
| `--color-control` | `#77716A` | `#8C877E` | input, select and checkbox borders | 4.28 / 5.37 (3:1 required) |
| `--color-accent` | `#0B6A4E` | `#5DC09A` | prose links, the primary button, focus, the selected chain | 5.84 / 8.65; 6.32 / 8.10 on surface |
| `--color-accent-wash` | `#DDEBE3` | `#16302A` | selected row or node ground | ink on it 14.83 / 12.15; accent on it 5.36 / 6.36 |
| `--color-on-accent` | `#FBFAF7` | `#0F0F0D` | label on a filled accent button | 6.32 / 8.65 on accent |
| `--color-focus` | = accent | = accent | focus outline | 5.84 / 8.65 (3:1 required) |
| `--color-danger` | `#A32A1D` | `#FF8B7B` | error text and error rule only | 6.41 / 8.43 |
| `--color-notice` / `--color-on-notice` | ink / paper | ink / paper | preview notice band (inverted) | 16.18 / 16.55 |

Rules for colour:

- One accent. It marks *where you can act or where you are* (link, primary button, focus, selection). It never marks
  a tradition, a grade, a basis or success.
- Red (`--color-danger`) appears only for errors, so a red mark always means something failed.
- No colour carries meaning alone. Tradition, basis and selection are always shape plus words, and every mark
  survives black-and-white printing.

### Typography

| Token pair | Size / line | Weight, tracking | Use |
| --- | --- | --- | --- |
| `--text-display` | 48 / 52 | 800, -0.035em | home page only |
| `--text-heading-1` | 32 / 40 | 800, -0.02em | page title (one per page) |
| `--text-heading-2` | 24 / 32 | 700, -0.02em | rare: a section that needs more than a label |
| `--text-heading-3` | 20 / 28 | 600, -0.01em | subsection ("Chain 1 of 2"), empty-state titles |
| `--text-reading` | 18 / 28 | 400 | English translation and prose |
| `--text-body` | 16 / 24 | 400 | interface text, form values |
| `--text-small` | 14 / 20 | 400 | metadata, table cells, source references, basis labels |
| `--text-label` | 12 / 16 | 600, +0.08em, UPPERCASE | section labels, table heads |
| mono label | 12 / 16 | 500, +0.02em | source codes (`SUN`, `K6I`), addresses, digests |
| `--text-arabic-display` | 28 / 56 | 400 | a report quoted as the subject of a page |
| `--text-arabic-reading` | 22 / 44 | 400 | the report text and written isnad |
| `--text-arabic-inline` | 18 / 32 | 400 | narrator names in lists, beside 14–16px Latin |

Every line height is a multiple of 4px.

**Faces.** Inter (variable, optical size on) for all Latin. JetBrains Mono for codes. Both are used by Neos, are
under the SIL Open Font License, and load through `next/font/google`. Amiri for all Arabic (unchanged, OFL), with
Noto Naskh Arabic as fallback. Inter replaces Geist: both references use Inter, and its optical sizes hold up at 12px.

### Arabic beside Latin

- **Face.** Amiri, a classical naskh that sets full harakat cleanly. It is used for every Arabic run, including
  single names inside English sentences (`ArabicText`, `NarratorName`, `BilingualTitle` already split mixed strings).
- **Size.** About 1.25 times the Latin it sits beside, because Arabic letterforms are smaller at the same font size:
  22px reading text in a 16px interface, 18px names beside 14–16px Latin, 28px for a quoted report.
- **Line height.** 2 (22/44, 18/32 rounds to the grid, 28/56). Harakat above and below need the room.
- **Alignment.** `text-align: start` with `dir="rtl"`, so Arabic blocks align right and Latin blocks align left
  inside the same flush-left column. Never `justify`: kashida-less justification stretches the gaps between words
  unevenly.
- **Never letter-spaced** (it breaks the joining of letters), never uppercase-transformed, never italicised or
  synthetically bolded. Bold Arabic is rare: Amiri 700 only for a heading in Arabic.
- **Mixed direction.** An Arabic block gets `lang="ar" dir="rtl"`. An Arabic name or title inside a Latin line is
  wrapped in `<bdi lang="ar" dir="rtl">` so that commas, numbers and brackets do not reorder. A Latin code inside
  Arabic is also wrapped in `<bdi>`. Inputs that may receive either script use `dir="auto"`.
- **Source text is never altered.** No normalisation of hamza, ta marbuta, harakat or digits on display. The
  "As written" label states this.
- **Numerals.** Interface numbers (report numbers, counts, years) use Western digits with `tabular-nums`. Digits
  inside source text stay in whatever script the source uses.
- **Isnad and matn.** When the data splits them, the written isnad is set in `--color-ink-muted` and the matn in
  `--color-ink`, at the same size, as one paragraph. When it does not, the whole text is set in ink.

### Spacing, grid and layout

- **Spacing scale (4px base):** `--space-1` 4, `-2` 8, `-3` 12, `-4` 16, `-5` 24, `-6` 32, `-7` 48, `-8` 64, `-9` 96.
  Inside a component use 4–16; between components 24–32; between page sections 48; between bands 96.
- **Grid:** `--grid-max` 72rem (1152px), 12 columns, 24px gutter, page margin `clamp(16px, 4vw, 32px)`.
- **Breakpoints:** below 40rem (640px) everything stacks; from 40rem two-part rows sit side by side (an isnad name
  beside its identity); from 64rem (1024px) the 12-column grid applies.
- **Report layout (from 64rem):** a flush-left main column of 8 columns, capped at `--measure-reading` (42rem,
  about 70 Arabic characters a line at 22px), and a facts margin in columns 9–12. Wide sections (tellings table,
  transmission graph, timeline) span all 12. The layout is asymmetric and never centred.

### Rules, radii, focus, motion

- `--rule-hairline` (1px, `--color-rule`) divides rows. A 1px `--color-rule-strong` rule opens each section above its
  label. A 2px ink rule closes the page header. Nothing else draws a line.
- `--radius-none` everywhere, including inputs and buttons (`--radius-control` is 0). Circles appear only in basis
  marks.
- Focus: `--focus-width` 2px outline in `--color-focus`, `--focus-offset` 2px (0 on text inputs, whose border takes
  the focus colour), visible on every interactive element, never removed.
- Motion: `--motion-fast` 120ms and `--motion-base` 180ms with `--motion-ease`, for colour, border and underline
  changes only. No entrance animation, no slide, no parallax. Both durations become 0 under
  `prefers-reduced-motion: reduce`.

## Components

Each rule names the existing file it applies to. "Shown in" points to `docs/design/preview.html`.

### Site header and navigation (`SiteHeader.tsx`)

A single row on paper: the wordmark (15px, 800), then the five primary links (14px, 500, muted), wrapping to a second
row under 640px. No menu button is needed for five links. The current page is ink with a 2px ink underline set 8px
below the text (`aria-current="page"`). A 1px ink rule closes the header. No background fill, no sticky blur.
*Proposed, needs owner approval:* a 16px wordmark mark made of the four tradition modules in one 2x2 square,
representing consultation across four traditions with none first.

### Page header

A breadcrumb trail (14px, muted, `/` separators in faint), then the title (32/40, 800), then one metadata line
(14px): tradition mark and name, chapter, Arabic chapter title in `<bdi>`. A 2px ink rule closes it. No description
paragraph.

### Report reading column (`hadith/[id]/client-page.tsx`)

In order: `TEXT` label, Arabic text (22/44), the English (18/28) labelled as an unreviewed translation or the line
"No English translation recorded for this report.", then the source short reference. Then the isnad, assessments,
variants and references, each opened by a 1px ink rule and a 12px uppercase label. The facts margin holds a definition
list (tradition, work, number, book, attribution, tellings, address in mono) and the one secondary action
("Copy citation"). Under 1024px the facts follow the text.

### Isnad list (`hadith/[id]/components/IsnadChain.tsx`)

- Order is **as written**: the name nearest the compiler first, labelled "As written, nearest the compiler first".
  (The graph runs the other way, from the attribution down; each says which way it runs.)
- Each chain has a heading ("Chain 2 of 2", 20px) and a count ("5 names, 5 identified").
- Each position is a three-part row: the position number (12px muted), a rail (12px column with a 1px faint vertical
  line and the position's node mark), and the body. In the body, the Arabic surface is at 18/32. The identity (14px)
  sits beside it from 640px and below it on smaller screens: the narrator name as a row link, the record's Arabic name
  in `<bdi>`, then one basis line per candidate.
- An unidentified mention shows an outline node and "Not identified" in muted text. It is never a link.
- A narrator through whom several chains of this report pass shows the shared node and "in N chains of this report".
- Where sources disagree, every candidate is listed with its own basis line, under "Sources differ. Both identities
  are shown; neither is preferred." Kunya-only candidates are a note, never a disagreement.
- Rows are divided by hairlines; no boxes. *Shown in:* `#isnad`.

### Identity basis labels (`BasisMark`, basis wording)

The basis line is the basis mark (10px), the wording, and the source code of the dataset behind it (`K6I` for
source-index bases, `MSD` for name bases, `SWI` for reviewer decisions). The marks form a scale that fills as the basis
firms up:

| Basis | Mark | Wording |
| --- | --- | --- |
| `reviewer_decision` | filled disc | verified by a reviewer |
| `source_index_confirmed_by_text` | ring with a centre dot | machine-reviewed: matches the source's index and the text |
| `source_index` | ring | source index |
| `name_exact`, `name_spelling_fold` | dashed ring | matched by name |
| `name_kunya_only` | short bar (off the scale) | matched by kunya only |

Kunya-only is a bar rather than a circle because, by owner decision, it is a label and not a rung on the scale.
Timeline datum bases (`basisLabel`) stay text-only.

### Tradition marks (`TraditionMark`, replaces `TraditionBadge` styling)

One framed 12-unit square module, divided four ways, in alphabetical order:

| Tradition | Division | Line pattern (`TRADITION_DASH`) |
| --- | --- | --- |
| Ibadi | lower half filled | long dash `6 2` |
| Imami | left half filled | dot `1.5 2` |
| Sunni | lower-left diagonal half filled | dash-dot `6 2 1.5 2` |
| Zaydi | centre square filled | even dash `3 3` |

- The four marks carry roughly equal ink, so none dominates. None is a plain circle, square or dot, the shapes a
  reader would take for a default bullet.
- The assignment is arbitrary and alphabetical. It carries no claim about any tradition. Do not reassign it.
- A mark always precedes the tradition name in running UI. Only diagram legends introduce the mark once and then use
  it alone.
- Line patterns are only for plots where several traditions share one axis (timeline lanes). Inside the transmission
  graph, traditions are separate groups, so edges stay solid.
- Marks are fixed glyphs: they are not mirrored in RTL.
- Other traditions on the comparative page (`TraditionBadge`'s world-religion entries) are text-only in muted ink,
  with no mark and no colour.

### Badges (`badges.tsx`, `ConsensusBadge.tsx`, `ui/badge.tsx`)

There are no pill or filled badges. A status is a 12px uppercase label in muted ink, optionally preceded by its mark.
Labels that read as warnings ("machine translation, not reviewed") are plain muted text. Badge colours are removed.

### Tables (`TellingsList.tsx`, `ReportList.tsx`, collections)

Header cells are 12px uppercase muted with a 1px ink rule under the header row. Body rows are 14/20 with hairlines.
Numbers align right with tabular digits. The current row has the accent-wash ground and a 2px accent bar at its start.
Below 640px a table stacks into rows of label and value (labels from `data-label`); it never scrolls sideways.
A caption states only what the reader needs in order to read it correctly ("Linked by wording · machine candidates,
not reviewed").

### Filters and forms (`SearchFilterBar.tsx`, `ui/input.tsx`, `ui/label.tsx`)

The label sits above the control (14px, 600). Inputs and selects are 40px tall (44px on coarse pointers), with a 1px
`--color-control` border on surface and a square corner. The search icon sits inside the field at the start. Tradition
filters are checkboxes inside bordered chips: native checkbox with `accent-color`, then the mark and the name. A
checked chip has a doubled ink border. An error turns the border and a 2px inner bottom rule red, with the message
below in danger text, linked by `aria-describedby`. Actions: one primary (accent fill), then a quiet text button
("Clear"). A disabled control shows faint text and a rule-coloured border.

### Buttons and links (`ui/button.tsx`)

- **Primary:** accent fill, on-accent label, 14px 600, 40px tall. One per view. Hover inverts to ink.
- **Secondary:** transparent with a 1px ink border. Hover fills with ink.
- **Quiet:** text with a hairline underline.
- **Prose link:** accent and underlined.
- **Row link** (names, works, navigation lists): ink with a rule-coloured underline that turns accent on hover.
- **Glossary term:** dotted muted underline linking to `/glossary#slug`.

### Empty, loading and error states (`EmptyState.tsx`, `RouteState.tsx`, `loading.tsx` files)

- **Empty:** a label, a 20px title saying what is absent, one sentence on why, and one action that changes the
  outcome.
- **Loading:** flat sunken bars in the shape of the content they stand for (Arabic bars 20px tall, Latin 12px), with
  `aria-busy` and a visually hidden "Loading report". No shimmer or pulse.
- **Error:** a 2px danger rule on top, the label in danger, a title, a reason, the digest in mono, then "Try again"
  (primary) and a way back (quiet). `role="alert"`.

### Preview notice (`PreviewNoticeBar.tsx`)

A full-width inverted band (ink ground, paper text, 14/20) directly under the site header, with the word "PREVIEW"
as a 12px label, the existing sentence and an underlined link. It replaces the amber band, so no warning colour
outside errors. Temporary: removed with the rest of the preview machinery after the first release.

### Source short references (`archive/SourceCredit.tsx`)

`Role: CODE Name · Licence`: role in ink, code in mono, name as a muted row link to `/sources#code`, licence muted.
One line, 14px, directly under the material it credits. Never collapsed into a footer, never shown as an icon only. The
`/sources` page lists each source as a hairline row of code, name and licence.

### Glossary (`GlossaryTerm.tsx`, `/glossary`)

Inline, a term is a dotted underline, not a tooltip-only affordance. On the page, each entry is a definition: the
term (20px, 600), the Arabic in `<span lang="ar">` at 18/32, the English gloss and aliases muted, the one-sentence
definition at body size, and "In this archive:" in small muted text. Entries are separated by hairlines, and the
filter field above them follows the form rules.

### Icons (`marks/Icons.tsx`)

16-unit grid, 1.5 stroke, square caps, mitred joins, no fills: search, arrow (four directions), external, copy,
check, close, chevron, menu. An icon accompanies a word; an icon-only button carries an accessible name. Lucide (Neos)
is not used: its round caps and 2px weight read softer than the square system.

## Diagrams

Both diagrams are decorative SVG over data that is also present as text (list or table). The SVG is `aria-hidden`
or has a summary `<title>`, so assistive technology reads the list, not the drawing.

### Transmission graph (`family/TransmissionDiagram.tsx`)

- **Direction.** Top to bottom: an ink rule at the top labelled with the attribution ("ATTRIBUTED TO THE PROPHET ·
  MARFUʿ", from `attributed_to` and `narration_level`), narrators in rows by distance from it, and an ink rule at the
  bottom with each chain's work and number as a 11px label (the current report in ink, the others muted).
- **Groups.** One group per tradition, separated by a vertical hairline and labelled at the foot with its mark and
  name. Narrators are merged only within a tradition and only by identity. Unidentified mentions are never merged.
  Nothing is merged across traditions.
- **Nodes** (`NarratorNodeShape`): identified = filled 8px square; not identified = 7px outline square on paper;
  shared by several chains = filled square inside a 13px frame; sources differ = two 3px bars.
- **Edges.** 1px straight lines in `--color-ink-faint`. Where a chain stops before the attribution with no named link
  (for example "أنه بلغه"), a dashed `2 3` line runs from the last named narrator to the top rule.
- **Labels.** Arabic, 15px Amiri, ending at the node (`text-anchor="end"`, 12px gap) so the name reads from the node
  outwards. The text is the most frequent written surface for that node, as written. Labels over 20 characters are cut
  at a word boundary with "…", and the full name goes in an SVG `<title>`.
- **Emphasis and selection.** Selecting a node draws its chain in 2px accent from the works rule to the attribution
  and places the node on an 18px accent-wash square with a 2px accent frame. Other edges stay faint. No shadow, glow,
  blur, opacity fade or scaling. The selection's details (both identities when sources differ) appear below the graph
  in a panel with a 2px accent start rule, with `aria-live="polite"`.
- **Small screens.** The graph keeps a minimum width of 46rem and scrolls sideways inside a focusable, labelled
  region; the page itself never scrolls sideways. A one-line hint says so, and the same chains are in the table above.
- **Omissions** are stated under the graph ("Not drawn here: …").

### Chain timeline (`timeline/*`)

Keeps the existing geometry (`TimelineGeometry.tsx`) and its legend, recoloured to tokens: a Hijri axis with faint
ticks every 50 years and 12px muted labels; era bands in sunken and band-alternate; a life as a 3-unit ink bar,
competing or ranged spans in faint, death-only as a filled square, birth-only as an outline square; events as 1px
ink ticks. The lane label is the narrator name with Arabic in `<bdi>`, the years and the basis in small muted text, and
the dataset code. A narrator with no dates shows "No dates recorded" in the lane: the absence is the information.
Where lanes from several traditions share the axis, the lane's line uses `TRADITION_DASH`.

## Marks inventory (`src/components/marks/`)

| Export | What it draws |
| --- | --- |
| `TraditionMark`, `TraditionLine`, `TRADITION_DASH`, `HADITH_TRADITIONS` | tradition modules and line samples |
| `BasisMark`, `IDENTITY_BASIS_LABEL` | identity basis scale |
| `NarratorNode`, `NarratorNodeShape`, `NARRATOR_NODE_LABEL` | graph nodes, standalone or inside a larger SVG |
| `ChainConnector` | vertical rail segment: continuous, gap, tradition dash, 2px emphasis |
| `ArrowIcon`, `SearchIcon`, `ExternalIcon`, `CopyIcon`, `CheckIcon`, `CloseIcon`, `ChevronIcon`, `MenuIcon` | interface icons |
| `MarkSvg` | shared frame: `currentColor`, `<title>` by default, `decorative` hides it |

All are server-safe (no client hooks other than `useId`), flat, single-colour through `currentColor`, and not yet used
by any page.

## Accessibility

- **Contrast:** every text pair at least 4.5:1 and every control boundary and focus ring at least 3:1, in both themes
  (table above). `--color-ink-faint` and `--color-rule` are never used for text.
- **Never colour alone:** tradition, basis, node kind and selection each combine shape and words. Links are
  underlined.
- **Focus:** visible 2px accent outline on every interactive element; skip link first in the page; diagram regions
  that scroll are focusable and labelled.
- **Targets:** at least 40px tall, 44px on coarse pointers.
- **Language and direction:** `lang`/`dir` on every Arabic run; `<bdi>` for embedded runs; `dir="auto"` on free-text
  inputs.
- **Structure:** one `h1`; sections labelled by their heading; tables with header cells and a caption; lists as
  `ol`/`ul`; `role="alert"` for errors, `aria-busy` for loading, `aria-live="polite"` for diagram selection details.
- **Reduced motion:** motion tokens drop to 0; nothing depends on animation.
- **Zoom and reflow:** usable at 320px wide and at 200% zoom without sideways page scroll.

## Applying the system: first pass

*Removable: delete this section once every step is done and recorded in the change log.*

Order matters: tokens first, so every later step only swaps class names. Each step lists what changes visibly.

1. **`src/app/globals.css`.** Add `@import "./design-tokens.css";` after the Tailwind imports. Replace the shadcn
   `:root` and `.dark` blocks with aliases (`--background: var(--color-paper)` and so on, per the mapping in the token
   file header) so `ui/*` keeps working. In `@theme inline`, point `--font-sans`, `--font-mono` and `--font-arabic` at
   the new families, set every `--radius-*` to `0`, and drop `--color-chart-*` and `--color-sidebar-*`. Change the dark
   variant to `@custom-variant dark (&:where(.dark, .dark *))`. Remove `.animate-fade-in` and `.animate-slide-up`.
   Point the Arabic base rule at `--leading-arabic-reading`. *Visible:* warm paper and ink, square corners, emerald
   focus.
2. **`src/app/layout.tsx`.** Replace `Geist`/`Geist_Mono` with `Inter` (axes `opsz`) and `JetBrains_Mono` from
   `next/font/google`, keep `Amiri`. Remove `className="dark"` from `<html>` so the system preference applies (**owner
   decision**: today the site is forced dark; keeping `.dark` is a one-word revert). *Visible:* Inter text; light theme
   for light-mode readers.
3. **Shared primitives.** `src/components/ui/button.tsx`, `badge.tsx`, `input.tsx`, `label.tsx`, `tabs.tsx`,
   `textarea.tsx`, `card.tsx`: radius 0, the button variants above, the input rules above. `card.tsx` loses its
   border and background. `src/components/archive/Marks.tsx` re-exports `ArrowIcon` and `NarratorNode` from
   `marks/`. *Visible:* flat controls.
4. **Local token sets.** `src/components/archive/archive.css` and `src/components/timeline/timeline.module.css`:
   replace each local value with its token (`--archive-accent: var(--color-accent)`, and so on), then delete the
   aliases once no class uses them. *Visible:* the red archive accent becomes emerald; the timeline takes both themes.
5. **Chrome.** `SiteHeader.tsx` (nav rules above, current-page underline), `archive/SiteChrome.tsx` footer (hairline,
   small muted), `PreviewNoticeBar.tsx` (inverted ink band). *Visible:* new header and notice on every page.
6. **Arabic and names.** `ArabicText.tsx`, `NarratorName.tsx`, `BilingualTitle`: size classes for the three Arabic
   roles; `<bdi>` for inline runs.
7. **Tradition and basis.** `TraditionBadge.tsx` renders `TraditionMark` and the name for the four traditions and
   muted text for the rest. `IsnadChain.tsx` uses `BasisMark` and imports `IDENTITY_BASIS_LABEL` (delete its local
   `BASIS_LABEL`). `badges.tsx` and `ConsensusBadge.tsx` become labels.
8. **Report page.** `hadith/[id]/client-page.tsx` and `loading.tsx`: 12-column layout with the facts margin, sections
   per the reading-column rules, `loading.tsx` mirroring it. `components/family/*`: tellings table rules,
   `TransmissionDiagram.tsx` per the graph rules (node shapes from `NarratorNodeShape`, selection, scroll region).
   `Assessments.tsx`, `GradingPanel.tsx`: labels and hairlines.
9. **Other routes**, one at a time: `narrator/[id]`, `collections/**`, `hadith` (list), `comparative`, `sources`,
   `glossary`, then `sign-in` and `admin/**` (same tokens, lowest priority).
10. **States.** `RouteState.tsx`, `EmptyState.tsx`, every `error.tsx`/`not-found.tsx`/`loading.tsx` per the state
    rules.
11. **Docs.** Update `src/components/AGENTS.md` ("one emerald accent" stays true; replace slate/amber references) and
    this file's change log.

**Checks, once, at the end** (per the repository's single-sweep rule): `npx tsc --noEmit`; `npx next build`; lint;
`rg "rounded-|shadow-|emerald-|slate-|amber-|bg-gradient" src` returns nothing outside `admin/` (or each remaining hit
is justified); screenshots of `/`, a report, a narrator, `/collections`, `/sources` and `/glossary` at 390 and
1440 in light and dark, with `scrollWidth === clientWidth` at both; keyboard pass (skip link, visible focus on every
control, graph region reachable); `prefers-reduced-motion` emulated; contrast re-run if any colour token changed.

## Maintaining this file

- **Who reads it:** every agent or person changing the interface, before starting. `src/components/AGENTS.md` points
  here.
- **When it must change:** with any new or changed token, component rule, mark, diagram convention, breakpoint or
  accessibility rule, in the same change as the code. If code and this file disagree, the code is wrong until this file
  is changed.
- **How:** keep `src/app/design-tokens.css`, `src/components/marks/` and `docs/design/preview.html` in step with the
  text; recompute contrast for any colour change and update the table; add a dated line to the change log below.
- **What does not belong here:** general UX practice (it lives in the shared guidance linked at the top), data rules
  (`src/db/AGENTS.md`), and integrity rules (`src/components/AGENTS.md`).

## Change log

- **2026-11-21:** First version. Studied Neos and Taawun (`docs/design/reference-study.md`); defined tokens
  (`src/app/design-tokens.css`, not yet imported), marks (`src/components/marks/`, not yet used) and the static
  specimen (`docs/design/preview.html`). Contrast computed for all pairs in both themes; all pass, with light faint at
  4.29:1 restricted to non-text. Open for the owner: the wordmark mark; following the system theme instead of forcing
  dark.
