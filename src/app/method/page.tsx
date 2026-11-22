import type { Metadata } from 'next';
import Link from 'next/link';
import { Fragment, type ReactNode } from 'react';
import { ArabicText } from '@/components/ArabicText';
import { SourceCredit } from '@/components/archive/SourceCredit';
import { glossaryHref } from '@/lib/glossary/terms';
import {
  AI_REVIEW_MEANING,
  METHOD_SECTIONS,
  REVIEW_KIND_LABEL,
  SPECIALISTS,
  STATUS_LABEL,
  type RuleProcedure,
  type Specialist,
} from '@/lib/review/procedures';
import { PERSPECTIVE_ASPECTS, PERSPECTIVE_ROW_KINDS } from '@/lib/review/perspectives';
import { CHAIN_TIERS, getChainTierCoverage, type ChainTier } from '@/db/queries/chain-tiers';
import { CHAIN_TIER_WORDING } from '@/lib/review/procedures';

export const metadata: Metadata = {
  title: 'Method',
  description: 'What “AI-reviewed” means for each kind of claim: the rule or specialist reviewer, its evidence, its measured accuracy and its limits.',
};

const REPOSITORY = 'https://github.com/JadeZaher/islamicapps/blob/main/';
const ARABIC_RUN = /([؀-ۿ][؀-ۿ\sً-ْ]*[؀-ۿ])/;

/** Plain text with every Arabic run set through ArabicText inside a bidi isolate. */
function WithArabic({ text }: { text: string }) {
  return (
    <>
      {text.split(ARABIC_RUN).map((part, index) =>
        index % 2 === 1 ? (
          <ArabicText key={index} as="bdi" variant="inline">
            {part}
          </ArabicText>
        ) : (
          <Fragment key={index}>{part}</Fragment>
        ),
      )}
    </>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 border-t border-rule py-3 sm:grid-cols-[10rem_1fr] sm:gap-6">
      <dt className="archive-label">{label}</dt>
      <dd className="type-small">{children}</dd>
    </div>
  );
}

