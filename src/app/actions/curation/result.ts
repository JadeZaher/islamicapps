/** Result contract for curation actions (see src/app/actions/AGENTS.md §Result contract). Not a 'use server' module. */
import { ZodError } from 'zod';
import { CurationError } from '@/db/queries/write';
import { UnauthorizedError } from '@/lib/auth/require-curator';

export type ActionResult<T> = { ok: true; data: T } | { ok: false; message: string; fieldErrors?: Record<string, string[]> };

function describeValidation(error: ZodError): { message: string; fieldErrors: Record<string, string[]> } {
  const fieldErrors: Record<string, string[]> = {};
  const sentences: string[] = [];
  for (const issue of error.issues) {
    const field = issue.path.map(String).join('.');
    (fieldErrors[field] ??= []).push(issue.message);
    const label = field.split('.').pop()?.replace(/_/g, ' ');
    sentences.push(label ? `${label}: ${issue.message}` : issue.message);
  }
  return { message: sentences.join(' ') || 'The submitted fields are not valid.', fieldErrors };
}

/**
 * Runs an action body: returns `{ ok: true, data }`, turns EXPECTED refusals (validation, curation rules, not found,
 * load in progress, not signed in) into `{ ok: false, message }`, and rethrows everything else so unexpected
 * failures stay failures.
 */
export async function attempt<T>(run: () => Promise<T>): Promise<ActionResult<T>> {
  try {
    return { ok: true, data: await run() };
  } catch (error) {
    if (error instanceof ZodError) return { ok: false, ...describeValidation(error) };
    if (error instanceof CurationError || error instanceof UnauthorizedError) return { ok: false, message: error.message };
    throw error;
  }
}
