// Table-driven tests of the builder's pure helpers: node --test context/tests
const test = require('node:test'); const assert = require('node:assert');
const { fold, diffTexts, chainSpan, opensWithBackReference, fitBudget } = require('../build_context.cjs');

test('diffTexts: what counts as a difference', () => {
  const table = [
    ['identical after diacritics, spacing, number and the ﷺ sign', '39- عِدَّةٌ مِنْ أَصْحَابِنَا وَأَحْمَدَ', 'عدة من أصحابنا وأحمد', 'identical_after_normalisation'],
    ['words glued in one copy', 'قال شيئا من محارم الله', 'قال شيئا منمحارم الله', 'identical_except_word_spacing'],
    ['ﷺ against the spelled honorific', 'قال النبي صلى الله عليه وسلم كذا', 'قال النبي ﷺ كذا', 'identical_after_normalisation'],
    ['theirs holds more (another chain after the matn)', 'قال كذا وكذا', 'حدثنا فلان قال كذا وكذا وحدثنا غيره', 'ours_inside_theirs'],
    ['a different word', 'قال شيئا من محارم الله', 'قال شيئا من حدود الله', 'differs'],
  ];
  for (const [name, ours, theirs, relation] of table) assert.strictEqual(diffTexts(ours, theirs).relation, relation, name);
  const d = diffTexts('أ ب ج د هـ', 'أ ب س د هـ');
  assert.strictEqual(d.shared_opening_words, 2); assert.strictEqual(d.shared_closing_words, 2);
});

test('opensWithBackReference: the openings that need the previous report', () => {
  const yes = ['13- عنه، عن أحمد بن مهران', '20 - وبهذا الإسناد قال', '168 - وعن أبي عبد الله عليه السلام قال', 'حدثنا ابن أبي شيبة بهذا الإسناد مثله'];
  const no = ['39- عِدَّةٌ مِنْ أَصْحَابِنَا عَنْ سَهْلٍ', 'حدثنا أبو بكر، حدثنا وكيع، عن الأعمش', '6ـ عَلِيُّ بْنُ إِبْرَاهِيمَ عَنْ أَبِيهِ'];
  for (const t of yes) assert.ok(opensWithBackReference(t), t);
  for (const t of no) assert.ok(!opensWithBackReference(t), t);
});

test('chainSpan: ends at the last located stored surface, marks ignored; null when none is found', () => {
  const text = '6ـ عَلِيُّ بْنُ إِبْرَاهِيمَ عَنْ أَبِيهِ عَنْ يُونُسَ قَالَ سَأَلْتُ أَبَا عَبْدِ الله عَنْ كذا';
  assert.strictEqual(fold(chainSpan(text, ['علي بن إبراهيم', 'أبيه', 'يونس'])).endsWith('يونس'), true);
  assert.strictEqual(chainSpan(text, ['لا يوجد']), null);
});

test('fitBudget: drops the lowest-priority item first and records nothing when it fits', () => {
  const big = 'x'.repeat(900);
  const context = { work: { name: 'w' }, source_claims: [{ source: 'K6I', sequence: [big] }], name_facts: [{ name: big }], correspondences: [{ chain_text: big }] };
  const omitted = []; fitBudget(context, 1400, omitted);
  assert.ok(JSON.stringify(context).length <= 1400); assert.ok(context.source_claims, 'claims outrank facts and correspondences');
  const small = { work: { name: 'w' }, source_claims: [] }; const none = []; fitBudget(small, 1400, none); assert.deepStrictEqual(none, []);
});
