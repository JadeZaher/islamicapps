/**
 * Record one reviewer's final-review decision on a chain fix (many reviewers per fix, each kept), then re-decide the store.
 * Status rule: the latest review per reviewer counts; any human rejection rejects (and removes the fix from the overrides);
 * else a human confirmation confirms (the only state worded "verified"); AI reviews are recorded and never move a fix.
 */
import path from 'node:path';
import {
  appendRecords,
  argumentsOf,
  DEFAULT_OVERRIDES,
  DEFAULT_STORE,
  PROPOSAL_REVIEW_FORMAT,
  proposalStatuses,
  readProposalReviews,
  readProposals,
  readSubmissions,
  type ProposalReview,
  reconcile,
  REVIEW_DECISIONS,
  REVIEW_FORMAT,
  storePaths,
  utcNow,
  type Review,
  type ReviewDecision,
} from './chain-fix-lib';
import { sha256Hex, UTC_TIMESTAMP } from './specialist-lib';

const USAGE = `usage: npx tsx reviews/ai/tools/chain-fix-review.ts --fix <chain-fix:id> --decision confirmed|rejected|superseded
         --reviewer <name or handle> --note "<what you read and why>" [--reviewed-at <UTC>] [--superseded-by <chain-fix:id>]
         [--citation-url <url> | --citation-edition "<work, volume, page>"] [--citation-quote "<exact words>"]
         [--ai --model <model id> --prompt <prompt path> --prompt-sha256 <hash>] [--store <dir>] [--overrides <file>]
  A human review needs a name and a date (default now). An AI review needs --ai, the model and the prompt it ran under.
       npx tsx reviews/ai/tools/chain-fix-review.ts --proposal <reader-proposal:id> --decision accepted|rejected
         --reviewer <name> --note "<what you checked>"
  A proposal (identity, lexicon date, text, translation, metadata) is never applied by a tool: an accepted proposal is work
  for the owner of that data; the review only records the decision.`;

/** Record a human decision on a reader's proposal (reviews/ai/AGENTS.md §Proposals). */
function reviewProposal(args: ReturnType<typeof argumentsOf>, paths: ReturnType<typeof storePaths>): number {
  const proposalId = args.get('proposal') ?? '';
  const decision = args.get('decision') as ProposalReview['decision'];
  const reviewer = (args.get('reviewer') ?? '').trim();
  const note = (args.get('note') ?? '').trim();
  const reviewedAt = args.get('reviewed-at') ?? utcNow();
  const problems: string[] = [];
  if (!readProposals(paths).some((proposal) => proposal.proposal_id === proposalId)) problems.push(`--proposal: ${proposalId || '(missing)'} is not in the store`);
  if (decision !== 'accepted' && decision !== 'rejected') problems.push('--decision: accepted or rejected');
  if (!reviewer) problems.push('--reviewer: the reviewer’s name or handle');
  if (!note) problems.push('--note: say what you checked');
  if (!UTC_TIMESTAMP.test(reviewedAt)) problems.push('--reviewed-at: UTC time like 2026-11-22T14:00:00Z');
  if (args.has('ai')) problems.push('a proposal is decided by a person; AI readers file proposals, they do not decide them');
  if (problems.length > 0) {
    for (const problem of problems) console.error(`FAIL ${problem}`);
    return 1;
  }
  const review: ProposalReview = {
    format: PROPOSAL_REVIEW_FORMAT,
    review_id: `reader-proposal-review:${sha256Hex([proposalId, reviewer, reviewedAt, decision].join('\u001f')).slice(0, 24)}`,
    proposal_id: proposalId,
    reviewer,
    decision,
    note,
    reviewed_at: reviewedAt,
  };
  appendRecords(path.join(paths.proposalReviews, `${reviewer.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'reviewer'}.jsonl`), [review]);
  const now = proposalStatuses(readProposals(paths), readProposalReviews(paths)).find((entry) => entry.proposal.proposal_id === proposalId)!;
  console.log(`ok   recorded ${review.review_id}; ${proposalId} is now ${now.status}`);
  return 0;
}

