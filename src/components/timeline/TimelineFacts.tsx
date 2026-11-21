/** Text forms of the time-and-place claims, each with its basis. Competing reports are listed side by side, never resolved. */
import type { DateClaim, GenerationClaim, Lifespan, PlaceClaim } from '@/db/queries/timeline-contracts';
import { formatHijri, formatRange, generationLabel } from '@/db/queries/timeline-rules';
import { BasisLabel } from './BasisLabel';
import styles from './timeline.module.css';

const RELATION_LABELS: Record<PlaceClaim['relation'], string> = {
  born: 'born',
  died: 'died',
  resided: 'lived',
  region: 'region',
};

/** "d. 93 AH" for a row label; ranges stay ranges. */
export function shortLife(lifespan: Lifespan): string | null {
  const parts = [
    lifespan.birth ? `b. ${formatRange(lifespan.birth)}` : null,
    lifespan.death ? `d. ${formatRange(lifespan.death)}` : null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(' · ') : null;
}

function ClaimLine({ claim }: { claim: DateClaim }) {
  return (
    <li>
      {claim.usable ? formatRange(claim.range) : <>recorded as {claim.as_recorded}, {formatHijri(0)}, so not drawn</>}{' '}
      <BasisLabel basis={claim.basis} />
    </li>
  );
}

/** Birth and death claims grouped by event; a note when the recorded values compete. */
export function LifespanFacts({ lifespan }: { lifespan: Lifespan }) {
  const births = lifespan.claims.filter((claim) => claim.event === 'birth');
  const deaths = lifespan.claims.filter((claim) => claim.event === 'death');
  return (
    <>
      <dt>Born</dt>
      <dd>{births.length > 0 ? <ul>{births.map((claim, index) => <ClaimLine key={index} claim={claim} />)}</ul> : 'Not recorded'}</dd>
      <dt>Died</dt>
      <dd>
        {deaths.length > 0 ? <ul>{deaths.map((claim, index) => <ClaimLine key={index} claim={claim} />)}</ul> : 'Not recorded'}
        {lifespan.competing && <p className={styles.basis}>The recorded values differ; both are shown and neither is preferred.</p>}
      </dd>
    </>
  );
}

export function GenerationFacts({ generation }: { generation: GenerationClaim[] }) {
  return (
    <>
      <dt>Generation</dt>
      <dd>
        {generation.length > 0 ? (
          <ul>
            {generation.map((claim, index) => (
              <li key={index}>
                {generationLabel(claim)} <BasisLabel basis={claim.basis} />
              </li>
            ))}
          </ul>
        ) : (
          'Not recorded'
        )}
      </dd>
    </>
  );
}

export function PlaceFacts({ places }: { places: PlaceClaim[] }) {
  return (
    <>
      <dt>Places</dt>
      <dd>
        {places.length > 0 ? (
          <ul>
            {places.map((place, index) => (
              <li key={index}>
                <span dir="auto">{place.place}</span> <span className={styles.basis}>({RELATION_LABELS[place.relation]})</span>{' '}
                <BasisLabel basis={place.basis} />
              </li>
            ))}
          </ul>
        ) : (
          'Not recorded'
        )}
      </dd>
    </>
  );
}
