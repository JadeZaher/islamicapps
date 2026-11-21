/**
 * Writes src/db/queries/lexicon-held-back.json: the lexicon death years held back from public narrator pages because
 * Ibn Hajar's Taqrib disagrees by three years or more (owner decision 2026-11-21, the "61 values"). Reads the
 * biography-verification comparison file; deterministic; never touches a dataset.
 *
 *   npx tsx src/scripts/db/build-lexicon-held-back.ts
 *
 * See src/db/queries/AGENTS.md §Lexicon on public narrator pages.
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';

const INPUT = 'datasets/hadith-data/diagnostics/biography-verification/lexicon_source_comparisons.jsonl.gz';
const OUTPUT = 'src/db/queries/lexicon-held-back.json';
/** Comparison classes that hold a lexicon death year back (README "Reading": gross, century slip, 3-10 years). */
const HELD_CLASSES = ['gross_conflict', 'differs_by_exactly_100', 'differ_3_10_years'];

interface Comparison {
  scholar_indx: string;
  source: string;
  entry_number: string | null;
  death_year?: { class?: string; source_value?: { verbatim?: string } | null } | null;
}

const bytes = readFileSync(path.resolve(INPUT));
const rows = gunzipSync(bytes)
  .toString('utf8')
  .split('\n')
  .filter((line) => line.trim() !== '')
  .map((line) => JSON.parse(line) as Comparison);

const held = rows
  .filter((row) => row.source === 'ibn_hajar_taqrib' && HELD_CLASSES.includes(row.death_year?.class ?? ''))
  .map((row) => ({
    narrator_id: `narrator:rawi:${row.scholar_indx}`,
    field: 'death_year' as const,
    comparison: row.death_year!.class!,
    taqrib_entry: row.entry_number,
  }))
  .sort((a, b) => a.narrator_id.localeCompare(b.narrator_id, 'en', { numeric: true }));

const output = {
  meaning: 'Lexicon death years withheld from public pages until reviewed: Ibn Hajar, Taqrib al-Tahdhib disagrees by 3+ years.',
  input: INPUT,
  input_sha256: createHash('sha256').update(bytes).digest('hex'),
  rule: `source = ibn_hajar_taqrib and death_year.class in (${HELD_CLASSES.join(', ')})`,
  count: held.length,
  held,
};
writeFileSync(path.resolve(OUTPUT), `${JSON.stringify(output, null, 2)}\n`, 'utf8');
console.log(`Wrote ${OUTPUT}: ${held.length} held-back death years.`);
