import type { Metadata } from 'next';
import { getSourceAccounting, type SourceAccounting } from '@/db/queries/sources';
import { SOURCES, WORK_CREDITS, type SourceRecord } from '@/lib/sources/registry';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Sources and licences',
  description: 'Every source the archive draws on: what it supplies, its licence and the attribution it requires.',
};

const number = (value: number) => value.toLocaleString('en');

/** What a source accounts for in the loaded data, in one short phrase. */
function accountsFor(record: SourceRecord, accounting: SourceAccounting | null): string {
  if (!accounting) return '—';
  if (record.databaseSourceSlugs.length > 0) {
    const works = accounting.works.filter((work) => record.databaseSourceSlugs.includes(work.sourceSlug));
    const reports = works.reduce((sum, work) => sum + work.reports, 0);
    return `${number(works.length)} ${works.length === 1 ? 'work' : 'works'}, ${number(reports)} reports`;
  }
  const basis = accounting.candidatesByBasis;
  if (record.code === 'K6I') return `${number((basis.source_index ?? 0) + (basis.source_index_confirmed_by_text ?? 0))} identity claims`;
  if (record.code === 'MSD') {
    const names = (basis.name_exact ?? 0) + (basis.name_spelling_fold ?? 0) + (basis.name_kunya_only ?? 0);
    return `${number(accounting.narrators)} narrators, ${number(names)} name matches`;
  }
  if (record.code === 'RIJ') return '6 works (checks only)';
  if (record.code === 'HKG' || record.code === 'RWY') return 'Diagnostics only';
  return '—';
}

/** The sources reference page: a summary table, then one record per source with a stable anchor and short code. */
export default async function SourcesPage() {
  const accounting = await getSourceAccounting().catch((error: unknown) => {
    console.error('Source accounting failed', error instanceof Error ? error.message : error);
    return null;
  });

  return (
    <main className="archive archive-column py-[var(--archive-space-5)]">
      <h1 className="type-h1 border-b-2 border-rule-strong pb-5">Sources and licences</h1>

      <section aria-labelledby="summary" className="mt-[var(--archive-space-5)]">
        <h2 id="summary" className="archive-label mb-[var(--archive-space-3)]">
          Summary
        </h2>
        <div>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Code</th>
                <th scope="col">Source</th>
                <th scope="col">Supplies</th>
                <th scope="col">Licence</th>
                <th scope="col">Accounts for</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((record) => (
                <tr key={record.code}>
                  <td data-label="Code">
                    <a href={`#${record.anchor}`} className="archive-link archive-code">
                      {record.code}
                    </a>
                  </td>
                  <td data-label="Source">{record.name}</td>
                  <td data-label="Supplies" className="text-ink-muted">{record.supplies.join(', ')}</td>
                  <td data-label="Licence" className="text-ink-muted">{record.licence.name}</td>
                  <td data-label="Accounts for" className="text-ink-muted">{accountsFor(record, accounting)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {SOURCES.map((record) => {
        const works = accounting?.works.filter((work) => record.databaseSourceSlugs.includes(work.sourceSlug)) ?? [];
        return (
          <section
            key={record.code}
            id={record.anchor}
            aria-labelledby={`${record.anchor}-title`}
            className="archive-rule mt-[var(--archive-space-5)] scroll-mt-16 pt-[var(--archive-space-4)]"
          >
            <p className="archive-code text-ink">{record.code}</p>
            <h2 id={`${record.anchor}-title`} className="type-h3 mt-1">
              {record.name}
            </h2>
            <dl className="mt-[var(--archive-space-3)] grid grid-cols-1 gap-x-[var(--archive-space-4)] gap-y-[var(--archive-space-2)] text-sm sm:grid-cols-[9rem_1fr]">
              <dt className="text-ink-muted">What we take</dt>
              <dd>{record.took}</dd>
              <dt className="text-ink-muted">Licence</dt>
              <dd>
                {record.licence.url ? (
                  <a href={record.licence.url} className="archive-link" rel="license noopener" target="_blank">
                    {record.licence.name}
                  </a>
                ) : (
                  record.licence.name
                )}
              </dd>
              {record.link && (
                <>
                  <dt className="text-ink-muted">Link</dt>
                  <dd className="break-all">
                    <a href={record.link} className="archive-link" rel="noopener" target="_blank">
                      {record.link}
                    </a>
                  </dd>
                </>
              )}
              <dt className="text-ink-muted">Retrieved</dt>
              <dd>{record.retrieved}</dd>
              {record.requiredWording && (
                <>
                  <dt className="text-ink-muted">Required attribution</dt>
                  <dd className="border-s-2 border-rule ps-4 text-ink-muted">
                    {record.requiredWording}
                  </dd>
                </>
              )}
            </dl>
            {works.length > 0 && (
              <table className="data-table mt-[var(--archive-space-3)]">
                <caption className="sr-only">Works from {record.name}</caption>
                <thead>
                  <tr>
                    <th scope="col">Work</th>
                    <th scope="col">Author</th>
                    <th scope="col">Translation</th>
                    <th scope="col" className="num-cell">Reports</th>
                  </tr>
                </thead>
                <tbody>
                  {works.map((work) => {
                    const credit = WORK_CREDITS[work.sourceWorkId];
                    return (
                      <tr key={work.sourceWorkId}>
                        <td data-label="Work">
                          {work.name}
                          {credit?.openitiUri && (
                            <span className="archive-code block break-all text-ink-muted">{credit.openitiUri}</span>
                          )}
                        </td>
                        <td data-label="Author" className="text-ink-muted">{credit?.author ?? 'Not recorded'}</td>
                        <td data-label="Translation" className="text-ink-muted">{credit?.translator ?? '—'}</td>
                        <td data-label="Reports" className="num-cell">{number(work.reports)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>
        );
      })}
    </main>
  );
}
