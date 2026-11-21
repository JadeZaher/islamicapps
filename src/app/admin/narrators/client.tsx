'use client';

import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';
import { ConsensusBadge } from '@/components/ConsensusBadge';
import { TraditionBadge } from '@/components/TraditionBadge';
import { HADITH_TRADITION_OPTIONS } from '@/lib/constants/traditions';
import type { NarratorVerdict } from '@/db/queries/contracts';
import { NarratorName } from '@/components/NarratorName';

interface PaginationInfo {
    page: number;
    totalPages: number;
    total: number;
    pageSize: number;
}

interface NarratorsClientProps {
    narrators: any[];
    pagination: PaginationInfo;
}

const TABAQAH_LABELS: Record<string, string> = {
    PROPHET: 'Prophet',
    SAHABA: 'Sahaba',
    TABI_UN: "Tabi'un",
    TABI_TABI_IN: "Tabi' al-Tabi'in",
    LATER_SCHOLAR: 'Later Scholar',
};

/** Each tradition's verdicts with their critic; reviewer mode, so every status shows, and non-published ones are labelled. */
function VerdictsByTradition({ verdicts }: { verdicts: NarratorVerdict[] }) {
    const groups = new Map<string, NarratorVerdict[]>();
    for (const verdict of verdicts) {
        const key = verdict.tradition ?? '';
        groups.set(key, [...(groups.get(key) ?? []), verdict]);
    }
    return (
        <>
            {[...groups.entries()].map(([tradition, entries]) => (
                <span key={tradition} className="flex items-center gap-1.5">
                    {tradition && <TraditionBadge tradition={tradition} />}
                    {entries.map((verdict) => (
                        <span key={verdict.id} className="flex items-center gap-1.5">
                            <ConsensusBadge verdict={verdict.verdict} />
                            {verdict.critic && <span className="text-xs text-ink-muted">{verdict.critic}</span>}
                            {verdict.status !== 'published' && (
                                <span className="text-xs capitalize text-ink-muted">{verdict.status}</span>
                            )}
                        </span>
                    ))}
                </span>
            ))}
        </>
    );
}

export function NarratorsClient({ narrators, pagination }: NarratorsClientProps) {
    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-3xl font-bold text-ink">Narrators</h1>
            </div>

            <SearchFilterBar
                searchPlaceholder="Search narrators by name..."
                totalResults={pagination.total}
                filters={[
                    {
                        key: 'verdict',
                        label: 'Verdict',
                        legacyKeys: ['reliability'],
                        options: [
                            { label: 'Any verdict', value: '' },
                            { label: 'Thiqa', value: 'thiqa' },
                            { label: 'Thiqa thabt', value: 'thiqa_thabt' },
                            { label: 'Saduq', value: 'saduq' },
                            { label: 'La basa bihi', value: 'la_basa_bihi' },
                            { label: 'Mukhtalaf fihi', value: 'mukhtalaf_fihi' },
                            { label: "Da'if", value: 'daif' },
                            { label: 'Matruk', value: 'matruk' },
                            { label: 'Kadhab', value: 'kadhab' },
                            { label: 'Majhul', value: 'majhul' },
                        ],
                    },
                    {
                        key: 'tradition',
                        label: 'Tradition',
                        options: HADITH_TRADITION_OPTIONS,
                    },
                    {
                        key: 'tabaqah',
                        label: 'Generation',
                        options: [
                            { label: 'All Generations', value: '' },
                            { label: 'Sahaba', value: 'SAHABA' },
                            { label: "Tabi'un", value: 'TABI_UN' },
                            { label: "Tabi' al-Tabi'in", value: 'TABI_TABI_IN' },
                            { label: 'Later Scholar', value: 'LATER_SCHOLAR' },
                        ],
                    },
                ]}
            />

            <div className="space-y-3">
                {narrators.map((n) => (
                    <Card key={n.id} className="pb-6">
                        <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                                <h3 className="mb-1.5">
                                    <NarratorName
                                        english={n.name_english || 'Unnamed record'}
                                        arabic={n.name_arabic}
                                        latinClassName="text-base font-semibold text-ink"
                                        arabicClassName="text-lg leading-relaxed text-ink-muted"
                                    />
                                </h3>
                                <div className="flex items-center gap-2 flex-wrap">
                                    <VerdictsByTradition verdicts={n.verdicts ?? []} />
                                    {n.tabaqah && (
                                        <Badge className="bg-sunken text-ink border-rule">
                                            {TABAQAH_LABELS[n.tabaqah] || n.tabaqah}
                                        </Badge>
                                    )}
                                    {n.death_year_hijri && (
                                        <span className="text-xs text-ink-muted">
                                            d. {n.death_year_hijri} AH
                                        </span>
                                    )}
                                    {n.geographic_region && (
                                        <span className="text-xs text-ink-muted">
                                            {n.geographic_region}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <Button
                                asChild
                                size="sm"
                                variant="outline"
                                className="border-rule text-ink hover:text-ink hover:bg-sunken shrink-0 ml-4"
                            >
                                <Link href={`/narrator/${n.id}`} aria-label={`View ${n.name_english || 'narrator'}`}>View</Link>
                            </Button>
                        </div>
                    </Card>
                ))}

                {narrators.length === 0 && (
                    <Card className="border-rule border-dashed py-8">
                        <p className="text-center text-ink-muted">No narrators found.</p>
                    </Card>
                )}

                <PaginationControls
                    page={pagination.page}
                    totalPages={pagination.totalPages}
                    total={pagination.total}
                    pageSize={pagination.pageSize}
                />
            </div>
        </div>
    );
}
