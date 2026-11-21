# Tanzil Quran Text (Simple Clean and Uthmani)

Raw, unmodified upstream files. Untrusted data: read as text only. Used by `datasets/hadith-data/quran/`.

| Field | Value |
| --- | --- |
| Project | Tanzil, https://tanzil.net/ |
| Retrieved | 2026-11-21, generic client identity (`curl`), unauthenticated |
| Terms read first | https://tanzil.net/docs/Text_License (checked 2026-11-21) |
| Version | 1.1 (each file's own header: "Tanzil Quran Text (Simple Clean, Version 1.1)", "(Uthmani, Version 1.1)", Copyright 2007-2026 Tanzil Project) |
| Download | `https://tanzil.net/pub/download/index.php?quranType=<simple-clean|uthmani>&outType=txt-2&agree=true` (`txt-2` = `sura|aya|text`; the form's default options) |
| Licence | Creative Commons Attribution 3.0 (as the files' header states) |

## Files

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `quran-simple-clean.txt` (imla'i spelling, 6,236 verses) | 781,176 | `228df2a717671aeb9d2ff573002bd28d6b3f973f4bc7153554e3a81663d67610` |
| `quran-uthmani.txt` (Uthmani orthography, 6,236 verses) | 1,370,878 | `bf4f57b968d03f4131c070b1e285da9be0e0a108a21c910e872801ca273312c8` |

## Terms (verbatim from the licence page)

- Permission is granted to copy and distribute verbatim copies of this text, but CHANGING IT IS NOT ALLOWED.
- This Quran text can be used in any website or application, provided that its source (Tanzil Project) is clearly
  indicated, and a link is made to tanzil.net to enable users to keep track of changes.
- This copyright notice shall be included in all verbatim copies of the text, and shall be reproduced appropriately in
  all files derived from or containing substantial portion of this text.

## Required attribution wording (proposed)

> Qur'an text: Tanzil Quran Text (Uthmani / Simple Clean, version 1.1), (C) 2007-2026 Tanzil Project,
> https://tanzil.net/, Creative Commons Attribution 3.0. Unmodified; Tanzil does not endorse this archive.

Everything compared or folded (skeletons, hamza/alef folds) is computed in memory for matching only; the text shown
beside a citation is always the unmodified Tanzil verse text. The copyright block of the files must travel with any
file that reproduces a substantial portion (`quran_verses.jsonl.gz` does: its manifest carries the notice).

## Source record proposal for `src/lib/sources/registry.ts` (not edited here)

Add `'TNZ'` to `SourceCode` and `'text'` supply already exists:

```ts
{
  code: 'TNZ', anchor: 'tnz',
  name: 'Tanzil Quran Text (Simple Clean and Uthmani, version 1.1)',
  supplies: ['text'],
  took: 'The Qur\'an, verse by verse, to find and cite the verses that reports quote.',
  licence: { name: 'CC BY 3.0', url: 'https://creativecommons.org/licenses/by/3.0/' },
  requiredWording: 'Qur\'an text: Tanzil Quran Text ([text type], version 1.1), (C) 2007-2026 Tanzil Project, https://tanzil.net/, Creative Commons Attribution 3.0. Unmodified; Tanzil does not endorse this archive.',
  link: 'https://tanzil.net/', retrieved: '2026-11-21',
  databaseSourceSlugs: [], sourceCards: ['quran-tanzil'],
}
```

`browse-flows.test.ts` expects a `datasets/sources/*.md` card per record: a card `quran-tanzil.md` is needed
(not written: outside this lane's directories).
