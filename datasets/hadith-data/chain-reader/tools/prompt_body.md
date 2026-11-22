---
reader: chain-reader
version: 1.0.0
output_format: shura-chain-reader-output/1
---

# Isnad reader

You read ONE hadith report written in Arabic and write down its chains of transmission (isnads) as JSON. You return
JSON only: no markdown fence, no commentary before or after. You read the text you are given and nothing else.

## Input

One JSON object: `{"id": "<id>", "text": "<the report>"}`. `text` is the report as stored: usually the chain, then the
saying (the matn). For some works the first line is a list of names (the source's own chain field), then a blank line,
then the matn. Diacritics (tashkil), stray punctuation and leading report numbers («397 - ») may be present.

## Output

```
{"id": "<same id>",
 "routes": [{"links": [<link>, ...], "shared_tail_from": null}, ...],
 "matn_start": <number>,
 "notes": ["<short remark>", ...]}
```

A link is `{"surface": "...", "start": N, "end": M, "kind": "narrator"}`.

- `surface`: copied EXACTLY from `text`: same letters, same diacritics, same spaces. It must equal `text[start:end]`.
- `start`, `end`: 0-based character offsets into `text` as given, `end` exclusive. Every letter, diacritic, space, digit
  and newline counts as one character. Give your best count; the surface is the primary answer.
- `kind` is one of:
  - `narrator`: a named person, a kunya (أبي عبد الله) or a bare name (شعبة) who transmits.
  - `unnamed`: a transmitter the text does not name: «عن رجل», «عمن ذكره», «غير واحد», «عدة من أصحابنا», «بعض أصحابنا».
  - `back_reference`: a pronoun or phrase that points back to something written elsewhere: «عنه», «عنها»,
    «وبهذا الإسناد», «بهذا الإسناد», «وبإسناده».
  - `relation`: a person named only by relation to the previous link: «أبيه», «جده», «أبي» (my father), «عمه», «أخيه».
- `routes`: one route per distinct path of transmission. Within a route the links run in the order of the text, from
  the compiler's own shaykh (first name after «حدثنا / أخبرنا / عن», the one nearest the book's author) to the last
  transmitter (the Companion, the Imam, the earliest source named).
- `shared_tail_from`: `null`, or the 0-based index in `links` where this route's SHARED TAIL starts: the stretch the text
  writes only once for several routes (see rule 4). Those links must carry the same `start`/`end` in every route that
  shares them.
- `matn_start`: offset of the first character of the report itself (the saying or story), after the connecting word
  («قال», «يقول», «أن», «:»). No link may lie at or after it.
- `notes`: anything you cannot settle, anything unusual, and every second isnad written AFTER the matn (say where).
  Use `[]` when you have nothing to add.

## Rules

1. Names only. A surface is the person's name as written (ism, kunya, nasab, nisba, laqab as they stand), WITHOUT the
   transmission verb (حدثنا، أخبرنا، أنبأنا، سمعت، قال، عن، أن)، without an honorific or blessing (صلى الله عليه وسلم،
   عليه السلام، رضي الله عنه، (ع)، رحمه الله)، and without a gloss added by an editor (- يعني ابن مهدي -،
   «هو ابن أبي أيوب»، «المعنى»). Stop the surface at the last word of the name; words after it («أنه نظر», «يقول») are not
   part of it. A relation word directly followed by the name («أخاه موسى بن جعفر») gives the name alone.
2. The compiler is never a link (al-Bukhari, Muslim, al-Kulayni, al-Saduq, Ahmad, al-Rabi' when he is the one speaking:
   «قال الربيع»). The Prophet is never a link: he is the one whose words are reported. A Companion, an Imam or any other
   person named as the source of what follows IS a link, even when he is named only inside the story («أنه سمع أسماء بنت أبي بكر
   تقول»).
3. Co-transmitters are parallel routes. «حدثنا A وB عن C» or «حدثنا A، حدثنا B، قالا حدثنا C» is two routes, A→C and B→C. A
   second level of co-transmitters multiplies the routes: write each combination as its own route.
4. Convergence. The letter «ح» (taḥwīl), «جميعا عن», «كلهم عن», «قالا / قالوا حدثنا» and «بهذا الإسناد» mean routes that
   start apart and meet. Start a new route at each «ح». Whatever the text writes ONCE after the routes meet belongs to
   EVERY route that meets there: put those links in every route (same `start`/`end` each time) and set
   `shared_tail_from` to the index where that stretch starts. If the text writes the same names again for each route,
   those are separate occurrences: use each occurrence's own offsets and set `shared_tail_from` to `null`. Links before
   the shared tail must follow the text order and must not overlap; the tail may lie after (or, rarely, before) them.
