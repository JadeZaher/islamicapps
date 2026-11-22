// Runs each detector over the confirmed defects (fixtures.json, exported read-only from production) and fails if one is missed.
// Usage: node test_detectors.cjs
'use strict';
const assert = require('assert');
const fx = require('./fixtures.json');
const D = require('./detectors.cjs');
const ctx = D.prepare(fx);
const hits = D.runAll(ctx);
const by = (hadith, detector, pred = () => true) => hits.filter((h) => h.hadith_id === hadith && h.detector === detector && pred(h));
let failures = 0;
const check = (name, fn) => { try { fn(); console.log('ok  ', name); } catch (e) { failures++; console.log('FAIL', name, '-', e.message); } };

check('homonym: «عمر» -> ʿUmar b. al-Khattab in k6:28147 is blamed (chronology, high)', () => {
  const h = by('hadith:k6:28147', 'chrono_contradiction', (x) => x.mention_id === 'mention:k6:28147:0000:0001' && x.confidence === 'high');
  assert.ok(h.length === 1, 'no high-confidence chrono hit on the «عمر» mention');
});
check('homonym: «عمر بن الخطاب أبو حفص» (Abu Dawud shaykh) in k6:18025 is blamed', () => {
  const h = by('hadith:k6:18025', 'chrono_contradiction', (x) => x.mention_id === 'mention:k6:18025:0000:0000' && x.confidence === 'high');
  assert.ok(h.length === 1, 'shaykh mention not caught');
});
check('bare relation «أبي» resolved to the Companion in k6:10550 chain 0002 is blamed', () => {
  const h = by('hadith:k6:10550', 'chrono_contradiction', (x) => x.mention_id === 'mention:k6:10550:0002:0001' && x.confidence === 'high');
  assert.ok(h.length === 1, 'not caught by chronology');
  const br = by('hadith:k6:10550', 'bare_relation_resolved', (x) => x.mention_id === 'mention:k6:10550:0002:0001');
  assert.ok(br.length === 1, 'bare_relation_resolved did not see the relation word');
});
check('flattened tahwil: k6:28195 chain 0000 is split before «عمرو بن عثمان» (position 4)', () => {
  const s = by('hadith:k6:28195', 'seam_in_chain', (x) => x.split_position === 4);
  assert.ok(s.length === 1, 'seam_in_chain missed position 4');
});
check('flattened tahwil: k6:28195 repeats الأوزاعي and الزهري/ابن شهاب in one chain', () => {
  assert.ok(by('hadith:k6:28195', 'repeated_narrator').length >= 2);
});
check('flattened tahwil: bukhari k6:1514 (Ismail<Malik || Abdallah b. Yusuf<Malik) is split at position 2', () => {
  assert.ok(by('hadith:k6:1514', 'seam_in_chain', (x) => x.split_position === 2).length === 1);
});
check('co-transmitters «جرير وعيسى» stored as teacher -> student in k6:9023', () => {
  assert.ok(by('hadith:k6:9023', 'co_transmitter_gap', (x) => x.mention_id === 'mention:k6:9023:0000:0002').length === 1);
});
check('formula stored as a narrator that even carries an id: «حماد بن زيد كلهم» in k6:8142', () => {
  const h = by('hadith:k6:8142', 'non_name_surface', (x) => x.mention_id === 'mention:k6:8142:0008:0001');
  assert.ok(h.length === 1 && h[0].evidence.values.narrator_id, 'formula mention not flagged or id missing');
});
check('Tirmidhi grading formula «هذا حديث حسن صحيح» as a mention in k6:21827', () => {
  assert.ok(by('hadith:k6:21827', 'non_name_surface', (x) => x.mention_id === 'mention:k6:21827:0002:0005').length === 1);
});
check("relation «أبي» resolved to الجراح بن مليح instead of the speaker father (k6:14206) fails the nasab test", () => {
  assert.ok(by('hadith:k6:14206', 'bare_relation_resolved', (x) => x.verdict === 'mismatch' && x.mention_id === 'mention:k6:14206:0001:0001').length === 1);
});
check('two routes joined in one Tirmidhi chain (k6:23888) is caught by text order', () => {
  assert.ok(by('hadith:k6:23888', 'text_order_mismatch').length === 1);
});
check('control: a clean chain yields no high-confidence correction-grade hit', () => {
  const bad = hits.filter((h) => h.hadith_id === fx.control && ['chrono_contradiction', 'seam_in_chain', 'repeated_narrator', 'co_transmitter_gap'].includes(h.detector));
  assert.ok(bad.length === 0, 'false positive on control ' + fx.control);
});
if (failures) { console.log(failures + ' failure(s)'); process.exit(1); }
console.log('all detector tests passed');
