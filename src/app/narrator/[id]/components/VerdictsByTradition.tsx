import type { NarratorVerdict } from '@/db/queries/contracts';
import { ConsensusBadge } from '@/components/ConsensusBadge';
import { TraditionBadge } from '@/components/TraditionBadge';

/** Verdicts grouped by tradition, each with its critic; nothing renders when none carry a tradition. */
export function VerdictsByTradition({ verdicts }: { verdicts: NarratorVerdict[] }) {
    const groups = new Map<string, NarratorVerdict[]>();
    for (const verdict of verdicts) {
        if (!verdict.tradition) continue;
        groups.set(verdict.tradition, [...(groups.get(verdict.tradition) ?? []), verdict]);
    }
    if (groups.size === 0) return null;
    return (
        <dl className="mb-8 space-y-2 text-sm">
            {[...groups.entries()].map(([tradition, entries]) => (
                <div key={tradition} className="flex flex-wrap items-center gap-2">
                    <dt>
                        <TraditionBadge tradition={tradition} />
                    </dt>
                    {entries.map((verdict) => (
                        <dd key={verdict.id} className="flex items-center gap-2">
                            <ConsensusBadge verdict={verdict.verdict} />
                            {verdict.critic && <span className="text-slate-400">{verdict.critic}</span>}
                        </dd>
                    ))}
                </div>
            ))}
        </dl>
    );
}
