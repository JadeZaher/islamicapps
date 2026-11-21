/** requireCurator(): the first line of every curation action. Returns the audit actor or throws. */
import 'server-only';
import { cookies } from 'next/headers';
import { curatorActor, SESSION_COOKIE_NAME, verifyCuratorToken } from './session';

/** Thrown when a request carries no valid curator session. The message is safe to show. */
export class UnauthorizedError extends Error {
  readonly code = 'unauthorized';
  constructor() {
    super('Sign in as a curator to make changes.');
    this.name = 'UnauthorizedError';
  }
}

/** The signed-in curator's actor string (`curator:<name>`), or null. */
export async function currentCuratorActor(): Promise<string | null> {
  const store = await cookies();
  const session = await verifyCuratorToken(store.get(SESSION_COOKIE_NAME)?.value);
  return session ? curatorActor(session.name) : null;
}

/** Returns `curator:<name>` for a valid, unexpired session of a still-configured curator; throws otherwise. */
export async function requireCurator(): Promise<string> {
  const actor = await currentCuratorActor();
  if (!actor) throw new UnauthorizedError();
  return actor;
}
