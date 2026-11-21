export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArabicText } from '@/components/ArabicText';
import { orderPair } from '@/db/queries/correspondence-decisions';
import { getCorrespondencePairForReview, type PairSide } from '@/db/queries/correspondence-review';
import { CORRESPONDENCE_LABEL } from '@/app/hadith/[id]/components/family/labels';
import { ownMatn } from '@/app/hadith/[id]/matn';
import { DecisionForm } from './DecisionForm';

interface PageProps {
  searchParams: Promise<{ a?: string; b?: string }>;
}

function Side({ side, label }: { side: PairSide; label: string }) {
  const matn = ownMatn(side.matn_ar, side.text_ar);
  return (
    <section aria-label={`Report ${label}`} className="min-w-0 border-t border-rule pt-4">
      <h2 className="text-sm font-semibold">
        {label} · {side.tradition} · {side.source_work} {side.hadith_no ?? ''}
      </h2>
      <p className="mt-1 text-xs text-ink-muted">
        {side.record_id} · {side.public ? 'published' : 'not published'} ·{' '}
        <Link href={`/admin/correspondences/family/${encodeURIComponent(side.hadith_id)}`} className="underline-offset-4 hover:underline">
          family preview
        </Link>
      </p>
      {matn && (
        <>
          <p className="mt-4 text-xs uppercase tracking-[0.12em] text-ink-muted">Report text, chain omitted</p>
          <ArabicText as="p" className="mt-1 whitespace-pre-line text-xl leading-[2.1]">{matn}</ArabicText>
        </>
      )}
      <p className="mt-4 text-xs uppercase tracking-[0.12em] text-ink-muted">Text as in the source</p>
      <ArabicText as="p" className="mt-1 whitespace-pre-line text-lg leading-[2] text-ink">{side.text_ar}</ArabicText>
    </section>
  );
}

/** One pair, both Arabic texts side by side, the machine scores, the decision history and the decision form. */
export default async function CorrespondenceReviewPage({ searchParams }: PageProps) {
  const params = await searchParams;
  if (!params.a || !params.b || params.a === params.b) notFound();
  const [a, b] = orderPair(params.a, params.b);
  const pair = await getCorrespondencePairForReview(a, b);
  if (!pair) notFound();
  const live = pair.decisions.find((decision) => !decision.retired_at) ?? null;

  return (
    <div className="space-y-8 text-ink">
      <header>
        <p className="text-sm"><Link href="/admin/correspondences" className="text-ink-muted underline-offset-4 hover:underline">Review queue</Link></p>
        <h1 className="mt-2 text-2xl font-semibold">
          {pair.candidate ? CORRESPONDENCE_LABEL[pair.candidate.relation_class] : 'No machine candidate'}
        </h1>
        {pair.candidate && (
          <p className="mt-1 text-sm text-ink-muted">
            Shared wording {Math.round(pair.candidate.jaccard * 100)}% · {Math.round(pair.candidate.containment * 100)}% of the
            shorter text · {pair.candidate.scope.replace(/_/g, ' ')} · {pair.candidate.shown ? 'shown to readers' : 'below the display threshold'}
          </p>
        )}
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <Side side={pair.a} label="A" />
        <Side side={pair.b} label="B" />
      </div>

      <section aria-labelledby="decision-heading" className="max-w-2xl border-t border-rule pt-6">
        <h2 id="decision-heading" className="text-sm font-semibold">Decision</h2>
        {live && (
          <p className="mt-2 text-sm text-ink-muted">
            Current: {live.decision}
            {live.reviewed_relation ? ` (${live.reviewed_relation.replace(/_/g, ' ')})` : ''} by {live.decided_by.replace(/^curator:/, '')}
            {live.bound ? '' : ' — the texts have changed since; this decision no longer applies until reviewed again'}
          </p>
        )}
        <DecisionForm
          hadithIdA={pair.a.hadith_id}
          hadithIdB={pair.b.hadith_id}
          shaA={pair.a.arabic_sha256}
          shaB={pair.b.arabic_sha256}
          current={live?.bound ? live.decision : null}
        />
        {pair.decisions.length > 1 && (
          <details className="mt-6 text-sm text-ink-muted">
            <summary className="cursor-pointer">Earlier decisions ({pair.decisions.length - (live ? 1 : 0)})</summary>
            <ul className="mt-2 space-y-1">
              {pair.decisions.filter((decision) => decision.retired_at).map((decision) => (
                <li key={decision.id}>
                  {decision.decision} by {decision.decided_by.replace(/^curator:/, '')}, {new Date(decision.decided_at).toISOString().slice(0, 10)}
                  {decision.note ? ` — ${decision.note}` : ''}
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>
    </div>
  );
}
