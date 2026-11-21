/**
 * Check a JSONL file of claims against the citation standard (docs/review/citations.md).
 * Run: npx tsx reviews/tools/validate-citations.ts <claims.jsonl> [more.jsonl ...]
 * One line per claim: {claim_kind, claim_key, citation_status: "cited" | "not_yet_cited", citations: [...],
 * label?, shown_under?}. Exit 1 on any problem.
 */
import { readFileSync } from 'node:fs';
import { claimKeyProblem, isClaimKind } from '../../src/lib/review/claim-key';
import { citationProblems, MINIMUM_CITATIONS, NOT_YET_CITED_LABEL } from '../../src/lib/review/citation-standard';

/** Problems for one claim line; empty when it meets the standard. */
export function claimLineProblems(raw: unknown): string[] {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return ['line is not a JSON object'];
  const claim = raw as Record<string, unknown>;
  const problems: string[] = [];
  const kind = claim.claim_kind;
  if (!isClaimKind(kind)) return [`unknown claim_kind ${JSON.stringify(kind)}`];
  if (typeof claim.claim_key !== 'string') problems.push('claim_key is required');
  else {
    const keyProblem = claimKeyProblem(kind, claim.claim_key);
    if (keyProblem) problems.push(keyProblem);
  }
  const citations = Array.isArray(claim.citations) ? claim.citations : null;
  if (!citations) return [...problems, 'citations must be a list (empty when not yet cited)'];

  if (claim.citation_status === 'not_yet_cited') {
    if (claim.label !== NOT_YET_CITED_LABEL) problems.push(`an uncited claim must carry the label "${NOT_YET_CITED_LABEL}"`);
    if (typeof claim.shown_under !== 'string' || !claim.shown_under.trim()) {
      problems.push('an uncited claim needs shown_under: the owner decision that lets it be shown, or "not shown"');
    }
  } else if (claim.citation_status === 'cited') {
    const minimum = MINIMUM_CITATIONS[kind] ?? 1;
    if (citations.length < minimum) problems.push(`a cited ${kind} claim needs at least ${minimum} citation${minimum === 1 ? '' : 's'}`);
    citations.forEach((citation, index) => {
      for (const problem of citationProblems(citation, kind)) problems.push(`citations[${index}]: ${problem}`);
    });
  } else problems.push('citation_status must be "cited" or "not_yet_cited"');
  return problems;
}

/** Problems for a whole JSONL text, prefixed with the line number. */
export function claimsFileProblems(text: string): string[] {
  const problems: string[] = [];
  text.split('\n').forEach((line, index) => {
    if (!line.trim()) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch {
      problems.push(`line ${index + 1}: not valid JSON`);
      return;
    }
    for (const problem of claimLineProblems(parsed)) problems.push(`line ${index + 1}: ${problem}`);
  });
  return problems;
}

if (require.main === module) {
  const files = process.argv.slice(2);
  if (files.length === 0) {
    console.error('usage: npx tsx reviews/tools/validate-citations.ts <claims.jsonl> [...]');
    process.exitCode = 2;
  } else {
    let failed = false;
    for (const file of files) {
      const problems = claimsFileProblems(readFileSync(file, 'utf8'));
      if (problems.length === 0) console.log(`ok   ${file}`);
      else {
        failed = true;
        for (const problem of problems.slice(0, 200)) console.error(`FAIL ${file} ${problem}`);
        if (problems.length > 200) console.error(`     ... and ${problems.length - 200} more`);
      }
    }
    process.exitCode = failed ? 1 : 0;
  }
}
