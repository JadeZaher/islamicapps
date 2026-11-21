/**
 * Shared by the packet builders: a read-only production connection, glossary excerpts, neutral ordering and the
 * packet/manifest writer (which refuses a packet that leaks a verdict). See reviews/ai/README.md §Packets.
 */
import { config as loadEnvironment } from 'dotenv';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import postgres from 'postgres';
import { getGlossaryEntry } from '../../../src/lib/glossary/terms';
import { PACKET_FORMAT, packetLeaks, sha256Hex, type Packet, type PacketItem, type PacketManifestItem } from './specialist-lib';

export const REPOSITORY_ROOT = path.resolve(__dirname, '..', '..', '..');

/** Run `work` inside one READ ONLY transaction on the production database; the session is read-only too. */
export async function withProductionReadOnly<T>(work: (sql: postgres.TransactionSql) => Promise<T>): Promise<T> {
  loadEnvironment({ path: path.join(REPOSITORY_ROOT, '.env.local'), quiet: true });
  const url = process.env.DATABASE_URL_PRODUCTION;
  if (!url) throw new Error('DATABASE_URL_PRODUCTION is not set in .env.local');
  const sql = postgres(url, {
    max: 1,
    connect_timeout: 15,
    idle_timeout: 5,
    prepare: false,
    onnotice: () => {},
    connection: { default_transaction_read_only: true, statement_timeout: 90_000, application_name: 'review-packet-builder' },
  });
  try {
    return (await sql.begin('read only', work)) as T;
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/** Glossary definitions by slug, as the reviewer sees them (term and the plain definition only). */
export function glossaryExcerpt(slugs: readonly string[]): { term: string; definition: string }[] {
  return slugs.map((slug) => {
    const entry = getGlossaryEntry(slug);
    if (!entry) throw new Error(`unknown glossary slug ${slug}`);
    return { term: entry.arabic ? `${entry.term} (${entry.arabic})` : entry.term, definition: entry.definition };
  });
}

/** A stable order that carries no meaning: by SHA-256 of a salt and the value. */
export function neutralOrder<T>(values: readonly T[], keyOf: (value: T) => string, salt: string): T[] {
  return [...values].sort((a, b) => sha256Hex(`${salt}\u001f${keyOf(a)}`).localeCompare(sha256Hex(`${salt}\u001f${keyOf(b)}`)));
}

export function chunk<T>(values: readonly T[], size: number): T[][] {
  const out: T[][] = [];
  for (let index = 0; index < values.length; index += size) out.push(values.slice(index, index + size));
  return out;
}

export interface BuiltPacket {
  items: PacketItem[];
  manifest: PacketManifestItem[];
}

/**
 * Write packet-NN.json (what the reviewer sees) and packet-NN.manifest.json (what it must never see) under
 * reviews/ai/packets/<specialist>/<batch>/, plus batch.json describing how the batch was drawn.
 */
export function writeBatch(input: {
  specialistId: string;
  promptVersion: string;
  batch: string;
  packets: BuiltPacket[];
  glossary: { term: string; definition: string }[];
  batchInfo: Record<string, unknown>;
}): string[] {
  const directory = path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'packets', input.specialistId, input.batch);
  mkdirSync(directory, { recursive: true });
  const written: string[] = [];
  input.packets.forEach((built, index) => {
    const name = `packet-${String(index + 1).padStart(2, '0')}`;
    const packet: Packet = {
      format: PACKET_FORMAT,
      packet_id: `${input.specialistId}/${input.batch}/${name}`,
      specialist_id: input.specialistId,
      prompt_version: input.promptVersion,
      instructions: 'Answer every claim_id listed in items. Use only this file.',
      items: built.items,
      glossary: input.glossary,
    };
    const leaks = packetLeaks(packet);
    if (leaks.length > 0) throw new Error(`${name} would leak a verdict through keys: ${leaks.join(', ')}`);
    const packetPath = path.join(directory, `${name}.json`);
    writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`, 'utf8');
    writeFileSync(
      path.join(directory, `${name}.manifest.json`),
      `${JSON.stringify({ packet_id: packet.packet_id, do_not_show_to_reviewer: true, items: built.manifest }, null, 2)}\n`,
      'utf8',
    );
    written.push(path.relative(REPOSITORY_ROOT, packetPath).replace(/\\/g, '/'));
  });
  writeFileSync(path.join(directory, 'batch.json'), `${JSON.stringify({ ...input.batchInfo, packets: written }, null, 2)}\n`, 'utf8');
  return written;
}
