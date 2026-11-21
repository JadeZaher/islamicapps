/** requireCurator(): the first line of every curation action. Returns the audit actor or throws. */
import 'server-only';
import { cookies } from 'next/headers';
import { curatorActor, SESSION_COOKIE_NAME, verifyCuratorToken } from './session';
import { authEnabled } from './switches';

/** Thrown when a request carries no valid curator session. The message is safe to show. */
export class UnauthorizedError extends Error {
  readonly code = 'unauthorized';
  constructor(message = 'Sign in as a curator to make changes.') {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

/** The signed-in curator's actor string (`curator:<name>`), or null. */
export async function currentCuratorActor(): Promise<string | null> {
  // With AUTH_ENABLED off the session code is never reached.
  if (!authEnabled()) return null;
  const store = await cookies();
  const session = await verifyCuratorToken(store.get(SESSION_COOKIE_NAME)?.value);
  return session ? curatorActor(session.name) : null;
}

/** Returns `curator:<name>` for a valid, unexpired session of a still-configured curator; throws otherwise. */
export async function requireCurator(): Promise<string> {
  if (!authEnabled()) throw new UnauthorizedError('Curation is not enabled on this deployment.');
  const actor = await currentCuratorActor();
  if (!actor) throw new UnauthorizedError();
  return actor;
}
