/**
 * backup-db.ts
 *
 * Streams all nodes and relationships from Neo4j to local JSONL files under
 * .omc/backups/<timestamp>/. Safe to run on a managed/remote Neo4j (uses only Bolt).
 *
 * Output:
 *   .omc/backups/<ts>/nodes.jsonl      — { internalId, labels, props } per line
 *   .omc/backups/<ts>/rels.jsonl       — { internalId, type, startId, endId, props } per line
 *   .omc/backups/<ts>/manifest.json    — counts + timestamp
 *
 * Usage: tsx src/scripts/backup-db.ts
 */

import fs from 'fs';
import path from 'path';
import neo4j from 'neo4j-driver';
import { loadEnv } from './lib/env';
import { runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

const BATCH = 5000;

/** Convert neo4j Integer and DateTime types into JSON-safe primitives. */
function serializeProps(props: Record<string, any>): Record<string, any> {
  const out: Record<string, any> = {};
  for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined) {
      out[k] = v;
    } else if (neo4j.isInt(v)) {
      out[k] = (v as any).toNumber?.() ?? Number(v);
    } else if (neo4j.isDateTime?.(v) || neo4j.isDate?.(v) || neo4j.isLocalDateTime?.(v)) {
      out[k] = v.toString();
    } else if (Array.isArray(v)) {
      out[k] = v.map((x) =>
        neo4j.isInt(x) ? (x as any).toNumber?.() ?? Number(x) : x
      );
    } else {
      out[k] = v;
    }
  }
  return out;
}

async function main() {
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const dir = path.join(process.cwd(), '.omc', 'backups', ts);
  fs.mkdirSync(dir, { recursive: true });

  const nodesPath = path.join(dir, 'nodes.jsonl');
  const relsPath = path.join(dir, 'rels.jsonl');
  const manifestPath = path.join(dir, 'manifest.json');

  console.log(`📦 Backup directory: ${dir}\n`);

  // === Nodes ===
  const nodesStream = fs.createWriteStream(nodesPath, { encoding: 'utf8' });
  let nodeCount = 0;
  let offset = 0;

  console.log('📤 Streaming nodes...');
  while (true) {
    const batch = await runQuery<any>(
      `MATCH (n)
       WITH n ORDER BY id(n)
       SKIP $offset LIMIT $batch
       RETURN id(n) AS internalId, labels(n) AS labels, properties(n) AS props`,
      { offset: neo4j.int(offset), batch: neo4j.int(BATCH) }
    );
    if (batch.length === 0) break;
    for (const row of batch) {
      nodesStream.write(
        JSON.stringify({
          internalId: Number(row.internalId),
          labels: row.labels,
          props: serializeProps(row.props),
        }) + '\n'
      );
      nodeCount++;
    }
    offset += batch.length;
    process.stdout.write(`  ${nodeCount.toLocaleString()} nodes\r`);
    if (batch.length < BATCH) break;
  }
  nodesStream.end();
  await new Promise<void>((r) => nodesStream.on('finish', () => r()));
  console.log(`\n  ✅ ${nodeCount.toLocaleString()} nodes written to nodes.jsonl`);

  // === Relationships ===
  const relsStream = fs.createWriteStream(relsPath, { encoding: 'utf8' });
  let relCount = 0;
  offset = 0;

  console.log('\n📤 Streaming relationships...');
  while (true) {
    const batch = await runQuery<any>(
      `MATCH (a)-[r]->(b)
       WITH r, a, b ORDER BY id(r)
       SKIP $offset LIMIT $batch
       RETURN id(r) AS internalId,
              type(r) AS type,
              id(a) AS startId,
              id(b) AS endId,
              properties(r) AS props`,
      { offset: neo4j.int(offset), batch: neo4j.int(BATCH) }
    );
    if (batch.length === 0) break;
    for (const row of batch) {
      relsStream.write(
        JSON.stringify({
          internalId: Number(row.internalId),
          type: row.type,
          startId: Number(row.startId),
          endId: Number(row.endId),
          props: serializeProps(row.props),
        }) + '\n'
      );
      relCount++;
    }
    offset += batch.length;
    process.stdout.write(`  ${relCount.toLocaleString()} rels\r`);
    if (batch.length < BATCH) break;
  }
  relsStream.end();
  await new Promise<void>((r) => relsStream.on('finish', () => r()));
  console.log(`\n  ✅ ${relCount.toLocaleString()} relationships written to rels.jsonl`);

  // === Manifest ===
  const manifest = {
    timestamp: ts,
    nodes: nodeCount,
    relationships: relCount,
    neo4j_url: process.env.NEO4J_URL,
  };
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8');
  console.log(`\n📄 Manifest: ${manifestPath}`);

  const nodesSize = fs.statSync(nodesPath).size;
  const relsSize = fs.statSync(relsPath).size;
  console.log(`\n📊 Backup sizes:`);
  console.log(`   nodes.jsonl : ${(nodesSize / 1024 / 1024).toFixed(2)} MB`);
  console.log(`   rels.jsonl  : ${(relsSize / 1024 / 1024).toFixed(2)} MB`);
  console.log(`\n✅ Backup complete.\n`);

  await closeDriver();
}

main().catch((err) => {
  console.error('❌ Backup failed:', err);
  process.exit(1);
});
