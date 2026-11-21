/** Renders docs/glossary.md from the glossary data; pure, so the doc and the drift test share one output. */
import { NOT_USER_FACING_ENUMS, NOT_USER_FACING_VALUES, PLAIN_LANGUAGE_VALUES } from './enum-coverage';
import { GLOSSARY_ENTRIES, GLOSSARY_SECTIONS, TRANSLITERATION_NOTE, getGlossaryEntry, type GlossaryEntry } from './terms';

function heading(entry: GlossaryEntry): string {
  const parts = [entry.term, entry.english ? `(${entry.english})` : '', entry.arabic ? `· ${entry.arabic}` : ''];
  return parts.filter(Boolean).join(' ');
}

function relatedLinks(entry: GlossaryEntry): string {
  return (entry.related ?? [])
    .map((slug) => `[${getGlossaryEntry(slug)?.term ?? slug}](#${slug})`)
    .join(', ');
}

function renderEntry(entry: GlossaryEntry): string[] {
  const lines = [`<a id="${entry.slug}"></a>`, '', `### ${heading(entry)}`, '', entry.definition, ''];
  if (entry.inArchive) lines.push(`- **In this archive:** ${entry.inArchive}`);
  if (entry.acrossTraditions) lines.push(`- **Across traditions:** ${entry.acrossTraditions}`);
  if (entry.related?.length) lines.push(`- **Related:** ${relatedLinks(entry)}`);
  if (entry.enumValues?.length) lines.push(`- **Data values:** ${entry.enumValues.map((value) => `\`${value}\``).join(', ')}`);
  if (lines.at(-1) !== '') lines.push('');
  return lines;
}

/** The full markdown document, newline-terminated. */
export function renderGlossaryMarkdown(): string {
  const lines: string[] = [
    '# Glossary',
    '',
    '<!-- Generated from src/lib/glossary/terms.ts by `npx tsx src/lib/glossary/generate-doc.ts`. Do not edit by hand. -->',
    '',
    'Definitions of the terms used in the Shura wa Istehsan app, its documentation and its data. The same entries render at `/glossary`.',
    '',
    `**Transliteration.** ${TRANSLITERATION_NOTE}`,
    '',
    '## Sections',
    '',
  ];

  for (const section of GLOSSARY_SECTIONS) {
    const count = GLOSSARY_ENTRIES.filter((entry) => entry.section === section.id).length;
    lines.push(`- [${section.title}](#section-${section.id}) (${count})`);
  }
  lines.push('- [Needs the owner’s review](#owner-review)', '- [Enum values without an entry](#enum-values-without-an-entry)', '');

  for (const section of GLOSSARY_SECTIONS) {
    lines.push(`<a id="section-${section.id}"></a>`, '', `## ${section.title}`, '');
    for (const entry of GLOSSARY_ENTRIES.filter((candidate) => candidate.section === section.id)) {
      lines.push(...renderEntry(entry));
    }
  }

  lines.push('<a id="owner-review"></a>', '', '## Needs the owner’s review', '');
  lines.push('Entries written conservatively where a tradition-specific usage or a data mapping is uncertain.', '');
  for (const entry of GLOSSARY_ENTRIES.filter((candidate) => candidate.ownerReview)) {
    lines.push(`- [${entry.term}](#${entry.slug}): ${entry.ownerReview}`);
  }
  lines.push('');

  lines.push('## Enum values without an entry', '');
  lines.push('Every other value in `src/db/schema/enums.ts` is explained by an entry above (see its “Data values”).', '');
  lines.push('| Value | Kind | Reason |', '| --- | --- | --- |');
  for (const [name, reason] of Object.entries(NOT_USER_FACING_ENUMS)) lines.push(`| \`${name}.*\` | not user-facing | ${reason} |`);
  for (const [value, reason] of Object.entries(NOT_USER_FACING_VALUES)) lines.push(`| \`${value}\` | not user-facing | ${reason} |`);
  for (const [value, reason] of Object.entries(PLAIN_LANGUAGE_VALUES)) lines.push(`| \`${value}\` | plain language | ${reason} |`);
  lines.push('');

  return lines.join('\n');
}
