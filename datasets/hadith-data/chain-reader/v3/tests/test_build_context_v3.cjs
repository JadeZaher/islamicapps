// The v3 packet builder's budget rules: previous_reports keep every intermediate and the named chain's words; the rest of the context still obeys the 3,000-character budget.
//   node --test v3/tests/test_build_context_v3.cjs
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { fitBudget, fitPrevious, leadingNumber } = require('../build_context_v3.cjs');

const long = (n) => 'كلمة '.repeat(n).trim();

test('fitPrevious shortens intermediates first, never drops one, and keeps the named chain readable', () => {
  const items = [];
  for (let i = 1; i <= 11; i++) items.push({ ref: 'prev' + i, number: String(40 - i), has_written_chain: false, chain_text: `${40 - i} - وبالإسناد الأول عن علي بن مهزيار، ${long(20)}` });
  items.push({ ref: 'prev12', number: '28', has_written_chain: true, chain_text: 'حدثنا أبو حفص عمر بن محمد بن علي الزيات قال حدثنا عبيد الله بن جعفر بن محمد بن أعين', text_head: long(60) });
  const fitted = fitPrevious(items.map((x) => ({ ...x })), 2600);
  assert.strictEqual(fitted.length, 12);
  assert.ok(JSON.stringify(fitted).length <= 2600);
  assert.strictEqual(fitted[11].chain_text, items[11].chain_text, 'the named chain is not elided');
  assert.ok(fitted.every((p) => p.chain_text.length > 0));
});

test('fitBudget drops optional context in order', () => {
  const context = { work: { key: 'k' }, source_notes: [{ x: long(300) }], name_facts: [{ name: long(200), src: 'MSD' }], source_claims: [{ source: 'RWY', routes: [[long(5)]] }] };
  const omitted = [];
  fitBudget(context, 900, omitted);
  assert.ok(JSON.stringify(context).length <= 900);
  assert.strictEqual(omitted[0], 'source_notes');
  assert.ok(context.work && context.source_claims);
});

test('leadingNumber reads the printed number before the text', () => {
  assert.strictEqual(leadingNumber('349 - وبهذا الإسناد'), '349');
  assert.strictEqual(leadingNumber('6ـ مُحَمَّدُ'), '6');
  assert.strictEqual(leadingNumber('حدثنا'), null);
});
