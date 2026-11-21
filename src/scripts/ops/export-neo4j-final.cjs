#!/usr/bin/env node
/**
 * Read-only full export of the old Neo4j store to gzipped JSONL. See docs/backups/neo4j-final-dump.md.
 * Usage: NODE_PATH=<repo>/node_modules node export-neo4j-final.cjs <output dir>
 * Reads NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD from the environment (never printed). MATCH/RETURN/SHOW only.
 * Keyset pagination on id(); values keep their Neo4j type (see encode()).
 */
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const neo4j = require('neo4j-driver');

const BATCH = 10000;
const outputDirectory = process.argv[2];
if (!outputDirectory) throw new Error('usage: export-neo4j-final.cjs <output dir>');
fs.mkdirSync(outputDirectory, { recursive: true });

/** Lossless JSON encoding: Integers beyond 2^53 and temporal/spatial values are tagged objects. */
function encode(value) {
  if (value === null || value === undefined) return null;
  if (neo4j.isInt(value)) return value.inSafeRange() ? value.toNumber() : { $int: value.toString() };
  if (Array.isArray(value)) return value.map(encode);
  if (typeof value === 'object') {
    if (neo4j.isDateTime(value) || neo4j.isDate(value) || neo4j.isLocalDateTime(value) || neo4j.isTime(value) ||
        neo4j.isLocalTime(value) || neo4j.isDuration(value)) {
      return { $temporal: value.constructor.name, value: value.toString() };
    }
    if (neo4j.isPoint(value)) return { $point: { srid: encode(value.srid), x: value.x, y: value.y, z: value.z } };
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, encode(v)]));
  }
  return value;
}

function sink(name) {
  const filePath = path.join(outputDirectory, name);
  const gzip = zlib.createGzip({ level: 6 });
  const file = fs.createWriteStream(filePath);
  gzip.pipe(file);
  return {
    filePath,
    write: (line) => gzip.write(line + '\n'),
    close: () => new Promise((resolve) => { file.on('finish', resolve); gzip.end(); }),
  };
}

async function main() {
  const url = process.env.NEO4J_URL;
  const address = /^(bolt|neo4j)(\+s(sc)?)?:\/\//.test(url) ? url : `bolt://${url.includes(':') ? url : url + ':7687'}`;
  const driver = neo4j.driver(address, neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD),
    { maxConnectionLifetime: 30 * 60 * 1000, connectionAcquisitionTimeout: 120000 });
  const read = async (query, params = {}) => {
    const session = driver.session({ defaultAccessMode: neo4j.session.READ });
    try { return (await session.run(query, params)).records; } finally { await session.close(); }
  };
  const started = Date.now();
  for (let attempt = 1; ; attempt++) {
    try { await read('RETURN 1'); break; } catch (error) {
      if (attempt >= 8) throw error;
      console.log(`waiting for the database to wake (attempt ${attempt})`);
      await new Promise((resolve) => setTimeout(resolve, 10000));
    }
  }

  const expected = { labels: {}, types: {} };
  expected.nodes = (await read('MATCH (n) RETURN count(n) AS c'))[0].get('c').toNumber();
  expected.relationships = (await read('MATCH ()-[r]->() RETURN count(r) AS c'))[0].get('c').toNumber();
  for (const r of await read('MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS c')) expected.labels[r.get('l')] = r.get('c').toNumber();
  for (const r of await read('MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c')) expected.types[r.get('t')] = r.get('c').toNumber();
  expected.unlabelled = (await read('MATCH (n) WHERE size(labels(n)) = 0 RETURN count(n) AS c'))[0].get('c').toNumber();
  console.log(`expected: ${expected.nodes} nodes, ${expected.relationships} relationships`);

  const schema = {};
  for (const [key, query] of [['indexes', 'SHOW INDEXES'], ['constraints', 'SHOW CONSTRAINTS']]) {
    try { schema[key] = (await read(query)).map((r) => encode(r.toObject())); } catch (error) { schema[key] = `unavailable: ${error.code}`; }
  }
  const components = (await read('CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition')).map((r) => encode(r.toObject()));

  const exported = { nodes: 0, relationships: 0, labels: {}, types: {}, unlabelled: 0 };
  const nodes = sink('nodes.jsonl.gz');
  let last = -1;
  for (;;) {
    const records = await read(
      'MATCH (n) WHERE id(n) > $last WITH n ORDER BY id(n) LIMIT $batch RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props',
      { last: neo4j.int(last), batch: neo4j.int(BATCH) });
    if (records.length === 0) break;
    for (const r of records) {
      const labels = r.get('labels');
      nodes.write(JSON.stringify({ id: r.get('id').toNumber(), labels, props: encode(r.get('props')) }));
      exported.nodes++;
      if (labels.length === 0) exported.unlabelled++;
      for (const l of labels) exported.labels[l] = (exported.labels[l] || 0) + 1;
      last = r.get('id').toNumber();
    }
    console.log(`  nodes ${exported.nodes}/${expected.nodes} (${Math.round((Date.now() - started) / 1000)}s)`);
  }
  await nodes.close();

  const relationships = sink('relationships.jsonl.gz');
  last = -1;
  for (;;) {
    const records = await read(
      `MATCH (a)-[r]->(b) WHERE id(r) > $last WITH r, a, b ORDER BY id(r) LIMIT $batch
       RETURN id(r) AS id, type(r) AS type, id(a) AS start, id(b) AS end, properties(r) AS props`,
      { last: neo4j.int(last), batch: neo4j.int(BATCH) });
    if (records.length === 0) break;
    for (const r of records) {
      relationships.write(JSON.stringify({ id: r.get('id').toNumber(), type: r.get('type'), start: r.get('start').toNumber(),
        end: r.get('end').toNumber(), props: encode(r.get('props')) }));
      exported.relationships++;
      exported.types[r.get('type')] = (exported.types[r.get('type')] || 0) + 1;
      last = r.get('id').toNumber();
    }
    console.log(`  relationships ${exported.relationships}/${expected.relationships} (${Math.round((Date.now() - started) / 1000)}s)`);
  }
  await relationships.close();
  await driver.close();

  const same = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
  const reconciled = exported.nodes === expected.nodes && exported.relationships === expected.relationships &&
    same(exported.labels, expected.labels) && same(exported.types, expected.types) && exported.unlabelled === expected.unlabelled;
  const manifest = { taken_at: new Date().toISOString(), seconds: Math.round((Date.now() - started) / 1000), components, schema,
    expected, exported, reconciled,
    format: { 'nodes.jsonl.gz': '{id, labels, props}', 'relationships.jsonl.gz': '{id, type, start, end, props}' } };
  fs.writeFileSync(path.join(outputDirectory, 'manifest.json'), JSON.stringify(manifest, null, 1));
  console.log(`reconciled: ${reconciled}; ${exported.nodes} nodes, ${exported.relationships} relationships`);
  process.exit(reconciled ? 0 : 2);
}

main().catch((error) => { console.error('export failed:', error.code || '', error.message.replace(/\/\/[^@\s]*@/g, '//***@')); process.exit(1); });
