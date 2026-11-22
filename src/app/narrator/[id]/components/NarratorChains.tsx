import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { Pager } from '@/components/archive/ReportList';
import { BasisMark, IDENTITY_BASIS_LABEL, STANDING_BASIS_LABEL } from '@/components/marks';
import { TraditionMark } from '@/components/marks';
import type { Paginated } from '@/db/queries/contracts';
import type { NarratorAppearance } from '@/db/queries/narrator-sources';
import { hadithPath } from '@/lib/hadith-address';
import { WithheldIdentity } from '@/components/archive/WithheldIdentity';

/** Bases that could have made this narrator the standing identity, so a withheld reason is about him. */
const TIER_BASES: ReadonlySet<string> = new Set([
  'source_index_confirmed_by_text', 'source_hadith_kg_confirmed_by_text', 'source_riwayat_confirmed_by_text', 'imam_kunya_convention',
  'named_in_opening_isnad', 'edition_identification',
]);

/**
 * Every public chain position that names this narrator, as its standing identity or as a candidate, in source order and
 * paged. Each row links the report's chains view; the basis says how this narrator was named there.
 */
export function NarratorChains({ narratorId, appearances }: { narratorId: string; appearances: Paginated<NarratorAppearance> }) {
  if (appearances.total === 0) return null;
  const totalPages = Math.max(1, Math.ceil(appearances.total / appearances.pageSize));
  return (
    <section aria-labelledby="chains-heading" className="mb-12 max-w-[var(--measure-wide)]" data-narrator-chains>
      <h2 id="chains-heading" className="section-rule type-label mb-1">
        Named in chains
      </h2>
      <p className="mb-3 type-small text-ink-muted">
        {appearances.total.toLocaleString('en')}
        {appearances.totalCapped ? '+' : ''} chain {appearances.total === 1 ? 'position' : 'positions'}, as an identity or a
        candidate. As written, with how each source names this narrator there.
      </p>
      <ol className="border-t border-rule-strong">
        {appearances.items.map((item) => (
          <li
            key={`${item.hadith_id}:${item.branch}:${item.position}`}
            className="grid grid-cols-1 gap-x-6 gap-y-1 border-b border-rule py-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]"
          >
            <div className="type-small">
              <p className="flex flex-wrap items-center gap-x-2">
                <TraditionMark tradition={item.tradition} decorative size={12} />
                <span className="text-ink-muted">{item.tradition} · {item.work}</span>
              </p>
              <Link href={`${hadithPath(item.hadith_id)}/chains`} className="link-row text-ink">
                {item.reference}
              </Link>
              <span className="text-ink-muted"> · position {item.position + 1}{item.branch > 0 ? `, branch ${item.branch + 1}` : ''}</span>
            </div>
            <div className="type-small">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <ArabicText as="p" variant="inline" className="order-2 ms-auto text-ink">{item.surface_ar}</ArabicText>
                {item.name_latin && <p className="order-1 text-ink">{item.name_latin}</p>}
              </div>
              {item.standing_basis ? (
                <p className="relative ps-[1.125rem] text-ink-muted">
                  <BasisMark basis="source_index_confirmed_by_text" decorative className="absolute start-0 top-[0.3125rem]" />
                  {STANDING_BASIS_LABEL[item.standing_basis] ?? 'machine-reviewed'}
                </p>
              ) : (
                <>
                  {item.bases.map((basis) => (
                    <p key={basis} className="relative ps-[1.125rem] text-ink-muted">
                      <BasisMark basis={basis} decorative className="absolute start-0 top-[0.3125rem]" />
                      candidate: {IDENTITY_BASIS_LABEL[basis] ?? basis}
                    </p>
                  ))}
                  {item.identity_withheld_reason && item.bases.some((basis) => TIER_BASES.has(basis)) && (
                    <WithheldIdentity reason={item.identity_withheld_reason} />
                  )}
                </>
              )}
            </div>
          </li>
        ))}
      </ol>
      <Pager basePath={`/narrator/${encodeURIComponent(narratorId)}`} page={appearances.page} totalPages={totalPages} />
    </section>
  );
}
