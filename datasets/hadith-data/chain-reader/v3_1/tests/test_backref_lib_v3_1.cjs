// Back-reference detection in JS must equal the Python tool's (tests/backref_cases.json is read by both).  node --test v3_1/tests/test_backref_lib_v3_1.cjs
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const lib = require('../backref_lib_v3_1.cjs');

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

const openings = JSON.parse(fs.readFileSync(path.join(__dirname, 'opening_cases_v3_1.json'), 'utf8'));
test('v3.1 opening classes equal the Python tool on the shared cases (the asker, the inherited speaker, a bare «وعن»)', () => {
  for (const c of openings) assert.strictEqual(lib.openingClass(c.text), c.class, c.text.slice(0, 40));
});

test('an asker with a pronoun and an inherited speaker lean on the earlier report; a named asker and a named Imam do not', () => {
  assert.strictEqual(lib.inheritsAtTheStart('و سأله سماعة : عن الطعام'), true);
  assert.strictEqual(lib.inheritsAtTheStart('وقال عليه السلام: «الماء'), true);
  assert.strictEqual(lib.inheritsAtTheStart('و كتب البزنطي إلى أبي الحسن عليه السلام'), false);
  assert.strictEqual(lib.inheritsAtTheStart('و قال الصادق عليه السلام: «كل ماء'), false);
});

test('the widened walk stops at a report that names the speaker, passes a pronoun asker and the Prophet, and says what it found', () => {
  const rows = [
    { id: 'a', text: '517 - وقال الصادق عليه السلام: «من أصيب بمصيبة' },
    { id: 'b', text: '518 - و كان رسول الله صلى الله عليه و آله إذا أراد أن يتزوج' },
    { id: 'c', text: '519 - و سأله سماعة: عن كذا' },
    { id: 'd', text: '520 - وقال عليه السلام: «كذا' },
  ];
  const found = lib.walkBack(rows, 3, (r) => r.text, lib.LIMIT, true);
  assert.deepStrictEqual(found.previous.map((r) => r.id), ['c', 'b', 'a']);
  assert.strictEqual(found.chainFound, true);
  assert.strictEqual(found.supplies, 'speaker');
  const strict = lib.walkBack(rows, 3, (r) => r.text);
  assert.strictEqual(strict.chainFound, false);                 // v3 stops only at a written chain
  const chain = lib.walkBack([{ id: 'x', text: '4013 - و روى أبو بصير عن أبي عبد الله' }, { id: 'y', text: '4014 - و سأله سماعة: عن' }], 1, (r) => r.text, lib.LIMIT, true);
  assert.strictEqual(chain.supplies, 'chain');
  assert.strictEqual(lib.supplies('و قال رسول الله صلى الله عليه و آله: «من'), null);
  assert.strictEqual(lib.supplies('قال : و سألته عن الحظيرة'), null);    // «قال :» opens a quotation, it names no speaker
});
