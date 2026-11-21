/**
 * In-memory, per-instance rate limits (sliding window): sign-in attempts per address and per curator name, and
 * anonymous read actions. Shared through globalThis so the proxy and the route handlers of one process see one
 * store. See src/lib/auth/AGENTS.md §Throttling.
 */

export const SIGN_IN_FAILURE_LIMIT = 5;
/** Per curator name, across all addresses; higher than the address limit so one attacker cannot cheaply lock a curator out. */
export const SIGN_IN_NAME_LIMIT = 20;
export const SIGN_IN_WINDOW_MS = 15 * 60 * 1000;
export const READ_LIMIT_PER_MINUTE = 30;
const READ_WINDOW_MS = 60 * 1000;
const MAX_TRACKED_KEYS = 10_000;

type Store = Map<string, number[]>;
type Stores = { signIn: Store; signInNames: Store; reads: Store };

const globalStores = globalThis as typeof globalThis & {
  [key: symbol]: Stores | undefined;
};
const STORE_KEY = Symbol.for('islamicapps.auth.throttle.v2');

function stores(): Stores {
  globalStores[STORE_KEY] ??= { signIn: new Map(), signInNames: new Map(), reads: new Map() };
  return globalStores[STORE_KEY]!;
}

function recent(store: Store, key: string, windowMs: number, now: number): number[] {
  const kept = (store.get(key) ?? []).filter((time) => now - time < windowMs);
  if (kept.length === 0) store.delete(key);
  else store.set(key, kept);
  return kept;
}

function record(store: Store, key: string, windowMs: number, now: number): void {
  if (store.size >= MAX_TRACKED_KEYS && !store.has(key)) {
    // Bounded memory: drop the oldest tracked key.
    const oldest = store.keys().next().value;
    if (oldest !== undefined) store.delete(oldest);
  }
  store.set(key, [...recent(store, key, windowMs, now), now]);
}

function forget(store: Store, key: string, time: number): void {
  const kept = store.get(key);
  if (!kept) return;
  const index = kept.indexOf(time);
  if (index >= 0) kept.splice(index, 1);
  if (kept.length === 0) store.delete(key);
}

/** Read-only check for the proxy: true once SIGN_IN_FAILURE_LIMIT attempts from `ip` fall inside the window. */
export function isSignInBlocked(ip: string, now = Date.now()): boolean {
  return recent(stores().signIn, ip, SIGN_IN_WINDOW_MS, now).length >= SIGN_IN_FAILURE_LIMIT;
}

/** One sign-in attempt that has been counted but not yet judged. */
export interface SignInAttempt {
  readonly ip: string;
  readonly ipTime: number;
  nameKey?: string;
}

/**
 * Check-and-count in one synchronous step (no await between), so concurrent requests cannot all pass a stale
 * check: each caller either gets a slot that already counts toward the limit, or null (answer 429).
 */
export function reserveSignInAttempt(ip: string, now = Date.now()): SignInAttempt | null {
  if (isSignInBlocked(ip, now)) return null;
  record(stores().signIn, ip, SIGN_IN_WINDOW_MS, now);
  return { ip, ipTime: now };
}

/** Second synchronous reservation, once the form has been parsed: the same attempt counted against its curator name. */
export function reserveSignInName(attempt: SignInAttempt, name: string, now = Date.now()): boolean {
  const key = name.trim().toLowerCase();
  if (recent(stores().signInNames, key, SIGN_IN_WINDOW_MS, now).length >= SIGN_IN_NAME_LIMIT) return false;
  record(stores().signInNames, key, SIGN_IN_WINDOW_MS, now);
  attempt.nameKey = key;
  return true;
}

/** A correct passphrase: frees this attempt's address slot and clears the name's failures. */
export function confirmSignIn(attempt: SignInAttempt): void {
  forget(stores().signIn, attempt.ip, attempt.ipTime);
  if (attempt.nameKey) stores().signInNames.delete(attempt.nameKey);
}

/** Consumes one anonymous read; false when `ip` has used READ_LIMIT_PER_MINUTE in the last minute. */
export function consumeRead(ip: string, now = Date.now()): boolean {
  const store = stores().reads;
  if (recent(store, ip, READ_WINDOW_MS, now).length >= READ_LIMIT_PER_MINUTE) return false;
  record(store, ip, READ_WINDOW_MS, now);
  return true;
}

const ADDRESS_SHAPE = /^[0-9a-fA-F:.]{2,64}$/;

function validAddress(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed && ADDRESS_SHAPE.test(trimmed) ? trimmed : undefined;
}

function rightmost(forwardedFor: string | null): string | undefined {
  const hops = forwardedFor?.split(',') ?? [];
  return validAddress(hops[hops.length - 1]);
}

/**
 * The client address as the edge saw it, never a value the client chose: the edge header named by
 * CLIENT_IP_HEADER (default `x-real-ip`), else the RIGHT-most X-Forwarded-For hop (the one the nearest proxy
 * appended; earlier hops are client-supplied). See src/lib/auth/AGENTS.md §Client address.
 */
export function clientIp(headers: Headers): string {
  const trusted = (process.env.CLIENT_IP_HEADER || 'x-real-ip').toLowerCase();
  const fromEdge = trusted === 'x-forwarded-for' ? rightmost(headers.get(trusted)) : validAddress(headers.get(trusted) ?? undefined);
  return fromEdge ?? rightmost(headers.get('x-forwarded-for')) ?? 'unknown';
}
