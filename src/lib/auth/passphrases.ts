/** Curator passphrases: scrypt hashes in CURATOR_PASSPHRASES as JSON `{name: hash}`. Node only. See src/lib/auth/AGENTS.md. */
import { randomBytes, scrypt as scryptCallback, timingSafeEqual, type ScryptOptions } from 'node:crypto';

const SCRYPT_COST = 16384;
const SCRYPT_BLOCK_SIZE = 8;
const SCRYPT_PARALLELISM = 1;
const KEY_LENGTH = 32;
/** Compared against when the name is unknown, so timing does not reveal which names exist. */
const DUMMY_HASH = `scrypt$${SCRYPT_COST}$${SCRYPT_BLOCK_SIZE}$${SCRYPT_PARALLELISM}$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`;

function scrypt(passphrase: string, salt: Buffer, keyLength: number, options: ScryptOptions): Promise<Buffer> {
  return new Promise((resolve, reject) =>
    scryptCallback(passphrase, salt, keyLength, options, (error, key) => (error ? reject(error) : resolve(key))),
  );
}

/** Hash format: `scrypt$N$r$p$<salt base64url>$<key base64url>`. */
export async function hashPassphrase(passphrase: string): Promise<string> {
  const salt = randomBytes(16);
  const key = await scrypt(passphrase, salt, KEY_LENGTH, { N: SCRYPT_COST, r: SCRYPT_BLOCK_SIZE, p: SCRYPT_PARALLELISM });
  return ['scrypt', SCRYPT_COST, SCRYPT_BLOCK_SIZE, SCRYPT_PARALLELISM, salt.toString('base64url'), key.toString('base64url')].join('$');
}

/** Constant-time check of a passphrase against one stored hash; false for any malformed hash. */
export async function verifyPassphrase(passphrase: string, stored: string): Promise<boolean> {
  const [scheme, cost, blockSize, parallelism, salt, key] = stored.split('$');
  if (scheme !== 'scrypt' || !salt || !key) return false;
  const expected = Buffer.from(key, 'base64url');
  if (expected.length === 0) return false;
  try {
    const actual = await scrypt(passphrase, Buffer.from(salt, 'base64url'), expected.length, {
      N: Number(cost),
      r: Number(blockSize),
      p: Number(parallelism),
      maxmem: 64 * 1024 * 1024,
    });
    return timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}

/** Parses CURATOR_PASSPHRASES; an absent or malformed value means no curator can sign in. */
export function curatorPassphraseHashes(): Map<string, string> {
  try {
    const parsed = JSON.parse(process.env.CURATOR_PASSPHRASES ?? '{}') as Record<string, unknown>;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return new Map();
    return new Map(Object.entries(parsed).filter((entry): entry is [string, string] => typeof entry[1] === 'string'));
  } catch {
    return new Map();
  }
}

/** True when `name` is a configured curator and the passphrase matches. Always runs one scrypt. */
export async function checkCuratorPassphrase(name: string, passphrase: string): Promise<boolean> {
  const stored = curatorPassphraseHashes().get(name);
  const matches = await verifyPassphrase(passphrase, stored ?? DUMMY_HASH);
  return Boolean(stored) && matches;
}
