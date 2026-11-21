/** Flat SVG geometry for the shared Hijri axis: ticks, era bands, event ticks and life marks. Decorative: aria-hidden; every datum is also in a list. */
import type { EpochEntry, EventEntry, Lifespan } from '@/db/queries/timeline-contracts';
import { formatHijri } from '@/db/queries/timeline-rules';
import { isVisible, placeInterval, type YearScale } from './scale';
import styles from './timeline.module.css';

/** An SVG stretched to the track; x runs 0..100 (percent), y 0..10. Hairlines keep 1px under stretching. */
function Track({ children, tall = false }: { children: React.ReactNode; tall?: boolean }) {
  return (
    <svg className={styles.svg} viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true" focusable="false" data-tall={tall || undefined}>
      {children}
    </svg>
  );
}

export function AxisRow({ scale }: { scale: YearScale }) {
  return (
    <div className={styles.row} aria-hidden="true">
      <span className={styles.laneLabel}>Hijri years</span>
      <div className={styles.track}>
        <Track>
          {scale.ticks.map((year) => (
            <line key={year} x1={scale.at(year)} x2={scale.at(year)} y1={8} y2={10} stroke="var(--timeline-faint)" vectorEffect="non-scaling-stroke" />
          ))}
        </Track>
        {scale.ticks.map((year) => (
          <span key={year} className={styles.tickLabel}
            // Edge labels anchor inward so they never clip at either end of the track.
            style={{ left: `${scale.at(year)}%`, transform: `translate(${scale.at(year) > 90 ? '-100%' : scale.at(year) < 10 ? '0' : '-50%'}, -50%)` }}>
            {formatHijri(year)}
          </span>
        ))}
      </div>
    </div>
  );
}

/** One lane of era bands: flat rectangles in two alternating tones, a lighter end where a boundary is disputed. */
export function EpochLane({ label, epochs, scale }: { label: string; epochs: EpochEntry[]; scale: YearScale }) {
  const visible = epochs.filter((epoch) => isVisible(scale, epoch.start, epoch.end));
  if (visible.length === 0) return null;
  return (
    <div className={styles.row} aria-hidden="true">
      <span className={styles.laneLabel}>{label}</span>
      <div className={styles.track}>
        <Track>
          {visible.map((epoch, index) => {
            const { left, width } = placeInterval(scale, epoch.start, epoch.end);
            const fill = index % 2 === 0 ? 'var(--timeline-band)' : 'var(--timeline-band-alternate)';
            return (
              <g key={epoch.id}>
                <rect x={left} width={width} y={0} height={10} fill={fill} />
                <line x1={left} x2={left} y1={0} y2={10} stroke="var(--timeline-rule)" vectorEffect="non-scaling-stroke" />
              </g>
            );
          })}
        </Track>
        {visible.map((epoch) => {
          const { left, width } = placeInterval(scale, epoch.start, epoch.end);
          return (
            <span key={epoch.id} className={styles.bandLabel} style={{ left: `${left}%`, width: `${width}%` }}>
              {epoch.name}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/** Events as hairline ticks (a flat span where the event lasts several years). */
export function EventLane({ events, scale }: { events: EventEntry[]; scale: YearScale }) {
  const visible = events.filter((event) => isVisible(scale, event.start, event.end));
  if (visible.length === 0) return null;
  return (
    <div className={styles.row} aria-hidden="true">
      <span className={styles.laneLabel}>Events</span>
      <div className={styles.track}>
        <Track>
          {visible.map((event) => {
            const x = scale.at(event.start);
            const spans = event.end !== null && event.end > event.start;
            return (
              <g key={event.id}>
                {spans && <rect x={x} width={scale.at(event.end!) - x} y={4} height={2} fill="var(--timeline-muted)" />}
                <line x1={x} x2={x} y1={1} y2={9} stroke="var(--timeline-ink)" vectorEffect="non-scaling-stroke" />
              </g>
            );
          })}
        </Track>
      </div>
    </div>
  );
}

/**
 * A life on the axis. Both bounds: a bar, certain part in ink, the span of competing or ranged dates lighter.
 * One bound: a square mark (filled for death, outlined for birth). No bound: nothing is drawn; `fallback` says why.
 */
export function LifeMarks({ lifespan, scale, fallback }: { lifespan: Lifespan; scale: YearScale; fallback: string }) {
  const { birth, death } = lifespan;
  if (!birth && !death) {
    return <span className={styles.trackText}>{fallback}</span>;
  }
  const shapes: React.ReactNode[] = [];
  if (birth && death) {
    const outerLeft = scale.at(birth.min);
    const innerLeft = scale.at(birth.max);
    const innerRight = scale.at(Math.max(death.min, birth.max));
    const outerRight = scale.at(death.max);
    shapes.push(<rect key="outer" x={outerLeft} width={Math.max(outerRight - outerLeft, 0.5)} y={3.5} height={3} fill="var(--timeline-uncertain)" />);
    shapes.push(<rect key="inner" x={innerLeft} width={Math.max(innerRight - innerLeft, 0.5)} y={3.5} height={3} fill="var(--timeline-life)" />);
  } else if (death) {
    const left = scale.at(death.min);
    shapes.push(<rect key="death" x={left - 0.4} width={Math.max(scale.at(death.max) - left, 0) + 0.8} y={2} height={6} fill="var(--timeline-life)" />);
  } else if (birth) {
    const left = scale.at(birth.min);
    shapes.push(
      <rect key="birth" x={left - 0.4} width={Math.max(scale.at(birth.max) - left, 0) + 0.8} y={2} height={6} fill="none"
        stroke="var(--timeline-life)" vectorEffect="non-scaling-stroke" />,
    );
  }
  return <Track tall>{shapes}</Track>;
}

export function Legend() {
  return (
    <ul className={styles.legend} aria-hidden="true">
      <li><span className={styles.legendSwatch} style={{ background: 'var(--timeline-life)' }} />Lifespan, both dates recorded</li>
      <li><span className={styles.legendSwatch} style={{ background: 'var(--timeline-uncertain)' }} />Range or competing dates</li>
      <li><span className={styles.legendSwatch} style={{ background: 'var(--timeline-life)', width: '0.375rem' }} />Death year only</li>
      <li><span className={styles.legendSwatch} style={{ outline: '1px solid var(--timeline-life)', width: '0.375rem', background: 'transparent' }} />Birth year only</li>
      <li><span className={styles.legendSwatch} style={{ background: 'var(--timeline-ink)', width: '1px' }} />Event</li>
    </ul>
  );
}
