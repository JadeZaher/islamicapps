import type { DatumBasis } from '@/db/queries/timeline-contracts';
import { basisLabel } from '@/db/queries/timeline-rules';
import { SourceCredit } from '@/components/archive/SourceCredit';
import type { SourceCode } from '@/lib/sources/registry';
import styles from './timeline.module.css';

/** Source of each basis (src/lib/sources/registry.ts): lexicon fields are MSD; bios, seed and curator rows this archive's (SWI). */
function sourceFor(basis: DatumBasis): SourceCode {
  return basis === 'lexicon_uncited' ? 'MSD' : 'SWI';
}

/**
 * Where a datum comes from and whether it has been reviewed, as small flat text, with the short source reference
 * beside it. Cited rijal assertions (Taqrib, Tahdhib al-Kamal) will pass `source="RIJ"` once they are loaded.
 */
export function BasisLabel({ basis, source }: { basis: DatumBasis; source?: SourceCode }) {
  return (
    <span className={styles.basisLine}>
      <span className={styles.basis}>{basisLabel(basis)}</span>
      <SourceCredit code={source ?? sourceFor(basis)} className={styles.credit} />
    </span>
  );
}
