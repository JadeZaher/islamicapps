import assert from 'node:assert/strict';
import {
  deterministicRijalCitationId,
  formatRijalLocator,
  normalizeCategory,
  normalizeSha256,
  normalizeTradition,
} from '../load-history-rijal';

// Deterministic RIJ citation IDs
const id1 = deterministicRijalCitationId('rijal_work:ibn_hajar_taqrib', 'edition:openiti:foo', { start: 10, end: 20 }, 'a'.repeat(64));
const id2 = deterministicRijalCitationId('rijal_work:ibn_hajar_taqrib', 'edition:openiti:foo', { start: 10, end: 20 }, 'a'.repeat(64));
const id3 = deterministicRijalCitationId('rijal_work:ibn_hajar_taqrib', 'edition:openiti:foo', { start: 10, end: 21 }, 'a'.repeat(64));
assert.equal(id1, id2);
assert.notEqual(id1, id3);
assert.match(id1, /^cit:rijal:[0-9a-f]{20}$/);

// SHA-256 validation
assert.equal(normalizeSha256('A'.repeat(64)), 'a'.repeat(64));
assert.equal(normalizeSha256('not-a-sha'), null);

// Tradition and category normalization
assert.equal(normalizeTradition('imami'), 'Imami');
assert.equal(normalizeTradition('SUNNI'), 'Sunni');
assert.equal(normalizeTradition('unknown'), null);
assert.equal(normalizeCategory('MILITARY'), 'MILITARY');
assert.equal(normalizeCategory('INVALID'), null);

// Locator formatting
assert.deepEqual(formatRijalLocator({ volume: '1', page: '283', entry_number: '3029' }), {
  volume: '1',
  page: '283',
  text: 'v1, p283, entry 3029',
});

console.log('load-history-rijal unit tests passed.');
