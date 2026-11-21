/** Operator CLI: reads a passphrase from stdin and prints its scrypt hash for CURATOR_PASSPHRASES. Never echoes input. */
import { hashPassphrase } from './passphrases';

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString('utf8').replace(/\r?\n$/, '');
}

async function main() {
  const passphrase = await readStdin();
  if (passphrase.length < 12) {
    console.error('Refused: use a passphrase of at least 12 characters.');
    process.exit(1);
  }
  console.log(await hashPassphrase(passphrase));
}

void main();
