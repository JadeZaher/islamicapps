/** Projection manifest checks the loader re-runs before any COPY (section 4.3 step 3). */
import { createHash } from 'node:crypto';
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { open } from 'node:fs/promises';
import path from 'node:path';
import { PIPELINE_TABLES } from './tables';

export interface ProjectionFile {
  path: string;
  table: string;
  header: string[];
  row_count: number;
  bytes: number;
  sha256: string;
}

export interface ProjectionManifest {
  projection_version: string;
  target: string;
  stream: string;
  content_sha256: string;
  files: ProjectionFile[];
  counts: Record<string, unknown>;
  /** `source_index` names where source-index candidates come from (the reconciled K6 sidecar). */
  options: { source_index?: string; name_match_traditions?: string[] };
  source_bundle: {
    path: string;
    content_sha256: string;
    bundle_version: string;
    bundle_schema_version: number;
    source_release_state: string;
    import_ready: boolean;
    expected_record_count: number;
  };
  inputs: {
    input_dataset_sha256: string;
    rawis_sha256: string;
    legacy_master: { path: string; sha256: string };
    curation_manifest_sha256: string | null;
    extractor: { version: string; sha256: string };
  };
  release: { release_class: 'release' | 'non_release'; non_release_reason: string | null; attribution_disclaimer: string };
}

export interface VerifiedProjection {
  directory: string;
  manifest: ProjectionManifest;
  /** Table name -> absolute CSV path and manifest entry. */
  files: Map<string, { absolutePath: string; entry: ProjectionFile }>;
}

async function sha256OfFile(filePath: string): Promise<string> {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(filePath)) hash.update(chunk as Buffer);
  return hash.digest('hex');
}

/** First CSV record of a file whose header has no embedded newlines; cells are quoted or bare. */
async function readHeader(filePath: string): Promise<string[]> {
  const handle = await open(filePath, 'r');
  try {
    const buffer = Buffer.alloc(64 * 1024);
    const { bytesRead } = await handle.read(buffer, 0, buffer.length, 0);
    const firstLine = buffer.subarray(0, bytesRead).toString('utf8').split('\n')[0];
    return firstLine.split(',').map((cell) => cell.replace(/^"(.*)"$/, '$1'));
  } finally {
    await handle.close();
  }
}

/** Same binding as neo4j_export/contract.py graph_content_hash: sorted entries, sorted keys, compact JSON. */
export function projectionContentHash(files: ProjectionFile[]): string {
  const bound = [...files]
    .sort((left, right) => (left.path < right.path ? -1 : left.path > right.path ? 1 : 0))
    .map((file) => ({ bytes: file.bytes, header: file.header, path: file.path, row_count: file.row_count, sha256: file.sha256 }));
  return createHash('sha256').update(JSON.stringify(bound), 'utf8').digest('hex');
}

/** Refuses unless every file, header, row count and hash matches, and the source bundle is import-ready. */
export async function verifyProjection(projectionDirectory: string, repositoryRoot = process.cwd()): Promise<VerifiedProjection> {
  const directory = path.resolve(projectionDirectory);
  const manifestPath = path.join(directory, 'canonical', 'manifest.json');
  if (!existsSync(manifestPath)) throw new Error(`no canonical/manifest.json under ${directory}`);
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8')) as ProjectionManifest;
  const problems: string[] = [];
  if (manifest.target !== 'postgres' || manifest.stream !== 'canonical') problems.push('manifest is not a canonical postgres stream');

  const files = new Map<string, { absolutePath: string; entry: ProjectionFile }>();
  for (const entry of manifest.files) {
    const absolutePath = path.join(directory, entry.path);
    if (!existsSync(absolutePath)) {
      problems.push(`${entry.path}: missing`);
      continue;
    }
    if (statSync(absolutePath).size !== entry.bytes) problems.push(`${entry.path}: byte size differs from manifest`);
    else if ((await sha256OfFile(absolutePath)) !== entry.sha256) problems.push(`${entry.path}: SHA-256 differs from manifest`);
    const header = await readHeader(absolutePath);
    if (header.join(',') !== entry.header.join(',')) problems.push(`${entry.path}: header differs from manifest`);
    if (files.has(entry.table)) problems.push(`${entry.table}: listed twice`);
    files.set(entry.table, { absolutePath, entry });
  }
  const expectedTables = PIPELINE_TABLES.map((table) => table.name).sort();
  if ([...files.keys()].sort().join(',') !== expectedTables.join(',')) {
    problems.push(`projection tables ${[...files.keys()].sort()} differ from the load contract ${expectedTables}`);
  }
  if (projectionContentHash(manifest.files) !== manifest.content_sha256) problems.push('content_sha256 does not match the files');

  // The source bundle: validated, import-ready, and the input hash the projection read.
  const bundleDirectory = path.resolve(repositoryRoot, manifest.source_bundle.path);
  const bundleManifestPath = path.join(bundleDirectory, 'manifest.json');
  const reportPath = path.join(bundleDirectory, 'validation_report.json');
  if (!existsSync(bundleManifestPath) || !existsSync(reportPath)) {
    problems.push(`source bundle not found at ${manifest.source_bundle.path}`);
  } else {
    const bundleManifest = JSON.parse(readFileSync(bundleManifestPath, 'utf8')) as {
      content_sha256: string;
      inputs: { role: string; sha256: string }[];
    };
    const report = JSON.parse(readFileSync(reportPath, 'utf8')) as { import_ready: boolean; content_sha256: string };
    if (report.import_ready !== true) problems.push('source bundle validation report is not import_ready');
    if (report.content_sha256 !== manifest.source_bundle.content_sha256) problems.push('validation report names another bundle');
    if (bundleManifest.content_sha256 !== manifest.source_bundle.content_sha256) problems.push('bundle manifest content_sha256 differs');
    const inputHash = bundleManifest.inputs.find((input) => input.role === 'schema_v2_dataset')?.sha256;
    if (inputHash !== manifest.inputs.input_dataset_sha256) problems.push('unified CSV hash differs from the bundle input hash');
  }
  if (!/^[0-9a-f]{64}$/.test(manifest.inputs.legacy_master?.sha256 ?? '')) problems.push('legacy master hash missing');

  if (problems.length > 0) throw new Error(`projection refused:\n  - ${problems.join('\n  - ')}`);
  return { directory, manifest, files };
}
