/**
 * In-memory, per-instance rate limits (sliding window): sign-in failures and anonymous read actions.
 * Shared through globalThis so the proxy and the route handlers of one process see one store.
 */

export const SIGN_IN_FAILURE_LIMIT = 5;
export const SIGN_IN_WINDOW_MS = 15 * 60 * 1000;
export const READ_LIMIT_PER_MINUTE = 30;
const READ_WINDOW_MS = 60 * 1000;
const MAX_TRACKED_KEYS = 10_000;

type Store = Map<string, number[]>;

const globalStores = globalThis as typeof globalThis & {
  [key: symbol]: { signIn: Store; reads: Store } | undefined;
};
const STORE_KEY = Symbol.for('islamicapps.auth.throttle');

function stores(): { signIn: Store; reads: Store } {
  globalStores[STORE_KEY] ??= { signIn: new Map(), reads: new Map() };
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

/** True once SIGN_IN_FAILURE_LIMIT failures from `ip` fall inside the window: the next attempt gets 429. */
export function isSignInBlocked(ip: string, now = Date.now()): boolean {
  return recent(stores().signIn, ip, SIGN_IN_WINDOW_MS, now).length >= SIGN_IN_FAILURE_LIMIT;
}

export function recordSignInFailure(ip: string, now = Date.now()): void {
  record(stores().signIn, ip, SIGN_IN_WINDOW_MS, now);
}

/** Consumes one anonymous read; false when `ip` has used READ_LIMIT_PER_MINUTE in the last minute. */
export function consumeRead(ip: string, now = Date.now()): boolean {
  const store = stores().reads;
  if (recent(store, ip, READ_WINDOW_MS, now).length >= READ_LIMIT_PER_MINUTE) return false;
  record(store, ip, READ_WINDOW_MS, now);
  return true;
}

/** Client IP from the first X-Forwarded-For hop (Railway's edge sets it), else "unknown". */
export function clientIp(headers: Headers): string {
  return headers.get('x-forwarded-for')?.split(',')[0]?.trim() || headers.get('x-real-ip')?.trim() || 'unknown';
}
