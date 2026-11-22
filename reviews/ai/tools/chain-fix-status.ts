/**
 * Chain-fix counts by state, work and tradition, and the list awaiting final review. Reads the store; writes nothing.
 */
import {
  argumentsOf,
  computeStates,
  DEFAULT_STORE,
  proposalStatuses,
  readApplications,
  readProposalReviews,
  readProposals,
  readReviews,
  readSubmissions,
  storePaths,
} from './chain-fix-lib';

const USAGE = `usage: npx tsx reviews/ai/tools/chain-fix-status.ts [--store <dir>] [--awaiting] [--json]
  --awaiting  list fixes awaiting final review (accepted, not yet confirmed), held and disputed ones
  --proposals list the readers' other proposals (identity, lexicon, text, translation, metadata) with their status
  --json      the full state list as JSON`;

const args = argumentsOf(process.argv.slice(2));
if (args.has('help')) {
  console.log(USAGE);
} else {
  const paths = storePaths(args.get('store') ?? DEFAULT_STORE);
  const states = computeStates(readSubmissions(paths), readReviews(paths), readApplications(paths));
  if (args.has('json')) {
    console.log(JSON.stringify(states, null, 1));
  } else {
    const table = new Map<string, Map<string, number>>();
    for (const state of states) {
      for (const group of ['all', `tradition:${state.tradition}`, `work:${state.work}`]) {
        const row = table.get(group) ?? new Map<string, number>();
        row.set(state.state, (row.get(state.state) ?? 0) + 1);
        table.set(group, row);
      }
    }
    for (const [group, row] of [...table.entries()].sort(([a], [b]) => (a === 'all' ? -1 : b === 'all' ? 1 : a.localeCompare(b)))) {
      console.log(`${group.padEnd(40)} ${[...row.entries()].sort().map(([state, n]) => `${state} ${n}`).join(', ')}`);
    }
    const proposals = proposalStatuses(readProposals(paths), readProposalReviews(paths));
    const byKind = new Map<string, number>();
    for (const entry of proposals) byKind.set(`${entry.proposal.kind} ${entry.status}`, (byKind.get(`${entry.proposal.kind} ${entry.status}`) ?? 0) + 1);
    console.log(`proposals ${proposals.length}${byKind.size ? `: ${[...byKind.entries()].sort().map(([key, n]) => `${key} ${n}`).join(', ')}` : ''}`);
    if (args.has('proposals')) {
      for (const { proposal, status, reviewers } of proposals) {
        const difference = proposal.differences[0];
        console.log(`${status.padEnd(20)} ${proposal.proposal_id} ${proposal.hadith_id} ${proposal.kind} (${proposal.target}): ${proposal.reason}`
          + `${difference ? ` | ours «${difference.ours}» vs ${difference.source} «${difference.theirs}»${difference.url ? ` ${difference.url}` : ''}` : ''}`
          + ` | read by ${proposal.model_id} (${proposal.orchestrator_run_id})${reviewers.length ? ` | reviewed by ${reviewers.join(', ')}` : ''}`);
      }
    }
    if (args.has('awaiting')) {
      for (const state of states.filter((s) => s.state === 'accepted' || s.state === 'disputed' || s.state === 'held')) {
        console.log(`${state.state.padEnd(9)} ${state.fix_id} ${state.hadith_id} [${state.fix_kinds.join(', ')}] read by ${state.models.join(', ')} (${state.runs.length} runs); ${state.why}`);
      }
    }
  }
}
