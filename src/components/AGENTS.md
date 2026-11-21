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
(written sanad, then the identified narrators as an ordered rail), matn (Arabic first, the English labelled as an
unreviewed translation), assessments by tradition, variant texts, parallels only when present, reference list.
`loading.tsx` mirrors this column so nothing shifts when data arrives.

## Narrator detail

Same rhythm as the hadith page: uppercase section labels, no nested cards, one emerald accent. The tab bar is
hidden (kept for screen readers) when Biography is the only tab. `TabaqahTimeline` is an inline five-step scale
that highlights only a recorded generation.

## Route states

Every `error.tsx` renders `RouteError` and every `not-found.tsx` renders `RouteMessage` (`RouteState.tsx`). One
layout, one emerald primary action, one secondary link. `RouteError` logs only the digest (an error message can
carry query text) and retries once after two seconds, which covers a database waking from idle.