function main(): number {
  const args = argumentsOf(process.argv.slice(2));
  if (args.has('help')) {
    console.log(USAGE);
    return 0;
  }
  const paths = storePaths(args.get('store') ?? DEFAULT_STORE);
  if (args.has('proposal')) return reviewProposal(args, paths);
  const problems: string[] = [];
  const fixId = args.get('fix') ?? '';
  const decision = args.get('decision') as ReviewDecision;
  const reviewer = (args.get('reviewer') ?? '').trim();
  const note = (args.get('note') ?? '').trim();
  const reviewedAt = args.get('reviewed-at') ?? utcNow();
  const isAi = args.has('ai');
  const submissions = readSubmissions(paths);
  const target = submissions.find((s) => s.fix_id === fixId);
  if (!target) problems.push(`--fix: ${fixId || '(missing)'} is not a fix in the store (see chain-fix-status.ts --awaiting)`);
  if (!REVIEW_DECISIONS.includes(decision)) problems.push(`--decision: one of ${REVIEW_DECISIONS.join(', ')}`);
  if (!reviewer) problems.push('--reviewer: the reviewer’s name or handle (every review is credited to a named reviewer)');
  if (!note) problems.push('--note: say what you read and why you decided so');
  if (!UTC_TIMESTAMP.test(reviewedAt)) problems.push('--reviewed-at: UTC time like 2026-11-22T14:00:00Z');
  const supersededBy = args.get('superseded-by') ?? null;
  if (decision === 'superseded' && !submissions.some((s) => s.fix_id === supersededBy && s.hadith_id === target?.hadith_id)) {
    problems.push('--superseded-by: name another fix of the same report');
  }
  const url = args.get('citation-url');
  const edition = args.get('citation-edition');
  const quote = args.get('citation-quote');
  if ((url || edition) && !quote) problems.push('--citation-quote: a citation needs the exact words relied on');
  if (quote && !url && !edition) problems.push('--citation-quote needs --citation-url or --citation-edition');
  if (url && !/^https?:\/\/\S+$/.test(url)) problems.push('--citation-url: an http or https URL');
  const model = args.get('model') ?? null;
  const prompt = args.get('prompt') ?? null;
  const promptSha256 = args.get('prompt-sha256') ?? null;
  if (isAi && (!model || !/\d/.test(model) || !prompt || !promptSha256 || !/^[0-9a-f]{64}$/.test(promptSha256))) {
    problems.push('--ai needs --model <exact id>, --prompt <path> and --prompt-sha256 <64 hex>');
  }
  if (!isAi && (model || prompt)) problems.push('--model/--prompt are for AI reviews: add --ai, or leave them out for a human review');
  if (problems.length > 0) {
    for (const problem of problems) console.error(`FAIL ${problem}`);
    return 1;
  }
  const review: Review = {
    format: REVIEW_FORMAT,
    review_id: `chain-fix-review:${sha256Hex([fixId, isAi ? 'ai' : 'human', reviewer, reviewedAt, decision].join('\u001f')).slice(0, 24)}`,
    fix_id: fixId,
    hadith_id: target!.hadith_id,
    reviewer_kind: isAi ? 'ai' : 'human',
    reviewer,
    model_id: model,
    prompt_path: prompt,
    prompt_sha256: promptSha256,
    decision,
    superseded_by: supersededBy,
    note,
    citation: url || edition ? { ...(url ? { url } : {}), ...(edition ? { edition_locator: edition } : {}), quote: quote! } : null,
    reviewed_at: reviewedAt,
  };
  const file = path.join(paths.reviews, `${isAi ? 'ai' : 'human'}-${reviewer.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'reviewer'}.jsonl`);
  appendRecords(file, [review]);
  const { states } = reconcile(paths, args.get('overrides') ?? DEFAULT_OVERRIDES, utcNow());
  const now = states.find((state) => state.fix_id === fixId)!;
  console.log(`ok   recorded ${review.review_id}; ${fixId} is now ${now.state} (${now.why})${now.state === 'rejected' && now.database === 'applied' ? '; run the revert for it' : ''}`);
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
