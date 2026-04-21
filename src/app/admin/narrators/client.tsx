'use client';

import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';

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

const RELIABILITY_STYLES: Record<string, string> = {
    THIQA: 'bg-green-500/20 text-green-400 border-green-500/30',
    SADUQ: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    DAIF: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    KADHAB: 'bg-red-500/20 text-red-400 border-red-500/30',
    MAJHUL: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

const TABAQAH_LABELS: Record<string, string> = {
    PROPHET: 'Prophet',
    SAHABA: 'Sahaba',
    TABI_UN: "Tabi'un",
    TABI_TABI_IN: "Tabi' al-Tabi'in",
    LATER_SCHOLAR: 'Later Scholar',
};

export function NarratorsClient({ narrators, pagination }: NarratorsClientProps) {
    const router = useRouter();

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Narrators</h1>
                    <p className="text-slate-400 mt-1">Browse narrator biographies and reliability ratings</p>
                </div>
            </div>

            <SearchFilterBar
                searchPlaceholder="Search narrators by name..."
                totalResults={pagination.total}
                filters={[
                    {
                        key: 'reliability',
                        label: 'Reliability',
                        options: [
                            { label: 'All Reliability', value: '' },
                            { label: 'Thiqa (Trustworthy)', value: 'THIQA' },
                            { label: 'Saduq (Truthful)', value: 'SADUQ' },
                            { label: "Da'if (Weak)", value: 'DAIF' },
                            { label: 'Kadhab (Liar)', value: 'KADHAB' },
                            { label: 'Majhul (Unknown)', value: 'MAJHUL' },
                        ],
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
                    <Card key={n.id} className="bg-slate-900 border-slate-700 p-5 hover:border-slate-600 transition-colors">
                        <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-1.5">
                                    <h3 className="text-base font-semibold text-white truncate">
                                        {n.name_english || 'Unknown'}
                                    </h3>
                                    {n.name_arabic && (
                                        <span className="text-base text-slate-400 font-amiri shrink-0" dir="rtl">
                                            {n.name_arabic}
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                    {n.reliability && (
                                        <Badge className={RELIABILITY_STYLES[n.reliability] || RELIABILITY_STYLES.MAJHUL}>
                                            {n.reliability}
                                        </Badge>
                                    )}
                                    {n.tabaqah && (
                                        <Badge className="bg-slate-800 text-slate-300 border-slate-600">
                                            {TABAQAH_LABELS[n.tabaqah] || n.tabaqah}
                                        </Badge>
                                    )}
                                    {n.death_year_hijri && (
                                        <span className="text-xs text-slate-500">
                                            d. {n.death_year_hijri} AH
                                        </span>
                                    )}
                                    {n.geographic_region && (
                                        <span className="text-xs text-slate-500">
                                            {n.geographic_region}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => router.push(`/narrator/${n.id}`)}
                                className="border-slate-600 text-slate-300 hover:text-white hover:bg-slate-800 shrink-0 ml-4"
                            >
                                View
                            </Button>
                        </div>
                    </Card>
                ))}

                {narrators.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">No narrators found.</p>
                    </Card>
                )}

                <PaginationControls
                    page={pagination.page}
                    totalPages={pagination.totalPages}
                    total={pagination.total}
                    pageSize={pagination.pageSize}
                    onPageChange={(p) => router.push(`?page=${p}`)}
                />
            </div>
        </div>
    );
}
