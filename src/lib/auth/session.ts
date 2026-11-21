/** Curator session cookie: `{name, expiry}` signed with HMAC-SHA256 via Web Crypto. See src/lib/auth/AGENTS.md. */

export const SESSION_COOKIE_NAME = 'curator_session';
/** Twelve hours (section 10.1). */
export const SESSION_TTL_SECONDS = 12 * 60 * 60;
/** Shorter secrets are refused so a weak key never signs a session. */
const MIN_SECRET_LENGTH = 32;

export interface CuratorSession {
  name: string;
  expiresAt: number;
}

const encoder = new TextEncoder();
const decoder = new TextDecoder();

function toBase64Url(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function fromBase64Url(value: string): Uint8Array<ArrayBuffer> | null {
  if (!/^[A-Za-z0-9_-]*$/.test(value)) return null;
  const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4);
  try {
    const binary = atob(padded);
    const bytes = new Uint8Array(new ArrayBuffer(binary.length));
    for (let index = 0; index < binary.length; index++) bytes[index] = binary.charCodeAt(index);
    return bytes;
  } catch {
    return null;
  }
}

/** The configured signing secret, or null when missing or too short (sessions then fail closed). */
export function sessionSecret(): string | null {
  const secret = process.env.ADMIN_SESSION_SECRET;
  return secret && secret.length >= MIN_SECRET_LENGTH ? secret : null;
}

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
}

/** Signs a session for `name`, valid for SESSION_TTL_SECONDS from `nowSeconds`. */
export async function createSessionToken(name: string, secret: string, nowSeconds = Math.floor(Date.now() / 1000)): Promise<string> {
  const payload = toBase64Url(encoder.encode(JSON.stringify({ n: name, e: nowSeconds + SESSION_TTL_SECONDS })));
  const signature = new Uint8Array(await crypto.subtle.sign('HMAC', await hmacKey(secret), encoder.encode(payload)));
  return `${payload}.${toBase64Url(signature)}`;
}

/** Verifies signature (constant time, via subtle.verify) and expiry; null for anything else. */
export async function verifySessionToken(
  token: string | null | undefined,
  secret: string | null,
  nowSeconds = Math.floor(Date.now() / 1000),
): Promise<CuratorSession | null> {
  if (!token || !secret) return null;
  const [payload, signature, extra] = token.split('.');
  if (!payload || !signature || extra !== undefined) return null;
  const signatureBytes = fromBase64Url(signature);
  if (!signatureBytes) return null;
  const valid = await crypto.subtle.verify('HMAC', await hmacKey(secret), signatureBytes, encoder.encode(payload));
  if (!valid) return null;
  const payloadBytes = fromBase64Url(payload);
  if (!payloadBytes) return null;
  try {
    const parsed = JSON.parse(decoder.decode(payloadBytes)) as { n?: unknown; e?: unknown };
    if (typeof parsed.n !== 'string' || typeof parsed.e !== 'number' || parsed.e <= nowSeconds) return null;
    return { name: parsed.n, expiresAt: parsed.e };
  } catch {
    return null;
  }
}

/** Curator names currently allowed (keys of CURATOR_PASSPHRASES). Removing a name revokes that curator at once. */
export function configuredCuratorNames(): Set<string> {
  try {
    const parsed = JSON.parse(process.env.CURATOR_PASSPHRASES ?? '{}') as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return new Set();
    return new Set(Object.keys(parsed));
  } catch {
    return new Set();
  }
}

/** A verified session whose curator is still configured, or null. */
export async function verifyCuratorToken(token: string | null | undefined): Promise<CuratorSession | null> {
  const session = await verifySessionToken(token, sessionSecret());
  return session && configuredCuratorNames().has(session.name) ? session : null;
}

/** Audit actor for a curator name (section 10.2). */
export function curatorActor(name: string): string {
  return `curator:${name}`;
}
