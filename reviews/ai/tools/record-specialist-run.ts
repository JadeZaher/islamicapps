/**
 * Validate a specialist's output against its packet and prompt, then append one review record per verdict to
 * reviews/ai/records/<specialist>/<batch>.jsonl. Prints agreement with any known answers in the manifest.
 * Run: npx tsx reviews/ai/tools/record-specialist-run.ts --packet <packet.json> --output <output.json>
 *        --model <exact model id> --runtime <provider/runtime> --started <UTC> --finished <UTC> --run-id <id> [--check-only]
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { specialistById } from '../../../src/lib/review/procedures';
import { REPOSITORY_ROOT } from './packet-common';
import {
  buildSpecialistRecords,
  packetLeaks,
  promptInfo,
  scoreAgainstKnownAnswers,
  sha256File,
  validateSpecialistOutput,
  type Packet,
  type PacketManifestItem,
  type SpecialistOutput,
} from './specialist-lib';

const argument = (name: string): string | undefined => {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : undefined;
};

function main(): number {
  const packetPath = argument('packet');
  const outputPath = argument('output');
  if (!packetPath || !outputPath) {
    console.error('usage: --packet <packet.json> --output <output.json> --model <id> --runtime <runtime> --started <UTC> --finished <UTC> --run-id <id> [--check-only]');
    return 2;
  }
  const packet = JSON.parse(readFileSync(packetPath, 'utf8')) as Packet;
  const manifestPath = packetPath.replace(/\.json$/, '.manifest.json');
  const manifest = (JSON.parse(readFileSync(manifestPath, 'utf8')) as { items: PacketManifestItem[] }).items;
  const specialist = specialistById(packet.specialist_id);
  if (!specialist) throw new Error(`unknown specialist ${packet.specialist_id}`);
  const promptPath = path.join(REPOSITORY_ROOT, specialist.prompt);
  const prompt = promptInfo(promptPath);

  const raw = readFileSync(outputPath, 'utf8').trim().replace(/^```(?:json)?\s*|\s*```$/g, '');
  let output: unknown;
  try {
    output = JSON.parse(raw);
  } catch {
    console.error('FAIL output is not valid JSON');
    return 1;
  }
  const problems = [
    ...packetLeaks(packet).map((key) => `packet leaks a verdict through key "${key}"`),
    ...(packet.prompt_version === prompt.version ? [] : [`packet was built for prompt ${packet.prompt_version}, prompt file is ${prompt.version}`]),
    ...validateSpecialistOutput(packet, output, prompt.version),
  ];
  if (problems.length > 0) {
    for (const problem of problems) console.error(`FAIL ${problem}`);
    return 1;
  }
  const verdicts = (output as SpecialistOutput).verdicts;
  const score = scoreAgainstKnownAnswers(manifest, verdicts);
  console.log(`ok   ${verdicts.length} verdicts valid; known answers: ${score.agree} of ${score.known} agree`);
  for (const row of score.rows) if (!row.agrees) console.log(`     differs on ${row.claim_id}: expected ${row.expected}, got ${row.got}`);
  if (process.argv.includes('--check-only')) return 0;

  const records = buildSpecialistRecords({
    packet,
    packetPath: path.relative(REPOSITORY_ROOT, path.resolve(packetPath)).replace(/\\/g, '/'),
    packetSha256: sha256File(packetPath),
    manifest,
    output: output as SpecialistOutput,
    outputSha256: sha256File(outputPath),
    prompt: { path: specialist.prompt, version: prompt.version, sha256: prompt.sha256 },
    specialistVersion: specialist.version,
    run: {
      model_id: argument('model') ?? '',
      provider_runtime: argument('runtime') ?? '',
      started_at: argument('started') ?? '',
      finished_at: argument('finished') ?? '',
      orchestrator_run_id: argument('run-id') ?? '',
    },
  });
  const batch = packet.packet_id.split('/')[1];
  const directory = path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'records', packet.specialist_id);
  mkdirSync(directory, { recursive: true });
  const target = path.join(directory, `${batch}.jsonl`);
  const existing = existsSync(target) ? readFileSync(target, 'utf8') : '';
  const fresh = records.filter((record) => !existing.includes(`"record_id":"${String(record.record_id)}"`));
  appendFileSync(target, fresh.map((record) => JSON.stringify(record)).join('\n') + (fresh.length ? '\n' : ''), 'utf8');
  console.log(`appended ${fresh.length} records to ${path.relative(REPOSITORY_ROOT, target)}`);
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