function ProcedureEntry({ procedure }: { procedure: RuleProcedure }) {
  return (
    <article id={procedure.id} aria-labelledby={`${procedure.id}-title`} className="mt-[var(--archive-space-4)] scroll-mt-16">
      <h3 id={`${procedure.id}-title`} className="type-h3">
        {procedure.title}
      </h3>
      <p className="type-small text-ink-muted mt-1">
        {REVIEW_KIND_LABEL.rule} · <span className="archive-code">{procedure.id}</span> {procedure.version} · {STATUS_LABEL[procedure.status]}
      </p>
      <dl className="mt-3">
        <Row label="Rule">
          <WithArabic text={procedure.rule} />
        </Row>
        <Row label="Evidence">
          <ul className="list-none p-0">
            {procedure.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Row>
        <Row label="Measured">
          {procedure.measured ? (
            <>
              <p>{procedure.measured.summary}</p>
              <p className="text-ink-muted mt-1">
                {procedure.measured.sample} <span className="archive-code">{procedure.measured.where}</span>
              </p>
            </>
          ) : (
            <p>
              <span className="text-ink">No measured accuracy.</span> {procedure.unmeasured}
            </p>
          )}
        </Row>
        <Row label="Fails when">
          <ul className="list-none p-0">
            {procedure.failureModes.map((item) => (
              <li key={item}>
                <WithArabic text={item} />
              </li>
            ))}
          </ul>
        </Row>
        <Row label="Reader sees">“{procedure.readerLabel}”</Row>
        {procedure.excluded && procedure.excluded.length > 0 && (
          <Row label="Excluded">
            <ul className="list-none p-0">
              {procedure.excluded.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Row>
        )}
        <Row label="Credited">
          {procedure.sources.map((code) => (
            <SourceCredit key={code} code={code} />
          ))}
        </Row>
        <Row label="Terms">
          {procedure.glossary.map((slug, index) => (
            <Fragment key={slug}>
              {index > 0 && ', '}
              <Link href={glossaryHref(slug)} className="link-term">
                {slug.replace(/-/g, ' ')}
              </Link>
            </Fragment>
          ))}
        </Row>
      </dl>
    </article>
  );
}

function SpecialistEntry({ specialist }: { specialist: Specialist }) {
  const anchor = `specialist-${specialist.id}`;
  return (
    <article id={anchor} aria-labelledby={`${anchor}-title`} className="mt-[var(--archive-space-4)] scroll-mt-16">
      <h3 id={`${anchor}-title`} className="type-h3">
        {specialist.title}
      </h3>
      <p className="type-small text-ink-muted mt-1">
        {REVIEW_KIND_LABEL.specialist} · <span className="archive-code">{specialist.id}</span> {specialist.version} · {STATUS_LABEL[specialist.status]}
      </p>
      <dl className="mt-3">
        <Row label="Question">{specialist.question}</Row>
        <Row label="System prompt">
          <a href={`${REPOSITORY}${specialist.prompt}`} className="link-prose">
            {specialist.prompt}
          </a>
          <span className="text-ink-muted"> · the full instructions the reviewer was given</span>
        </Row>
        <Row label="Sees only">
          <ul className="list-none p-0">
            {specialist.packet.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="text-ink-muted mt-1">Never the pipeline’s scores, basis or expected answer.</p>
        </Row>
        <Row label="Model">
          <span className="archive-code">{specialist.recommendedModel}</span> (recommended) · {specialist.modelReason}
          {specialist.notThisModel.length > 0 && <p className="text-ink-muted mt-1">Not: {specialist.notThisModel.join('; ')}</p>}
        </Row>
        <Row label="Agreement">
          {specialist.measured ? specialist.measured.summary : <span>No measured agreement yet. {specialist.unmeasured}</span>}
        </Row>
      </dl>
    </article>
  );
}

/** What "AI-reviewed" means, kind by kind. Every AI-review label in the app links to an anchor here. */
/** Live counts: the coverage table reads the database on every request. */
export const dynamic = 'force-dynamic';

const TIER_LABEL: Record<ChainTier, string> = {
  rule_uncertain: 'Rule-built, uncertain',
  rule_checked: 'Rule-built, checked',
  read_by_two_models: 'Read by two models',
  ai_reviewed: 'AI reviewed',
  agent_verified: 'Agent verified',
  verified_by_person: 'Verified by a person',
  no_chain_by_reading: 'No chain, by reading (reports)',
};
const TRADITION_LABEL: Record<string, string> = { ibadi: 'Ibadi', imami: 'Imami', sunni: 'Sunni', zaydi: 'Zaydi' };

/** Chains by tier, overall and per tradition, read live from the public views (src/db/queries/chain-tiers.ts). */
async function ChainTierTable() {
  let coverage: Awaited<ReturnType<typeof getChainTierCoverage>>;
  try {
    coverage = await getChainTierCoverage();
  } catch {
    return <p className="type-small text-ink-muted mt-[var(--archive-space-3)]">The counts could not be read just now.</p>;
  }
  const columns = ['all', ...coverage.traditions];
  return (
    <table className="data-table mt-[var(--archive-space-3)]" aria-describedby="chain-tiers-intro">
      <thead>
        <tr>
          <th scope="col">Tier</th>
          {columns.map((column) => (
            <th key={column} scope="col" className="text-right">{column === 'all' ? 'All' : TRADITION_LABEL[column] ?? column}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {CHAIN_TIERS.map((tier) => (
          <tr key={tier} data-tier={tier}>
            <th scope="row">{TIER_LABEL[tier]}</th>
            {columns.map((column) => (
              <td key={column} className="text-right tabular-nums">{(coverage.counts[column]?.[tier] ?? 0).toLocaleString('en')}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MethodPage() {
  return (
    <main className="archive archive-column py-[var(--archive-space-5)]">
      <h1 className="type-h1 border-b-2 border-rule-strong pb-5">Method</h1>

      <section aria-labelledby="meaning" className="mt-[var(--archive-space-5)]">
        <h2 id="meaning" className="archive-label mb-[var(--archive-space-3)]">
          What AI-reviewed means
        </h2>
        <p className="type-reading max-w-[var(--measure-reading)]">{AI_REVIEW_MEANING}</p>
        <dl className="mt-[var(--archive-space-4)]">
          <Row label={REVIEW_KIND_LABEL.rule}>Deterministic code, recorded with its procedure id, version and code hash. No model is involved.</Row>
          <Row label={REVIEW_KIND_LABEL.specialist}>
            A model working as a specialist reviewer from a saved system prompt. It sees only a self-contained packet of evidence, never how the claim was produced or what answer is expected. Each review records the exact model, the prompt’s hash, the packet’s hash, and its start and finish times in UTC.
          </Row>
          <Row label="Human reviews">
            Listed separately, one per reviewer, each with the reviewer’s name, stance and citations. They add to, contest or annotate a claim; they are never counted as AI review and never hidden.
          </Row>
        </dl>
        <nav aria-label="Kinds of claim" className="mt-[var(--archive-space-4)] type-small">
          {METHOD_SECTIONS.map((section, index) => (
            <Fragment key={section.id}>
              {index > 0 && <span className="text-ink-muted"> · </span>}
              <a href={`#${section.id}`} className="link-row">
                {section.title}
              </a>
            </Fragment>
          ))}
          <span className="text-ink-muted"> · </span>
          <a href="#perspectives" className="link-row">
            Perspectives
          </a>
        </nav>
      </section>

      {METHOD_SECTIONS.map((section) => (
        <section key={section.id} id={section.id} aria-labelledby={`${section.id}-heading`} className="archive-rule mt-[var(--archive-space-6)] scroll-mt-16 pt-[var(--archive-space-4)]">
          <h2 id={`${section.id}-heading`} className="type-h2">
            {section.title}
          </h2>
          <p className="type-small text-ink-muted mt-1">{section.intro}</p>
          {section.procedures.map((procedure) => (
            <ProcedureEntry key={procedure.id} procedure={procedure} />
          ))}
          {section.specialistIds.map((id) => {
            const specialist = SPECIALISTS.find((entry) => entry.id === id);
            return specialist ? <SpecialistEntry key={id} specialist={specialist} /> : null;
          })}
        </section>
      ))}

      <section id="chain-tiers" aria-labelledby="chain-tiers-heading" className="archive-rule mt-[var(--archive-space-6)] scroll-mt-16 pt-[var(--archive-space-4)]">
        <h2 id="chain-tiers-heading" className="type-h2">
          How far each chain has been checked
        </h2>
        <p id="chain-tiers-intro" className="type-small text-ink-muted mt-1">
          The goal is that every chain is read by two independent models that agree, reviewed against the Arabic by a stronger model, and matched to a primary witness of the text. “Verified” is kept for a named person’s decision. Counts are of public chains, live.
        </p>
        <ul className="type-small mt-[var(--archive-space-2)] list-disc pl-5">
          {CHAIN_TIER_WORDING.map((line) => (
            <li key={line}>“{line}”</li>
          ))}
        </ul>
        <ChainTierTable />
      </section>

      <section id="perspectives" aria-labelledby="perspectives-heading" className="archive-rule mt-[var(--archive-space-6)] scroll-mt-16 pt-[var(--archive-space-4)]">
        <h2 id="perspectives-heading" className="type-h2">
          Perspectives
        </h2>
        <p className="type-small text-ink-muted mt-1">
          A narrator or a report is shown as a matrix: one row per source of a view, grouped by tradition in alphabetical order, one column per aspect. AI and human reviews are further rows, marked by kind. Nothing is averaged across rows.
        </p>
        <table className="data-table mt-[var(--archive-space-3)]">
          <thead>
            <tr>
              <th scope="col">Row kind</th>
              <th scope="col">Shown as</th>
            </tr>
          </thead>
          <tbody>
            {PERSPECTIVE_ROW_KINDS.map((row) => (
              <tr key={row.kind}>
                <td data-label="Row kind">{row.label}</td>
                <td data-label="Shown as" className="text-ink-muted">
                  {row.shownAs}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="type-small mt-[var(--archive-space-3)]">
          <span className="text-ink">Aspects of a narrator:</span>{' '}
          <span className="text-ink-muted">{PERSPECTIVE_ASPECTS.narrator.map((aspect) => aspect.label).join(', ')}.</span>
        </p>
        <p className="type-small mt-1">
          <span className="text-ink">Aspects of a report:</span>{' '}
          <span className="text-ink-muted">{PERSPECTIVE_ASPECTS.report.map((aspect) => aspect.label).join(', ')}.</span>
        </p>
      </section>
    </main>
  );
}
