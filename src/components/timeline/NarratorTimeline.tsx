/**
 * A narrator's life and times: dates as ranges with their basis, generation, places, and the eras and events the
 * recorded life touches (lived through, or at the recorded birth or death year when only one is known). Server
 * component; the figure is decorative and every datum is repeated in the lists. See src/components/AGENTS.md §Time and place.
 */
import type { EpochEntry, EventEntry, LifeRelation, NarratorTimeline as NarratorTimelineData, RelatedInterval } from '@/db/queries/timeline-contracts';
import { formatInterval } from '@/db/queries/timeline-rules';
import { GlossaryTerm } from '@/components/GlossaryTerm';
import { TabaqahTimeline } from '@/components/TabaqahTimeline';
import { BasisLabel } from './BasisLabel';
import { buildScale } from './scale';
import { AxisRow, EpochLane, EventLane, Legend, LifeMarks } from './TimelineGeometry';
import { LifespanFacts, PlaceFacts } from './TimelineFacts';
import styles from './timeline.module.css';

const RELATION_LABELS: Record<LifeRelation, string> = {
  during_lifetime: 'During the recorded lifetime',
  at_death: 'At the recorded death year',
  at_birth: 'At the recorded birth year',
};

/** When every entry shares one basis it is stated once above the list instead of on every row. */
function RelatedList<T extends EpochEntry | EventEntry>({ items }: { items: Array<RelatedInterval<T>> }) {
  const shared = items.every((item) => item.entry.basis === items[0]?.entry.basis) ? items[0]?.entry.basis : undefined;
  return (
    <>
    {shared && <div className="mb-2"><BasisLabel basis={shared} /></div>}
    <ul className={styles.list}>
      {items.map(({ entry, relation }) => (
        <li key={entry.id} className={styles.listItem}>
          <span className={styles.listYear}>{formatInterval(entry)}</span>
          <div>
            {entry.name}
            <span className={styles.basis}> · {RELATION_LABELS[relation]}</span>
            {entry.kind === 'epoch' && entry.alternate_names.length > 0 && (
              <span className={styles.basis}>
                {' · Also called '}
                {entry.alternate_names.map((alternate) => `${alternate.name} (${alternate.used_by})`).join('; ')}
              </span>
            )}
            {entry.kind === 'epoch' && entry.boundary_note && <span className={styles.basis}> · Boundary disputed: {entry.boundary_note}</span>}
            {entry.kind === 'event' && entry.location_name && <span className={styles.basis}> · {entry.location_name}</span>}{' '}
            {!shared && <BasisLabel basis={entry.basis} />}
          </div>
        </li>
      ))}
    </ul>
    </>
  );
}

export function NarratorTimeline({ timeline }: { timeline: NarratorTimelineData }) {
  const { lifespan } = timeline;
  const known = lifespan.birth || lifespan.death
    ? { min: (lifespan.birth ?? lifespan.death)!.min, max: (lifespan.death ?? lifespan.birth)!.max }
    : null;
  const scale = known ? buildScale(known, 60) : null;
  const epochs = timeline.epochs.map((item) => item.entry);
  const parents = new Set(epochs.map((epoch) => epoch.parent_id).filter(Boolean));
  const traditions = [...new Set(epochs.map((epoch) => epoch.tradition_context).filter((value): value is string => Boolean(value)))].sort();
  const sharedEras = timeline.epochs.filter((item) => !item.entry.tradition_context);

  return (
    <section className={styles.root} aria-labelledby="life-and-times-heading">
      <h2 id="life-and-times-heading" className={styles.heading}>Life and times</h2>
      {timeline.audience === 'review' && <p className={styles.note}>Reviewer view: unreviewed data is included and labelled.</p>}

      <dl className={styles.facts}>
        <LifespanFacts lifespan={lifespan} />
        <dt><GlossaryTerm slug="tabaqa">Generation</GlossaryTerm></dt>
        <dd><TabaqahTimeline generation={timeline.generation} /></dd>
        <PlaceFacts places={timeline.places} />
      </dl>

      {scale ? (
        <figure className={`${styles.figure} mt-6`} aria-label="Timeline of the recorded life with eras and events; the same information follows as lists.">
          <AxisRow scale={scale} />
          <EpochLane label="Eras" epochs={epochs.filter((epoch) => !epoch.tradition_context && !epoch.parent_id)} scale={scale} />
          <EpochLane label="Sub-periods" epochs={epochs.filter((epoch) => !epoch.tradition_context && epoch.parent_id)} scale={scale} />
          {traditions.map((tradition) => (
            <EpochLane key={tradition} label={`${tradition} reckoning`}
              epochs={epochs.filter((epoch) => epoch.tradition_context === tradition && !parents.has(epoch.id))} scale={scale} />
          ))}
          <EventLane events={timeline.events.map((item) => item.entry)} scale={scale} />
          <div className={`${styles.row} ${styles.rowTall}`} aria-hidden="true">
            <span className={styles.laneLabel}>Life</span>
            <div className={styles.track}>
              <LifeMarks lifespan={lifespan} scale={scale} fallback="Not recorded" />
            </div>
          </div>
          <Legend />
        </figure>
      ) : (
        <p className={`${styles.note} mt-6`}>
          No life date is recorded{timeline.audience === 'public' ? ' that has been reviewed and cited' : ''}, so no era or event is
          related to this narrator. A generation is not converted into years.
        </p>
      )}

      {sharedEras.length > 0 && (
        <>
          <h3 className={styles.subheading}><GlossaryTerm slug="era">Eras</GlossaryTerm></h3>
          <RelatedList items={sharedEras} />
        </>
      )}
      {traditions.map((tradition) => (
        <div key={tradition}>
          <h3 className={styles.subheading}>Eras in {tradition} reckoning</h3>
          <RelatedList items={timeline.epochs.filter((item) => item.entry.tradition_context === tradition)} />
        </div>
      ))}
      {timeline.events.length > 0 && (
        <>
          <h3 className={styles.subheading}>Events</h3>
          <RelatedList items={timeline.events} />
        </>
      )}
      {scale && timeline.epochs.length === 0 && timeline.events.length === 0 && (
        <p className={styles.note}>No era or event{timeline.audience === 'public' ? ' that has been reviewed and cited' : ''} falls within the recorded dates.</p>
      )}
      {!timeline.epochs_available && timeline.audience === 'review' && <p className={styles.note}>Eras are not yet available in this database.</p>}
    </section>
  );
}
