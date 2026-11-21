# Glossary

`terms.ts` is the single source of term definitions. `/glossary` (`src/app/glossary/page.tsx`), `GlossaryTerm`
(`src/components/GlossaryTerm.tsx`) and `docs/glossary.md` all read it. Never edit `docs/glossary.md` by hand:
run `npx tsx src/lib/glossary/generate-doc.ts` (or `--check` to fail on drift).

## Writing rules

- One plain sentence per definition, followable without specialist training.
- Neutral across Sunni, Imami, Zaydi and Ibadi: no tradition is the default (the Traditions section is
  alphabetical), each is described in its own terms, and disputed questions are described as disputed.
- No entry promises more certainty than the data has. "In this archive" says what the app actually does.
- Where a tradition-specific usage is uncertain, write conservatively and set `ownerReview` to the specific doubt.
  Those doubts are listed in `docs/glossary.md` and never shown on the public page.
- Slugs are permanent anchors (`/glossary#kunya`); other pages link to them. Do not rename one without
  updating its links.

## Transliteration

`TRANSLITERATION_NOTE` states the scheme: no long-vowel or dot marks; ʿ (U+02BF) for ʿayn and ʾ (U+02BE) for
hamza, omitted word-initially; th, dh, kh, sh, gh digraphs; doubled letters written twice; the article as al-
without assimilation; ta marbuta as -a. Slugs drop ʿ and ʾ. The filter ignores these marks and Arabic vowel
signs, so "daif", "daʿif" and "ضعيف" all find the same entry.

## Enum coverage

Every value of every enum in `src/db/schema/enums.ts` is either named in some entry's `enumValues` or listed in
`enum-coverage.ts` as not user-facing or plain language, with a reason. `__tests__/glossary.test.ts` discovers
the enums at run time, so a new enum or value fails the test until it is accounted for.

Run: `npx tsx src/lib/glossary/__tests__/glossary.test.ts` (from the repository root).
