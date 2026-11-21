import type { GenerationClaim, GenerationClass } from '@/db/queries/timeline-contracts';
import { generationLabel } from '@/db/queries/timeline-rules';
import { BasisLabel } from '@/components/timeline/BasisLabel';
import styles from '@/components/timeline/timeline.module.css';

const SCALE: Array<{ key: GenerationClass; label: string }> = [
  { key: 'prophet', label: 'The Prophet' },
  { key: 'companion', label: 'Companions' },
  { key: 'follower', label: 'Followers' },
  { key: 'follower_of_followers', label: 'Followers of the Followers' },
  { key: 'third_century', label: 'Third century' },
  { key: 'fourth_century_or_later', label: 'Fourth century and later' },
];

/**
 * Generation (tabaqa) as a six-step flat scale. Every recorded claim is listed with its basis; each class a claim
 * names is marked, so two sources that disagree mark two steps. Nothing is marked when nothing is recorded.
 */
export function TabaqahTimeline({ generation }: { generation: GenerationClaim[] }) {
  if (generation.length === 0) return <span>Not recorded</span>;
  const marked = new Set(generation.map((claim) => claim.class));
  return (
    <div className="flex flex-col gap-2">
      <ul>
        {generation.map((claim, index) => (
          <li key={index}>
            {generationLabel(claim)} <BasisLabel basis={claim.basis} />
          </li>
        ))}
      </ul>
      <svg width="192" height="6" viewBox="0 0 192 6" aria-hidden="true" focusable="false" className={styles.root}>
        {SCALE.map((step, index) => (
          <rect key={step.key} x={index * 32} y={marked.has(step.key) ? 0 : 2} width={28} height={marked.has(step.key) ? 6 : 2}
            fill={marked.has(step.key) ? 'var(--color-ink)' : 'var(--color-rule)'}>
            <title>{step.label}</title>
          </rect>
        ))}
      </svg>
    </div>
  );
}
