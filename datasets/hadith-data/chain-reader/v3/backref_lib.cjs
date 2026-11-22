// Back references and previous reports for the v3 packet builder and the corpus census (see v3/AGENTS.md §previous reports).
// Pure functions, no database: the callers load the rows. OPENING must stay equal to OPENING in v3/holds_v3.py; tests/backref_cases.json runs both.
'use strict';

const MARKS = /[ً-ٰٟۖ-ۭـ​-‏‪-‮﻿]/g;
const PUNCT = /[\s،,.:;()\[\]«»"'*\-–—\/‘’“”…!?؟]+/g;
const CHAR_FOLD = { 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ی': 'ي', 'ې': 'ي', 'ے': 'ي', 'ئ': 'ي', 'ک': 'ك', 'ة': 'ه', 'ھ': 'ه', 'ہ': 'ه', 'ە': 'ه', 'ؤ': 'و' };
const KUNYA_CASE = { 'ابي': 'ابو', 'ابا': 'ابو', 'ذي': 'ذو', 'ذا': 'ذو', 'اخي': 'اخو', 'اخا': 'اخو' };

/** Letters-only comparison form, the same as norm_v3.fold_v3 (marks, bare hamza out; variants folded; punctuation one space; kunya case folded). */
function fold3(text) {
  let out = '';
  for (const ch of text || '') {
    if (ch === 'ء' || MARKS.test(ch)) { MARKS.lastIndex = 0; continue; }
    MARKS.lastIndex = 0;
    out += CHAR_FOLD[ch] || ch;
  }
  return out.replace(PUNCT, ' ').trim().split(' ').map((t) => KUNYA_CASE[t] || t).join(' ');
}

const OPENING = /^(?:\d+ )?(?:ح )?(?:و ?)?(?:(?<pronoun>عنهما|عنهم|عنها|عنه)(?= |$)|(?<isnad_phrase>بهذا (?:الاسناد|السند)|بنفس (?:الاسناد|السند)|بالاسناد|باسناده|باسنادهم|باسنادها|بالسند|بسنده|بسندهم)(?= |$)|(?<bare_an>عن ))/;
const FIRST_160 = /بهذا (?:الاسناد|السند)/;

/** pronoun | isnad_phrase | bare_an | in_first_160 | null */
function openingForm(text) {
  const folded = fold3(text);
  const m = OPENING.exec(folded);
  if (m) return Object.entries(m.groups).find(([, v]) => v !== undefined)[0];
  return FIRST_160.test(folded.slice(0, 160)) ? 'in_first_160' : null;
}
const opensWithBackReference = (text) => openingForm(text) !== null;
const opensAtTheStart = (text) => { const f = openingForm(text); return f !== null && f !== 'in_first_160'; };

const TRANSMISSION = /(?:^| )(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا|انبانا|ثنا|روي|حدثه|اخبره|سمعت|عن)(?= |$)/g;
/** A report that writes its own chain: it does not open with a back reference and its first 320 letters carry two transmission words. */
function hasWrittenChain(text) {
  const folded = fold3(text);
  if (OPENING.test(folded)) return false;
  return (folded.slice(0, 320).match(TRANSMISSION) || []).length >= 2;
}

/** Order of a report in its book: provider file and the numeric provider id (the printed number and hadith_no repeat inside a chapter or a section). */
function orderKey(row) {
  const file = /^provider-file:(\d+)\|/.exec(row.source_record_id || '');
  const digits = String(row.provider_hadith_id || '').replace(/\D/g, '');
  return { group: row.collection_id + '|' + (file ? file[1] : ''), position: digits ? Number(digits) : null };
}

/** The books' rows as ordered lists: Map(group -> rows sorted by provider id); rows without a numeric id are left out. */
function orderedBooks(rows) {
  const books = new Map();
  for (const row of rows) {
    const { group, position } = orderKey(row);
    if (position === null) continue;
    if (!books.has(group)) books.set(group, []);
    books.get(group).push({ ...row, position });
  }
  for (const list of books.values()) list.sort((a, b) => a.position - b.position);
  return books;
}

const LIMIT = 12;
/**
 * Walk back from the report at `index` of its ordered list until a report that writes its own chain is found (or LIMIT reports were passed).
 * Returns {previous: [rows nearest first, up to and including the chain-bearing one], chainFound}.
 */
function walkBack(list, index, readerText, limit = LIMIT) {
  const previous = [];
  for (let j = index - 1; j >= 0 && previous.length < limit; j--) {
    const row = list[j];
    const text = readerText(row);
    previous.push(row);
    if (hasWrittenChain(text)) return { previous, chainFound: true };
  }
  return { previous, chainFound: false };
}

module.exports = { fold3, OPENING, openingForm, opensWithBackReference, opensAtTheStart, hasWrittenChain, orderKey, orderedBooks, walkBack, LIMIT };
