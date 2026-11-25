/**
 * Flow tests for unified Agent Review tier labels, Agent-supersedes-AI precedence, original prompt + model
 * provenance stamping, and accessible tooltip + /method#chain-tiers link rendering.
 * Run: npx tsx "src/app/hadith/[id]/components/__tests__/chain-tier-labels.test.ts" (not --test: brackets read as glob)
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { ChainAiMark, ChainFixLabel } from '@/db/queries/contracts';
import { ChainReviewIndicator } from '../ChainReviewIndicator';
import {
  CHAIN_VERIFICATION_METHOD_HREF,
  chainFixNote,
  chainFixReviewMeta,
  formatPromptStamp,
  noChainNote,
  noChainReviewMeta,
  sayingHeading,
} from '../chain-structure';

const reading: ChainFixLabel = {
  fix_id: 'chain-fix:x',
  state: 'accepted',
  effect: 'replace_routes',
  models: ['claude-haiku-5-5'],
  runs: 2,
  decided_at: '2026-11-22T18:00:00Z',
  awaiting_final_review: true,
  human_confirmations: [],
  prompt_version: '3.4.0',
  prompt_path: 'datasets/hadith-data/chain-reader/v3_4/prompt-v3_4.md',
  prompt_sha256: 'b63fd535a8cdbdea9294704a494e110523874f846fb1c9be40d4cf26ea8ba959',
};

const legacyAiReview: ChainAiMark = {
  model_id: 'claude-opus-5-5',
  run_id: 'r1',
  at: '2026-11-23T09:00:00Z',
  outcome: 'label_ai_reviewed',
  decision: 'confirm_reading',
  prompt_version: '1.1.0',
  prompt_path: 'datasets/hadith-data/chain-reader/reviewer/prompt-reviewer-v1_1.md',
  prompt_sha256: '1136aec2c975aebd0f4b8f17cf14d6ad1410229c33b97e7d8382b8258cb735f6',
};

const agentReview: ChainAiMark = {
  model_id: 'claude-opus-5-6',
  run_id: 'agent-r2',
  at: '2026-11-25T10:00:00Z',
  outcome: 'label_agent_reviewed',
  decision: 'confirm_reading',
  prompt_version: '2.0.0',
  prompt_path: 'datasets/hadith-data/chain-reader/reviewer/prompt-agent-v2.md',
  prompt_sha256: 'a'.repeat(64),
};

test('unified Agent Review tiers, Agent-supersedes-AI precedence, and "Verified" reserved for a person', () => {
  const rows: [string, ChainFixLabel, string, string][] = [
    ['read by two models', reading, 'read_by_model', 'Read by two models (claude-haiku-5-5), 2026-11-22'],
    [
      'legacy AI review unified under Agent review',
      { ...reading, ai_review: legacyAiReview },
      'read_by_model',
      'Read by two models (claude-haiku-5-5), 2026-11-22; Agent reviewed (claude-opus-5-5), 2026-11-23',
    ],
    [
      'explicit agent_review supersedes legacy ai_review',
      { ...reading, ai_review: legacyAiReview, agent_review: agentReview },
      'read_by_model',
      'Read by two models (claude-haiku-5-5), 2026-11-22; Agent reviewed (claude-opus-5-6), 2026-11-25',
    ],
    [
      'explicit agent_review supersedes legacy ai_disputed',
      { ...reading, ai_disputed: { ...legacyAiReview, outcome: 'label_disputed' }, agent_review: agentReview },
      'read_by_model',
      'Read by two models (claude-haiku-5-5), 2026-11-22; Agent reviewed (claude-opus-5-6), 2026-11-25',
    ],
    [
      'disputed under Agent review',
      { ...reading, ai_disputed: { ...legacyAiReview, outcome: 'label_disputed' } },
      'read_by_model',
      'Read by two models (claude-haiku-5-5), 2026-11-22; Disputed by Agent review; awaiting second review',
    ],
    [
      'corrected under Agent review',
      { ...reading, ai_corrected: { runs: ['r1', 'r2'], models: ['claude-opus-5-5'], at: '2026-11-23T11:00:00Z' } },
      'read_by_model',
      'Corrected by Agent review (claude-opus-5-5, 2 runs), 2026-11-23',
    ],
    [
      'agent verified with witness match (agent_review supersedes ai_review)',
      {
        ...reading,
        ai_review: legacyAiReview,
        agent_review: agentReview,
        witness_match: { witness: 'the Bulaq edition', locator: 'vol. 1 p. 2', method: 'collation', matched_at: '2026-12-01' },
      },
      'read_by_model',
      'Agent verified: two readers agree, reviewed by claude-opus-5-6, text matched to the Bulaq edition',
    ],
    [
      'verified by a person overrides all agent/AI marks',
      {
        ...reading,
        ai_review: legacyAiReview,
        agent_review: agentReview,
        human_confirmations: [{ reviewer: 'A. Scholar', reviewed_at: '2026-11-24T10:00:00Z', note: 'read', citation: null }],
      },
      'verified_by_reviewer',
      'Verified by A. Scholar, 2026-11-24',
    ],
  ];
  for (const [name, fix, status, expected] of rows) assert.equal(chainFixNote(fix, status as never), expected, name);
  for (const [, fix, status] of rows.slice(0, -1)) assert.doesNotMatch(chainFixNote(fix, status as never)!, /\bVerified\b/);
});

test('original prompt & model provenance are stamped, and missing optional fields degrade gracefully', () => {
  const legacyMeta = chainFixReviewMeta({ ...reading, ai_review: legacyAiReview }, 'read_by_model')!;
  assert.equal(legacyMeta.tier, 'agent_reviewed');
  assert.equal(legacyMeta.supersededAiReview, true);
  assert.match(legacyMeta.supersededNote ?? '', /unified under Agent Review/i);
  assert.equal(legacyMeta.methodHref, CHAIN_VERIFICATION_METHOD_HREF);
  assert.equal(legacyMeta.stamps[0].role, 'Historical AI review (superseded)');
  assert.deepEqual(legacyMeta.stamps[0].models, ['claude-opus-5-5']);
  assert.equal(formatPromptStamp(legacyMeta.stamps[0]), 'v1.1.0 · prompt-reviewer-v1_1.md · sha256:1136aec2c975');
  assert.equal(formatPromptStamp(legacyMeta.stamps[1]), 'v3.4.0 · prompt-v3_4.md · sha256:b63fd535a8cd');

  // When explicit agent_review supersedes ai_review, both stamps are preserved in precedence order.
  const supersededMeta = chainFixReviewMeta({ ...reading, ai_review: legacyAiReview, agent_review: agentReview }, 'read_by_model')!;
  assert.equal(supersededMeta.stamps[0].role, 'Agent review');
  assert.deepEqual(supersededMeta.stamps[0].models, ['claude-opus-5-6']);
  assert.equal(supersededMeta.stamps[1].role, 'Historical AI review (superseded)');
  assert.deepEqual(supersededMeta.stamps[1].models, ['claude-opus-5-5']);

  // Missing optional prompt fields on older records or partial fixtures never emit undefined/null.
  const minimalMeta = chainFixReviewMeta(
    {
      fix_id: 'chain-fix:min',
      state: 'accepted',
      effect: 'replace_routes',
      models: ['claude-haiku-5-5'],
      runs: 2,
      decided_at: '2026-11-22T18:00:00Z',
      awaiting_final_review: true,
      human_confirmations: [],
      ai_review: { model_id: 'claude-opus-5-5', run_id: 'r1', at: '2026-11-23T09:00:00Z', outcome: 'label_ai_reviewed', decision: 'confirm_reading' },
    },
    'read_by_model',
  )!;
  assert.equal(formatPromptStamp(minimalMeta.stamps[0]), 'Not recorded');
  assert.equal(formatPromptStamp(minimalMeta.stamps[1]), 'Not recorded');
});

test('tooltip indicator renders accessible trigger, prompt/model stamp, superseded note, and /method#chain-tiers link', () => {
  const meta = chainFixReviewMeta({ ...reading, ai_review: legacyAiReview, agent_review: agentReview }, 'read_by_model')!;
  const html = renderToStaticMarkup(createElement(ChainReviewIndicator, { meta, dataChainFix: reading.fix_id }));

  assert.match(html, /<button type="button"[^>]*aria-expanded="false"[^>]*aria-controls="[^"]+"[^>]*aria-describedby="[^"]+"/);
  assert.match(html, /Agent reviewed \(claude-opus-5-6\), 2026-11-25/);
  assert.match(html, /data-review-tier="agent_reviewed"/);
  assert.match(html, /role="region" aria-label="Review provenance and verification details"/);
  assert.match(html, /claude-opus-5-6/);
  assert.match(html, /v2\.0\.0 · prompt-agent-v2\.md · sha256:aaaaaaaaaaaa/);
  assert.match(html, /Historical AI review \(superseded\)/);
  assert.match(html, /v1\.1\.0 · prompt-reviewer-v1_1\.md · sha256:1136aec2c975/);
  assert.match(html, /<a[^>]*href="\/method#chain-tiers"[^>]*>Verification process &amp; chain tiers →<\/a>/);
});

test('no chain by reading (with Agent/AI review precedence) and saying headings', () => {
  assert.equal(
    noChainNote({
      fix_id: 'f',
      disposition: 'no_chain_by_reading',
      models: ['claude-haiku-5-5'],
      runs: 2,
      decided_at: '2026-11-22T18:00:00Z',
      awaiting_final_review: true,
    }),
    'No chain is written in this report (read by two models (claude-haiku-5-5), 2026-11-22).',
  );
  assert.equal(
    noChainNote({
      fix_id: 'f',
      disposition: 'no_chain_by_reading',
      models: ['claude-haiku-5-5'],
      runs: 2,
      decided_at: '2026-11-22T18:00:00Z',
      awaiting_final_review: true,
      ai_review: legacyAiReview,
      agent_review: agentReview,
    }),
    'No chain is written in this report (read by two models (claude-haiku-5-5), 2026-11-22; Agent reviewed (claude-opus-5-6), 2026-11-25).',
  );
  const noChainMeta = noChainReviewMeta({
    fix_id: 'f',
    disposition: 'no_chain_by_reading',
    models: ['claude-haiku-5-5'],
    runs: 2,
    decided_at: '2026-11-22T18:00:00Z',
    awaiting_final_review: true,
    ai_review: legacyAiReview,
  })!;
  assert.equal(noChainMeta.methodHref, '/method#chain-tiers');
  assert.equal(noChainMeta.supersededAiReview, true);

  assert.equal(sayingHeading({ saying: 2, label: 'Chain of the second saying', opens: 'أنها لم تكن تفعل ذلك' }, 1, 1), 'Chain of the second saying');
  assert.equal(sayingHeading({ saying: 1, label: 'Chain of the first saying', opens: 'أن أبا بكر' }, 2, 2), 'Chain of the first saying, route 2');
});
