/** Resolves the request's read visibility from the session. The only producer of curator visibility. */
import 'server-only';
import { cache } from 'react';
import { cookies } from 'next/headers';
import { PUBLIC_VISIBILITY, type CuratorVisibility, type ReadVisibility } from '@/db/queries/visibility';
import { privatePreviewEnabled } from './switches';
import { SESSION_COOKIE_NAME, verifyCuratorToken } from './session';

/**
 * Curator visibility needs both the deployment switch and a verified, still-configured curator session; any other
 * combination (switch off, no cookie, forged, expired or revoked session) is public. See AGENTS.md §Private preview.
 */
export async function visibilityForSessionToken(
  token: string | null | undefined,
  environment: Readonly<Record<string, string | undefined>> = process.env,
): Promise<ReadVisibility> {
  if (!privatePreviewEnabled(environment)) return PUBLIC_VISIBILITY;
  const session = await verifyCuratorToken(token);
  return session ? ('curator' as CuratorVisibility) : PUBLIC_VISIBILITY;
}

/** This request's visibility, resolved once per render from the session cookie. */
export const requestVisibility = cache(async (): Promise<ReadVisibility> => {
  const store = await cookies();
  return visibilityForSessionToken(store.get(SESSION_COOKIE_NAME)?.value);
});
