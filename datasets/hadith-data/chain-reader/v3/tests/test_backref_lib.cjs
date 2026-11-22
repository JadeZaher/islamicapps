// Back-reference detection in JS must equal the Python tool's (tests/backref_cases.json is read by both).  node --test v3/tests/test_backref_lib.cjs
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const lib = require('../backref_lib.cjs');

const cases = JSON.parse(fs.readFileSync(path.join(__dirname, 'backref_cases.json'), 'utf8'));
test('opening forms equal the Python tool on the shared cases', () => {
  for (const c of cases) {
    assert.strictEqual(lib.opensWithBackReference(c.text), c.opens, c.text.slice(0, 40));
    assert.strictEqual(lib.openingForm(c.text), c.form, c.text.slice(0, 40));
  }
});

test('walkBack passes back references until a report that writes its own chain, and says when none is found', () => {
  const rows = [
    { id: 'a', text: '4 - حدثنا أبو الحسن محمد بن علي عن أبيه عن علي قال: كذا' },
    { id: 'b', text: '5 - وبهذا الإسناد عن الرضا' },
    { id: 'c', text: '6 - وبهذا الإسناد قال: كذا' },
    { id: 'd', text: '7 - وبهذا الإسناد قال: كذا آخر' },
  ];
  const found = lib.walkBack(rows, 3, (r) => r.text);
  assert.deepStrictEqual(found.previous.map((r) => r.id), ['c', 'b', 'a']);
  assert.strictEqual(found.chainFound, true);
  const none = lib.walkBack(rows.slice(1), 2, (r) => r.text);
  assert.deepStrictEqual(none.previous.map((r) => r.id), ['c', 'b']);
  assert.strictEqual(none.chainFound, false);
});

test('order key uses the provider file and numeric provider id, not the repeating section number', () => {
  const books = lib.orderedBooks([
    { id: 'x2', collection_id: 'c', source_record_id: 'provider-file:39|hadith:102', provider_hadith_id: '102' },
    { id: 'x1', collection_id: 'c', source_record_id: 'provider-file:39|hadith:101', provider_hadith_id: '101' },
    { id: 'y1', collection_id: 'c', source_record_id: 'provider-file:40|hadith:5', provider_hadith_id: '5' },
    { id: 'pc', collection_id: 'c', source_record_id: 'pc_1', provider_hadith_id: 'pc_x' },
  ]);
  assert.deepStrictEqual(books.get('c|39').map((r) => r.id), ['x1', 'x2']);
  assert.deepStrictEqual(books.get('c|40').map((r) => r.id), ['y1']);
});
