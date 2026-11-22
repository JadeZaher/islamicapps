/** The tier lines under a model-read chain, as the owner worded them (2026-11-22): one row per tier. npx tsx "src/app/hadith/[id]/components/__tests__/chain-tier-labels.test.ts" (not --test: the brackets read as a glob) */
import assert from 'node:assert/strict';
import test from 'node:test';
import type { ChainFixLabel } from '@/db/queries/contracts';
import { chainFixNote, noChainNote, sayingHeading } from '../chain-structure';

const reading: ChainFixLabel = { fix_id: 'chain-fix:x', state: 'accepted', effect: 'replace_routes', models: ['claude-haiku-5-5'], runs: 2, decided_at: '2026-11-22T18:00:00Z',
  awaiting_final_review: true, human_confirmations: [] };
const review = { model_id: 'claude-opus-5-5', run_id: 'r1', at: '2026-11-23T09:00:00Z', outcome: 'label_ai_reviewed', decision: 'confirm_reading' };

test('each tier reads as the owner worded it; "Verified" only names a person; "Agent verified" only with a witness match', () => {
  const rows: [string, ChainFixLabel, string, string][] = [
    ['read by two models', reading, 'read_by_model', 'Read by two models (claude-haiku-5-5), 2026-11-22'],
    ['AI reviewed', { ...reading, ai_review: review }, 'read_by_model', 'Read by two models (claude-haiku-5-5), 2026-11-22; AI reviewed (claude-opus-5-5), 2026-11-23'],
    ['disputed', { ...reading, ai_disputed: { ...review, outcome: 'label_disputed' } }, 'read_by_model', 'Read by two models (claude-haiku-5-5), 2026-11-22; Disputed by the reviewer; awaiting second review'],
    ['agent verified', { ...reading, ai_review: review, witness_match: { witness: 'the Bulaq edition', locator: 'vol. 1 p. 2', method: 'collation', matched_at: '2026-12-01' } }, 'read_by_model',
      'Agent verified: two readers agree, reviewed by claude-opus-5-5, text matched to the Bulaq edition'],
    ['verified by a person', { ...reading, ai_review: review, human_confirmations: [{ reviewer: 'A. Scholar', reviewed_at: '2026-11-24T10:00:00Z', note: 'read', citation: null }] }, 'verified_by_reviewer',
      'Verified by A. Scholar, 2026-11-24'],
  ];
  for (const [name, fix, status, expected] of rows) assert.equal(chainFixNote(fix, status as never), expected, name);
  for (const [, fix, status] of rows.slice(0, 4)) assert.doesNotMatch(chainFixNote(fix, status as never)!, /\bVerified\b/);
});

test('no chain by reading, and the saying heading of a two-saying report', () => {
  assert.equal(noChainNote({ fix_id: 'f', disposition: 'no_chain_by_reading', models: ['claude-haiku-5-5'], runs: 2, decided_at: '2026-11-22T18:00:00Z', awaiting_final_review: true }),
    'No chain is written in this report (read by two models (claude-haiku-5-5), 2026-11-22).');
  assert.equal(sayingHeading({ saying: 2, label: 'Chain of the second saying', opens: 'أنها لم تكن تفعل ذلك' }, 1, 1), 'Chain of the second saying');
  assert.equal(sayingHeading({ saying: 1, label: 'Chain of the first saying', opens: 'أن أبا بكر' }, 2, 2), 'Chain of the first saying, route 2');
});
