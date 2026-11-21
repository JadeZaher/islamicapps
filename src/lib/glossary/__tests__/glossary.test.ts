/**
 * Glossary integrity: unique slugs, resolvable cross-references, every database enum value accounted for,
 * and docs/glossary.md in step with the data.
 * Run: npx tsx src/lib/glossary/__tests__/glossary.test.ts
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import * as schemaEnums from '../../../db/schema/enums';
import { NOT_USER_FACING_ENUMS, NOT_USER_FACING_VALUES, PLAIN_LANGUAGE_VALUES } from '../enum-coverage';
import { renderGlossaryMarkdown } from '../render-markdown';
import { GLOSSARY_ENTRIES, GLOSSARY_SECTIONS, matchesGlossaryQuery, getGlossaryEntry } from '../terms';

const failures: string[] = [];
function check(name: string, run: () => void): void {
  try {
    run();
    console.log(`ok   ${name}`);
  } catch (error) {
    failures.push(name);
    console.error(`FAIL ${name}\n     ${error instanceof Error ? error.message : String(error)}`);
  }
}

interface PgEnumLike {
  enumName: string;
  enumValues: readonly string[];
}

const databaseEnums: PgEnumLike[] = Object.values(schemaEnums).filter(
  (value): value is typeof value & PgEnumLike =>
    typeof value === 'function' && 'enumName' in value && Array.isArray((value as unknown as PgEnumLike).enumValues),
);

check('slugs are unique and anchor-safe', () => {
  const seen = new Set<string>();
  for (const { slug } of GLOSSARY_ENTRIES) {
    assert.match(slug, /^[a-z0-9]+(-[a-z0-9]+)*$/, `slug "${slug}" is not lowercase ASCII words joined by hyphens`);
    assert.ok(!seen.has(slug), `slug "${slug}" is used twice`);
    assert.ok(!slug.startsWith('section-'), `slug "${slug}" collides with section anchors`);
    seen.add(slug);
  }
});

check('every related reference resolves to another entry', () => {
  const broken = GLOSSARY_ENTRIES.flatMap((entry) =>
    (entry.related ?? [])
      .filter((slug) => !getGlossaryEntry(slug) || slug === entry.slug)
      .map((slug) => `${entry.slug} -> ${slug}`),
  );
  assert.deepEqual(broken, []);
});

check('every entry sits in a declared section and every section has entries', () => {
  const sectionIds = new Set(GLOSSARY_SECTIONS.map((section) => section.id));
  for (const entry of GLOSSARY_ENTRIES) assert.ok(sectionIds.has(entry.section), `${entry.slug} has unknown section`);
  for (const section of GLOSSARY_SECTIONS) {
    assert.ok(GLOSSARY_ENTRIES.some((entry) => entry.section === section.id), `section ${section.id} is empty`);
  }
});

check('the terms other pages link to exist', () => {
  for (const slug of ['kunya', 'preview', 'isnad', 'matn', 'tabaqa', 'not-yet-identified', 'no-assessment-recorded']) {
    assert.ok(getGlossaryEntry(slug), `missing /glossary#${slug}`);
  }
});

check('enums were discovered from the schema', () => {
  assert.ok(databaseEnums.length >= 30, `found only ${databaseEnums.length} enums in src/db/schema/enums.ts`);
});

check('every database enum value has an entry or is listed as not user-facing / plain language', () => {
  const explained = new Map<string, string>();
  for (const entry of GLOSSARY_ENTRIES) for (const value of entry.enumValues ?? []) explained.set(value, entry.slug);

  const unaccounted: string[] = [];
  for (const { enumName, enumValues } of databaseEnums) {
    if (enumName in NOT_USER_FACING_ENUMS) continue;
    for (const value of enumValues) {
      const reference = `${enumName}.${value}` as const;
      if (!explained.has(reference) && !(reference in NOT_USER_FACING_VALUES) && !(reference in PLAIN_LANGUAGE_VALUES)) {
        unaccounted.push(reference);
      }
    }
  }
  assert.deepEqual(unaccounted, [], 'add these to an entry’s enumValues or to src/lib/glossary/enum-coverage.ts');
});

check('every enum reference in the glossary names a real enum value', () => {
  const real = new Set(databaseEnums.flatMap(({ enumName, enumValues }) => enumValues.map((value) => `${enumName}.${value}`)));
  const realEnumNames = new Set(databaseEnums.map(({ enumName }) => enumName));
  const stale = [
    ...GLOSSARY_ENTRIES.flatMap((entry) => (entry.enumValues ?? []).filter((value) => !real.has(value))),
    ...Object.keys(NOT_USER_FACING_VALUES).filter((value) => !real.has(value)),
    ...Object.keys(PLAIN_LANGUAGE_VALUES).filter((value) => !real.has(value)),
    ...Object.keys(NOT_USER_FACING_ENUMS).filter((name) => !realEnumNames.has(name)),
  ];
  assert.deepEqual(stale, []);
});

check('the filter matches transliterations without marks, Arabic, and aliases', () => {
  const cases: Array<[query: string, slug: string]> = [
    ['daif', 'daif'],
    ['ضعيف', 'daif'],
    ['sanad', 'isnad'],
    ['Companion', 'sahabi'],
    ['muanan', 'an'],
  ];
  for (const [query, slug] of cases) {
    assert.ok(matchesGlossaryQuery(getGlossaryEntry(slug)!, query), `"${query}" should find ${slug}`);
  }
  assert.ok(!matchesGlossaryQuery(getGlossaryEntry('kunya')!, 'muwaththaq'), 'unrelated query matched');
});

check('docs/glossary.md is generated from the current data', () => {
  const docPath = path.resolve(process.cwd(), 'docs/glossary.md');
  const current = readFileSync(docPath, 'utf8').replace(/\r\n/g, '\n');
  assert.ok(current === renderGlossaryMarkdown(), 'stale: run npx tsx src/lib/glossary/generate-doc.ts');
});

if (failures.length) {
  console.error(`\n${failures.length} failed`);
  process.exit(1);
}
console.log(`\nAll checks passed (${GLOSSARY_ENTRIES.length} entries, ${databaseEnums.length} enums).`);
