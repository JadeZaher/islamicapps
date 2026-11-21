/**
 * Writes docs/glossary.md from the glossary data. `--check` exits 1 instead of writing when the doc is out of date.
 * Run: npx tsx src/lib/glossary/generate-doc.ts [--check]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { renderGlossaryMarkdown } from './render-markdown';

/** Run from the repository root, like every other script here. */
const GLOSSARY_DOC_PATH = path.resolve(process.cwd(), 'docs/glossary.md');

function main(): void {
  const expected = renderGlossaryMarkdown();
  if (process.argv.includes('--check')) {
    let current = '';
    try {
      current = readFileSync(GLOSSARY_DOC_PATH, 'utf8').replace(/\r\n/g, '\n');
    } catch {
      // A missing doc is simply out of date.
    }
    if (current !== expected) {
      console.error('docs/glossary.md is out of date: run npx tsx src/lib/glossary/generate-doc.ts');
      process.exit(1);
    }
    console.log('docs/glossary.md is up to date');
    return;
  }
  writeFileSync(GLOSSARY_DOC_PATH, expected, 'utf8');
  console.log(`Wrote ${path.relative(process.cwd(), GLOSSARY_DOC_PATH)}`);
}

main();
