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
`<html>` forces one theme (the selectors are `:root.light` / `:root.dark`, so a library's own `.light`/`.dark` class,
such as React Flow's, cannot force part of the page). No JavaScript is needed to follow the system.

**How the app reaches the tokens.** `src/app/globals.css` imports the token file and exposes three layers:

- **Token utilities** (`bg-paper`, `bg-sunken`, `text-ink`, `text-ink-muted`, `border-rule`, `border-rule-strong`,
  `border-control`, `text-accent`, `bg-accent-wash`, `text-danger`, `bg-notice`, `font-mono`, `font-arabic`), declared
  with `@theme inline reference` so Tailwind emits no duplicate variables. New code uses these.
- **shadcn aliases** (`--color-background` → paper, `--color-primary` → accent, ...) so `src/components/ui/*` keep
  their class names. `bg-accent` is the design accent (emerald), not shadcn's hover grey; hover grounds use
  `bg-sunken`.
- **Legacy palette aliases.** Tailwind's palette names resolve to the token that played the same role in the old
  dark-only interface (`slate-100` → ink, `slate-400` → ink muted, `slate-800` → rule, `slate-900` → sunken,
  `emerald-*` → accent, `red-*` → danger, every other hue → ink muted). A screen not yet converted therefore still
  follows both themes with one accent and red only for errors. Never write a palette name in new code; the aliases
  exist only as a safety net and are deleted once `rg "slate-|emerald-|amber-" src` is empty.
- `rounded-*` resolve to 0; `shadow-*`, `blur-*` (and so `backdrop-blur-*`) and `animate-*` generate nothing.

Shared type roles are component classes in `globals.css`: `type-label`, `type-small`, `type-reading`, `type-h1`..`h3`,
`type-display`, `type-code`, `arabic-inline`, `arabic-reading`, `arabic-display`, `page-header`, `section-rule`,
`link-prose`, `link-row`, `link-term`, `data-table` and `placeholder-bar`. `archive.css` is imported by
`globals.css` into the components layer, so utilities override it.

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
under the SIL Open Font License, and load through `next/font/google`. `next/font` serves them under generated family
names, so `layout.tsx` sets `--font-inter-face`, `--font-jetbrains-mono-face` and `--font-amiri-face` on `<html>` and
the token stacks read those first (`var(--font-inter-face, "Inter")`). Amiri for all Arabic (unchanged, OFL), with
Noto Naskh Arabic as fallback. Inter replaces Geist: both references use Inter, and its optical sizes hold up at 12px.

### Arabic beside Latin

- **Face.** Amiri, a classical naskh that sets full harakat cleanly. It is used for every Arabic run, including
  single names inside English sentences (`ArabicText`, `NarratorName`, `BilingualTitle` already split mixed strings).
- **Size.** About 1.25 times the Latin it sits beside, because Arabic letterforms are smaller at the same font size:
  22px reading text in a 16px interface, 18px names beside 14–16px Latin, 28px for a quoted report.
  `ArabicText variant="inline" | "reading" | "display"` applies the three roles; an Arabic run inside a Latin title
  (`BilingualTitle`) is set at 1.15em.
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

In order: `TEXT` label, Arabic text (22/44), the English (18/28) under its label from `englishLabel` ("Source-provided
English, not reviewed here") with its `englishReference` credit, or the one muted line "No English available yet"
(`archive/ReportEnglish.tsx`, the one component for every surface that shows a report's English), then the source short
reference. Then the isnad, assessments,
variants and references, each opened by a 1px ink rule and a 12px uppercase label. The facts margin holds a definition
list (tradition, work, number, book, attribution, tellings, address in mono) and the one secondary action
("Copy citation"). Under 1024px the facts follow the text.

### Isnad list (`hadith/[id]/components/IsnadChain.tsx`)

- Order is **as written**: the name nearest the compiler first, labelled "As written, nearest the compiler first".
  (The graph runs the other way, from the attribution down; each says which way it runs.)
- Each chain has a heading ("Chain 2 of 2", 20px) and a count ("5 names, 5 identified").
- Each position is a three-part row: the position number (12px muted), a rail (12px column with a 1px faint vertical
  line and the position's node mark), and the body. The body's first cell is the name as written: the Arabic surface
  at 18/32 at the end (right), its Latin form at 14px in the Latin face at the start (left), on one line when they fit,
  and under them one 12px muted line: the name-basis mark, how the Latin form was obtained, and the source code
  (`SourceCodeLink`). No Latin form means none of the rules applied: the Arabic stands alone, never a guess. The identity
  (14px) sits beside it from 640px and below it on smaller screens: a standing identity first under its own line
  ("machine-reviewed: two sources agree"), then the record name as a row link with the record's Arabic name in `<bdi>`,
  other records of the same person as "Same person in hadith-kg: …", and one basis line per candidate, each ending in
  its source codes.
- The chain's sources are credited once below the list with the full `SourceCredit` ("Identity: HKG …", "Latin name:
  THQ …"); each row carries only the codes.
- An unidentified mention shows an outline node and "Not identified" in muted text. It is never a link.
- A narrator through whom several chains of this report pass shows the shared node and "in N chains of this report".
- Where sources disagree, every candidate is listed with its own basis line, under "Sources differ on who this is".
  Only records of one registry known to name different people disagree; records in different registries with no link
  between them are listed without that line. Kunya-only candidates and an undecided shared Imam kunya are a note, never a
  disagreement.
- A position that is not a name written in this report says so on one 12px muted line under the name: "From the earlier
  report's chain" (a continuation repeats the earlier report's names; the section already opens with "Chain continues
  from No. N"), "Unnamed transmitter: the text names no one here" (a gap the text marks: balagh, «عن رجل»), "Refers back
  to the previous report's chain; not a narrator" («عنه»). A chain that relies on another says so once under its heading in
  12px muted text: "Chain relies on the previous report", "Chain starts mid-way and relies on an earlier report", "The
  compiler gives his route to the first narrator elsewhere in the book". Text only, no new mark.
- Rows are divided by hairlines; no boxes. *Shown in:* `#isnad`.

### Identity basis labels (`BasisMark`, basis wording)

The basis line is the basis mark (10px), the wording, and the source code of the dataset behind it (`K6I` for
source-index bases, `MSD` for name bases, `SWI` for reviewer decisions). The marks form a scale that fills as the basis
firms up:

| Basis | Mark | Wording |
| --- | --- | --- |
| `reviewer_decision` | filled disc | verified by a reviewer |
| `source_index_confirmed_by_text`, `source_hadith_kg_confirmed_by_text`, `source_riwayat_confirmed_by_text` (tier basis), `imam_kunya_convention` | ring with a centre dot | six-books source index / hadith-kg index / the annotation's origin, "matches the text"; the Imam's conventional kunya with the honorific |
| `source_index`, `source_hadith_kg`, `source_riwayat`, and a Riwayat automatic link or label record even when confirmed | ring | six-books source index / hadith-kg index / "Thaqalayn's annotation via Riwayat", "Riwayat's automatic link, not counted" |
| `name_exact`, `name_spelling_fold` | dashed ring | matched by name |
| `name_kunya_only`, `imam_kunya_candidate` | short bar (off the scale) | matched by kunya only; a kunya several Imams share, not decided |

The standing identity's own line uses the ring with a centre dot and says what made it machine-reviewed (`STANDING_BASIS_LABEL`:
"the source's index and the text agree", "two sources agree", "hadith-kg's index and the text agree", "the annotation
and the text agree", "the Imam's kunya in Imami usage"). Kunya-only is a bar rather than a circle because, by owner
decision, it is a label and not a rung on the scale. Timeline datum bases (`basisLabel`) stay text-only. Wording and
marks live in one file, `marks/BasisMark.tsx`.

### Latin names (`NameBasisMark`, `NAME_LATIN_BASIS_LABEL`)

A 10px square of horizontal rules beside the Latin form, from the most to the least source-given:

| Basis | Mark | Wording | Source code |
| --- | --- | --- | --- |
| `provider_english` | two full rules | the source's English | `THQ` |
| `identity_name` | a full rule over a short one | name of the identified record | `MSD` (lexicon) or `SWI` (Imam register) |
| `transliteration_vocalized` | one full rule | transliterated from the vowelled text | `SWI` |
| `transliteration_table` | one dashed rule | transliterated from common name parts | `SWI` |

The Latin form never stands in for the identity: it renders the name as written.

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
("Clear"). A disabled control shows muted text and a rule-coloured border (faint is never text).

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
- **As built (2026-11-21).** The diagram is React Flow over a Sugiyama layout (`family/TransmissionDiagram.tsx`), not
  the static SVG of the specimen. It follows the node shapes, faint 1px edges, 15px Amiri labels, 11px work labels and
  accent-only selection above; traditions are not separate groups in that layout, so edges carry `TRADITION_DASH` and
  the legend names each pattern. Not yet built: the attribution rule at the top, per-tradition groups, the selection
  details panel and the 46rem scroll region (the canvas pans and zooms instead). React Flow's `colorMode` is fixed to
  `light` so server and client agree; the tokens carry the theme.

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
| `BasisMark`, `IDENTITY_BASIS_LABEL`, `STANDING_BASIS_LABEL`, `candidateBasisLabel` | identity basis scale and its wording |
| `NameBasisMark`, `NAME_LATIN_BASIS_LABEL` | how a chain name's Latin form was obtained |
| `NarratorNode`, `NarratorNodeShape`, `NARRATOR_NODE_LABEL` | graph nodes, standalone or inside a larger SVG |
| `ChainConnector` | vertical rail segment: continuous, gap, tradition dash, 2px emphasis |
| `ArrowIcon`, `SearchIcon`, `ExternalIcon`, `CopyIcon`, `CheckIcon`, `CloseIcon`, `ChevronIcon`, `MenuIcon` | interface icons |
| `MarkSvg` | shared frame: `currentColor`, `<title>` by default, `decorative` hides it |
| `ProductMark` | the wordmark's 2x2 square of the four tradition modules (site header) |

All are server-safe (no client hooks other than `useId`), flat, single-colour through `currentColor`. In use: tradition
marks (`TraditionBadge`, tellings, all-chains, timeline group labels, filter chips, home), basis marks and nodes
(`IsnadChain`), nodes (diagram and legend), icons (search fields, copy citation, report pager).

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

## Applying the system: what remains

*Removable: delete this section once every item is done and recorded in the change log.* The first pass (change log,
2026-11-21, second entry) applied tokens, primitives, marks and every route. Remaining, in priority order:

1. **Transmission graph.** The attribution rule, per-tradition groups, selection panel with `aria-live`, and the 46rem
   scroll region (see §Transmission graph, "As built"). This is layout logic, not styling.
2. **Tellings as a table.** The tellings list keeps its rows (with text excerpts) rather than the specimen's five-column
   table; converting it changes what each row shows.
3. **Isnad extras.** The section note "As written, nearest the compiler first", per-chain counts ("5 names, 1
   identified") and the shared node with "in N chains of this report" need new wording or a cross-chain count; the
   list uses identified, unidentified and contested nodes today.
4. **Facts margin contents.** It holds the existing reference rows; tellings count, address and "Copy citation" stay
   where they are (summary line, trail, report footer).
5. **Admin.** On tokens through the legacy aliases and a class sweep, but still uses Lucide icons and some sunken
   panels; replace icons with `marks/Icons.tsx` and move palette names to token utilities, then delete the aliases.
6. **Chain timeline.** Lane lines in `TRADITION_DASH` where traditions share the axis (lanes are bars today; the
   group label carries the tradition mark). The section itself is very long on large families (one row per transmitter
   for up to 12 tellings), a content decision for the history lane.

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

- **2026-11-21 (names, identities and English pass):** The isnad list row shows the Latin form beside the Arabic (Arabic
  at the end, Latin at the start, one muted basis line with `NameBasisMark`); the identity cell groups records of one
  person, leads with the standing identity's own line, and ends each basis line in inline source codes, with the chain's
  full credits once below the list (`ChainSourceCredits`, `SourceCodeLink`). New bases join the basis scale (table above).
  One English block (`archive/ReportEnglish.tsx`) on the report page, the family view and each telling, and a one-line
  label with its source code under each excerpt in report lists; "No English available yet" replaces silence. Narrator
  pages gain "Record in …" (an external source's or the Imam register's record, with a 2px ink start rule notice when the
  id names a label) and "Named in chains" (paged). No colour token changed.
- **2026-11-21 (application pass):** Applied the system to the whole app. Tokens imported in `globals.css` with token
  utilities, shadcn aliases and legacy palette aliases (§Tokens); radii 0, no shadows, blurs or animations; Inter and
  JetBrains Mono through `next/font` (`--font-*-face` on `<html>`, token stacks read them first); the forced `dark`
  class removed, so the site follows the system theme (owner decision); a skip link. Primitives (`ui/*`) flattened to
  the button, input and label rules; badges are labels; `TraditionBadge` renders `TraditionMark`; `IsnadChain` uses
  `BasisMark`, `NarratorNode` and `IDENTITY_BASIS_LABEL` (local copy deleted); the family view and timeline use the
  marks' `TRADITION_DASH` (the family view's own patterns were replaced, legend wording updated to match); `ProductMark`
  added and used in the header. `archive.css`, `timeline.module.css` and `family.module.css` alias every value to
  tokens; the archive's red accent is now emerald; faint text in the timeline, footer and family view moved to muted
  (faint measured 4.29:1, below text contrast). Every route restyled: home, collections, hadith list, report (page
  header, 8+4 grid with facts margin, text before isnad), chains view and diagram, narrator list and page, comparative,
  glossary, sources (tables stack below 640px), sign-in, admin, not-found, error, global error and loading states
  (flat placeholders, no pulse). Rule changes: `.light`/`.dark` scoped to `:root`; disabled text is muted, not faint;
  tradition options sorted alphabetically at the call sites. No colour token changed, so the contrast table stands.
- **2026-11-21:** First version. Studied Neos and Taawun (`docs/design/reference-study.md`); defined tokens
  (`src/app/design-tokens.css`, not yet imported), marks (`src/components/marks/`, not yet used) and the static
  specimen (`docs/design/preview.html`). Contrast computed for all pairs in both themes; all pass, with light faint at
  4.29:1 restricted to non-text. Open for the owner: the wordmark mark; following the system theme instead of forcing
  dark.
- 2026-11-22: Isnad list position notes for inherited names and unnamed transmitters (chain builder round 2); identity
  basis "named by the work's own opening isnad (report No. 1)" drawn with the confirmed mark.
- 2026-11-22: chain suspension line under the branch heading and the back-reference position note (round 2, Imami).
- 2026-11-22: "A link is missing after name N" line under the branch heading; identity basis "named by a printed edition's note" with its citation (round 2, Sunni).
