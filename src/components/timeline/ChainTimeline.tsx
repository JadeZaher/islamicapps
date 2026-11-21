/**
 * Chains of one report family on one Hijri axis: one row per transmitter (earliest first), era bands, event ticks,
 * then the chronological notes, the place trail and the full list (the accessible equivalent of the figure).
 * Presentational and server-rendered. See src/components/AGENTS.md §Time and place.
 */
import Link from 'next/link';
import type { ChainFamilyTimeline, ChainTimeline as ChainRows, ChainTransmitter, EpochEntry } from '@/db/queries/timeline-contracts';
import { formatInterval } from '@/db/queries/timeline-rules';
import { ArabicText } from '@/components/ArabicText';
import { GlossaryTerm } from '@/components/GlossaryTerm';
import { NarratorName } from '@/components/NarratorName';
import { BasisLabel } from './BasisLabel';
import { buildScale } from './scale';
import { AxisRow, EpochLane, EventLane, Legend, LifeMarks } from './TimelineGeometry';
import { GenerationFacts, LifespanFacts, PlaceFacts, shortLife } from './TimelineFacts';
import styles from './timeline.module.css';

function identitySentence(transmitter: ChainTransmitter): string {
  switch (transmitter.identity) {
    case 'verified':
      return 'Identity verified';
    case 'single_candidate':
      return `Identity not verified: ${transmitter.identity_bases.join(', ')}`;
    case 'candidates_differ':
      return `Sources name different people (${transmitter.candidate_names.map((candidate) => candidate.name).join('; ')}); no dates are drawn`;
    default:
      return 'Not yet identified';
  }
}

function trackFallback(transmitter: ChainTransmitter): string {
  if (transmitter.identity === 'unidentified') return 'Not yet identified';
  if (transmitter.identity === 'candidates_differ') return 'Sources name different people';
  return transmitter.generation.length > 0 ? 'No dates recorded · generation only' : 'Not recorded';
}

function chainTitle(family: ChainFamilyTimeline, chain: ChainRows, branches: number): string {
  const work = family.source_works[chain.hadith_id] ?? chain.hadith_id;
  const tradition = family.traditions[chain.hadith_id];
  const branch = branches > 1 ? ` · chain ${chain.branch + 1} of ${branches}` : '';
  return `${work}${tradition ? ` (${tradition})` : ''}${branch}`;
}

/** Shared top-level eras, shared sub-periods, then the finest eras of each tradition present. */
function epochLanes(family: ChainFamilyTimeline): Array<{ label: string; epochs: EpochEntry[] }> {
  const parents = new Set(family.epochs.map((epoch) => epoch.parent_id).filter(Boolean));
  const lanes = [
    { label: 'Eras', epochs: family.epochs.filter((epoch) => !epoch.tradition_context && !epoch.parent_id) },
    { label: 'Sub-periods', epochs: family.epochs.filter((epoch) => !epoch.tradition_context && epoch.parent_id) },
  ];
  const traditions = [...new Set(Object.values(family.traditions).filter((tradition): tradition is string => Boolean(tradition)))].sort();
  for (const tradition of traditions) {
    lanes.push({
      label: `${tradition} reckoning`,
      epochs: family.epochs.filter((epoch) => epoch.tradition_context === tradition && !parents.has(epoch.id)),
    });
  }
  return lanes.filter((lane) => lane.epochs.length > 0);
}

function TransmitterName({ transmitter }: { transmitter: ChainTransmitter }) {
  const name = transmitter.name_en || transmitter.name_ar ? (
    <NarratorName english={transmitter.name_en} arabic={transmitter.name_ar} latinClassName="font-medium" arabicClassName="text-base" />
  ) : (
    <ArabicText>{transmitter.surface_ar}</ArabicText>
  );
  return transmitter.narrator_id ? (
    <Link href={`/narrator/${encodeURIComponent(transmitter.narrator_id)}`} className="underline decoration-[var(--timeline-rule)] underline-offset-4 hover:decoration-[var(--timeline-ink)]">
      {name}
    </Link>
  ) : (
    name
  );
}