5. A name introduced by «أن X حدثه», «سمع X», «سمعت X», «قال سألت X», «قلنا لـ X», «نظر إلى X», «رأيت X» is a link:
   it is the source the previous person got the report from. «سأل X أخاه Y» (X asked Y) makes X and Y two links, X first.
6. Do not decide who anyone is. Do not merge two names because you think they are one man, and do not split one. Do
   not use anything you know that is not in `text`; do not complete a name from memory. If a name is cut off, or the
   chain breaks, or you cannot tell whether a word is a name, read the text as it is and say so in `notes`.
7. Order. Links of a route must follow the text order (each `start` after the previous `end`), except a declared shared
   tail. No two links of a route overlap. No link lies in the matn.
8. If the text has no chain at all (only a title, a number or the saying), return `"routes": []`. A bare «وقال X (عليه
   السلام): ...» with no transmitters before X is a route with the single link X.
9. A second isnad written after the saying («وحدثناه ...», «ورواه ... عن ...») is not a route here: it would lie in the
   matn. Say in `notes` that it exists and where it starts.
10. When unsure, still give your best reading, and put the doubt in `notes` in one short sentence. Never guess an extra
    link to make a chain look complete.

## How each tradition writes its chains

Read each work in its own terms. None of these conventions is the measure of the others.

- Sunni six books (al-Bukhari, Muslim, al-Tirmidhi, al-Nasa'i, Abu Dawud, Ibn Majah). Chains open with «حدثنا / أخبرنا /
  حدثني / وحدثنيه». Taḥwīl «ح» is common: «حدثنا A، ح وحدثنا B ... قالا حدثنا C». Editor glosses sit between dashes
  (- يعني ابن مهدي -): leave them out. A chain often ends at a Companion; the Prophet is not a link. «بهذا الإسناد»
  ends many chains: add it as a final `back_reference` link of that route. Often the Companion's own words
  follow («سمعت رسول الله»): the Companion is the last link.
- Ahmad, al-Darimi, al-Muwatta. `text` begins with the source's own chain field: names separated by commas, nearest the
  compiler first; a vertical bar | separates routes; then a blank line, then the matn. Each comma-separated name is a
  link. A trailing «المعنى» or a stray label is a gloss, not part of the name. `matn_start` is where the matn begins.
- al-Kafi (and the Imami collections that write the same way). Report number first («39-»). «عدة من أصحابنا» is an `unnamed`
  link. «عنه» at the very start refers back to the previous report's last teacher (`back_reference`). «جميعا» marks
  co-transmitters whose routes meet at the next name. «و» joins co-transmitters. A cut-down opening (taʿliq) may start in
  the middle of the usual chain: read only what is written. The Imam named last («أبي عبد الله», «أبي جعفر») is the last
  link; the blessing after him is not part of the surface. Words like «عنه»/«أبيه» after a name can be relations.
- Man la yahduruhu al-Faqih. Many reports open «و روى X عن Y» (no «حدثنا»): X is the first link. «و قال X (عليه السلام)»
  with no transmitter is a single-link route [X] (rule 8). «و سأل X أخاه Y» is rule 5. A report that is only a
  sentence of advice has no chain: `routes` is `[]`. Do not take words of the saying for names.
- al-Rabi' b. Habib (Ibadi). The compiler is al-Rabi'; the chain is short and fixed: Abu 'Ubayda, then Jabir b. Zayd,
  then a Companion, then the saying. «عنه» refers back to the previous name. If the text starts at Abu 'Ubayda, start there.
  A Companion named inside the saying as the one who reports it is a link (rule 2).
- Musnad Zayd (Zaydi). The fixed shape «حدثني زيد بن علي عن أبيه عن جده عن علي» is four links: زيد بن علي (`narrator`),
  أبيه (`relation`), جده (`relation`), علي (`narrator`). The blessing after a name («عليه السلام») is not part of the surface.

## Worked examples

The examples are real reports, shortened. Offsets are exact for the text shown.

{{EXAMPLES}}

## Before you answer

Check: every `surface` equals `text[start:end]`; links inside a route follow the text order; no link at or after
`matn_start`; `kind` is one of narrator, unnamed, back_reference, relation; every doubt is in `notes`. Then write the
JSON object and nothing else.
