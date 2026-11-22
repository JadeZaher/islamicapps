'use client';

import type { FamilyTelling } from '@/db/queries/contracts';
import { noChainNote } from '../chain-structure';
import { IsnadChain } from '../IsnadChain';
import styles from './family.module.css';
import { groupTellings, tellingReference } from './labels';
import { TextCredit } from './SourceCredits';
import { TraditionMark } from './TellingsList';

function ChainBlock({ telling, isFocal }: { telling: FamilyTelling; isFocal: boolean }) {
  const reference = tellingReference(telling);
  const chainIds = new Set(telling.chain.nodes.map((node) => node.chain_id));
  return (
    <section className={styles.chainBlock} aria-label={`${reference}, ${telling.tradition}${isFocal ? ', this report' : ''}`}>
      <h3 className={styles.chainHeading}>
        <TraditionMark tradition={telling.tradition} />
        <span className={styles.muted}>{telling.tradition} · </span>
        {reference}
        {isFocal && <span className={styles.muted}> · this report</span>}
      </h3>
      <TextCredit hadithId={telling.hadith_id} role="Chain as written" className="mb-4 !text-xs !leading-4" />
      {chainIds.size === 0 ? (
        <p className={`type-small ${styles.muted}`}>
          {noChainNote(telling.chain.disposition) ?? 'No chain was extracted for this telling; its source text is shown above.'}
        </p>
      ) : (
        // The shared chain renderer; the tradition and work are already in the heading above.
        <IsnadChain chain={{ ...telling.chain, tradition: null, source_work: null }} chainLabel={reference} />
      )}
    </section>
  );
}

/** Every chain of every telling as ordered lists, labelled by tradition and work: the diagram's accessible equivalent. */
export function AllChains({ tellings }: { tellings: FamilyTelling[] }) {
  const focal = tellings.find((telling) => telling.is_focal);
  const groups = groupTellings(tellings);
  return (
    <div>
      {focal && <ChainBlock telling={focal} isFocal />}
      {groups.flatMap((group) => group.works.flatMap((work) => work.tellings)).map((telling) => (
        <ChainBlock key={telling.hadith_id} telling={telling} isFocal={false} />
      ))}
    </div>
  );
}