export function ChainTimeline({ family, headingId = 'chain-timeline-heading' }: { family: ChainFamilyTimeline; headingId?: string }) {
  const branchCount = new Map<string, number>();
  for (const chain of family.chains) branchCount.set(chain.hadith_id, (branchCount.get(chain.hadith_id) ?? 0) + 1);
  const scale = family.span ? buildScale(family.span) : null;
  const gaps = family.chains.flatMap((chain) => chain.gaps.map((gap) => ({ chain, gap })));
  const axisEntries = [...family.epochs, ...family.events];
  // One basis for every era and event (today: all seed) is stated once above the list, not on every row.
  const sharedAxisBasis = axisEntries.length > 0 && axisEntries.every((entry) => entry.basis === axisEntries[0].basis) ? axisEntries[0].basis : undefined;

  return (
    <section className={styles.root} aria-labelledby={headingId}>
      <h2 id={headingId} className={styles.heading}>Chains through time and place</h2>
      <p className={styles.note}>
        Hijri years, earliest transmitter first. Each date, generation and place shows where it comes from.
        {family.audience === 'review' && ' Reviewer view: unreviewed data is included and labelled.'}
      </p>

      {family.chains.length === 0 ? (
        <p className={styles.note}>No chain is recorded for this report.</p>
      ) : scale ? (
        <figure className={styles.figure} aria-label="Timeline of the chains; the same information follows as lists.">
          <AxisRow scale={scale} />
          {epochLanes(family).map((lane) => <EpochLane key={lane.label} label={lane.label} epochs={lane.epochs} scale={scale} />)}
          <EventLane events={family.events} scale={scale} />
          {family.chains.map((chain) => (
            <div key={chain.chain_id} role="presentation">
              <div className={styles.row} aria-hidden="true">
                <span className={styles.groupLabel}>{chainTitle(family, chain, branchCount.get(chain.hadith_id) ?? 1)}</span>
              </div>
              {chain.transmitters.map((transmitter) => (
                <div key={transmitter.mention_id} className={`${styles.row} ${styles.rowTall}`} aria-hidden="true">
                  <span className={styles.label}>
                    {transmitter.name_en || transmitter.name_ar || transmitter.surface_ar}
                    {shortLife(transmitter.lifespan) && <span className={styles.basis}> · {shortLife(transmitter.lifespan)}</span>}
                  </span>
                  <div className={styles.track}>
                    <LifeMarks lifespan={transmitter.lifespan} scale={scale} fallback={trackFallback(transmitter)} />
                  </div>
                </div>
              ))}
            </div>
          ))}
          <Legend />
        </figure>
      ) : (
        <p className={styles.note}>No transmitter in these chains has a recorded date{family.audience === 'public' ? ' that has been reviewed and cited' : ''}.</p>
      )}

      {gaps.length > 0 && (
        <>
          <h3 className={styles.subheading}><GlossaryTerm slug="chronological-gap">Chronological notes</GlossaryTerm></h3>
          <p className={styles.note}>Where recorded dates or generations of consecutive transmitters do not meet. This is information about the records, not a ruling on the chain.</p>
          <ul className={styles.list}>
            {gaps.map(({ chain, gap }) => (
              <li key={`${chain.chain_id}:${gap.kind}:${gap.student_position}`} className={styles.listItem}>
                <span className={styles.listYear}>Positions {gap.teacher_position + 1}–{gap.student_position + 1}</span>
                <span className={styles.gap}>
                  {gap.statement}
                  <span className={styles.basis}> {chainTitle(family, chain, branchCount.get(chain.hadith_id) ?? 1)}</span>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {family.chains.some((chain) => chain.transmitters.some((transmitter) => transmitter.places.length > 0)) && (
        <>
          <h3 className={styles.subheading}>Place trail</h3>
          {family.chains.map((chain) => {
            const steps = chain.transmitters.filter((transmitter) => transmitter.places.length > 0);
            if (steps.length === 0) return null;
            return (
              <div key={chain.chain_id} className="mb-4">
                <p className={styles.basis}>{chainTitle(family, chain, branchCount.get(chain.hadith_id) ?? 1)}</p>
                <ol className={styles.trail}>
                  {steps.map((transmitter) => (
                    <li key={transmitter.mention_id} className={styles.trailStep}>
                      <span dir="auto">{transmitter.places.map((place) => place.place).join(' / ')}</span>{' '}
                      <span className={styles.basis}>({transmitter.name_en || transmitter.surface_ar})</span>
                    </li>
                  ))}
                </ol>
              </div>
            );
          })}
        </>
      )}

      <h3 className={styles.subheading}>Transmitters in order</h3>
      {family.chains.map((chain) => (
        <div key={chain.chain_id} className="mb-6">
          <p className={styles.basis}>{chainTitle(family, chain, branchCount.get(chain.hadith_id) ?? 1)}</p>
          <ol className={styles.list}>
            {chain.transmitters.map((transmitter) => (
              <li key={transmitter.mention_id} className={styles.listItem}>
                <span className={styles.listYear}>Position {transmitter.position + 1}</span>
                <div>
                  <TransmitterName transmitter={transmitter} />
                  <p className={styles.basis}>
                    As written: <ArabicText>{transmitter.surface_ar}</ArabicText> · {identitySentence(transmitter)}
                  </p>
                  {(transmitter.identity === 'verified' || transmitter.identity === 'single_candidate') && (
                    <dl className={styles.facts}>
                      <LifespanFacts lifespan={transmitter.lifespan} />
                      <GenerationFacts generation={transmitter.generation} />
                      <PlaceFacts places={transmitter.places} />
                    </dl>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ))}

      {(family.epochs.length > 0 || family.events.length > 0) && (
        <>
          <h3 className={styles.subheading}><GlossaryTerm slug="era">Eras</GlossaryTerm> and events on this axis</h3>
          {sharedAxisBasis && <div className="mb-2"><BasisLabel basis={sharedAxisBasis} /></div>}
          <ul className={styles.list}>
            {[...family.epochs, ...family.events]
              .sort((left, right) => left.start - right.start)
              .map((entry) => (
                <li key={entry.id} className={styles.listItem}>
                  <span className={styles.listYear}>{formatInterval(entry)}</span>
                  <div>
                    {entry.name}
                    {entry.kind === 'epoch' && entry.boundary_note && <span className={styles.basis}> · Boundary disputed: {entry.boundary_note}</span>}
                    {entry.kind === 'event' && entry.location_name && <span className={styles.basis}> · {entry.location_name}</span>}{' '}
                    {!sharedAxisBasis && <BasisLabel basis={entry.basis} />}
                  </div>
                </li>
              ))}
          </ul>
        </>
      )}
      {!family.epochs_available && family.audience === 'review' && <p className={styles.note}>Eras are not yet available in this database.</p>}
    </section>
  );
}
