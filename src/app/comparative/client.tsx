'use client';

import { useState, useTransition } from 'react';
import { searchParallels } from '@/app/actions/read/comparative';
import { CrossCulturalParallelCard } from '@/components/CrossCulturalParallelCard';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { REGIONAL_CONTEXT } from './regional-context';

const PARALLEL_TYPES = [
    { value: '', label: 'All Types' },
    { value: 'CONDEMNATION', label: 'Condemnation' },
    { value: 'CULTURAL_BLEED', label: 'Cultural Crossover' },
    { value: 'SHARED_SOURCE', label: 'Shared Source' },
    { value: 'DIRECT_BORROWING', label: 'Direct Borrowing' },
    { value: 'APOLOGETIC', label: 'Apologetic' },
    { value: 'DISPUTED', label: 'Disputed' },
];

const ISRA_STATUSES = [
    { value: '', label: 'All Statuses' },
    { value: 'MUWAFIQ', label: 'Muwafiq (Consistent)' },
    { value: 'MUKHALIF', label: 'Mukhalif (Contrary)' },
    { value: 'MASKUT_ANHU', label: 'Maskut Anhu (neither affirmed nor denied)' },
    { value: 'NONE', label: 'Not Classified' },
];

const MOTIF_CATEGORIES = [
    { value: '', label: 'All Motifs' },
    { value: 'ESCHATOLOGY', label: 'Eschatology' },
    { value: 'CREATION', label: 'Creation' },
    { value: 'PROPHETIC_STORIES', label: 'Prophetic Stories' },
    { value: 'LEGAL', label: 'Legal' },
    { value: 'WISDOM', label: 'Wisdom Literature' },
    { value: 'PERSIAN_INFLUENCE', label: 'Persian Influence' },
    { value: 'COSMOLOGY', label: 'Cosmology' },
];

const CONFIDENCE_LEVELS = [
    { value: '', label: 'All Confidence Levels' },
    { value: 'HIGH', label: 'High' },
    { value: 'MEDIUM', label: 'Medium' },
    { value: 'LOW', label: 'Low' },
];

type SelectFilterKey = 'parallel_type' | 'isra_iliyyat_status' | 'motif_category' | 'confidence_level';

const SELECT_FILTERS: { key: SelectFilterKey; label: string; options: { value: string; label: string }[] }[] = [
    { key: 'parallel_type', label: 'Parallel Type', options: PARALLEL_TYPES },
    { key: 'isra_iliyyat_status', label: "Isra'iliyyat Status", options: ISRA_STATUSES },
    { key: 'motif_category', label: 'Motif Category', options: MOTIF_CATEGORIES },
    { key: 'confidence_level', label: 'Confidence', options: CONFIDENCE_LEVELS },
];

interface Props {
    initialParallels: any[];
    traditions: any[];
    stats: any[];
}

export function ComparativeClient({ initialParallels, traditions, stats }: Props) {
    const [parallels, setParallels] = useState(initialParallels);
    const [isPending, startTransition] = useTransition();
    const [filters, setFilters] = useState({
        tradition_id: '',
        parallel_type: '',
        isra_iliyyat_status: '',
        motif_category: '',
        confidence_level: '',
    });
    const [activeView, setActiveView] = useState<'results' | 'regional'>('results');

    const [error, setError] = useState<string | null>(null);

    const applyFilters = (newFilters: typeof filters) => {
        setFilters(newFilters);
        setError(null);
        startTransition(async () => {
            try {
                const results = await searchParallels({
                    tradition_id: newFilters.tradition_id || undefined,
                    parallel_type: (newFilters.parallel_type as any) || undefined,
                    isra_iliyyat_status: (newFilters.isra_iliyyat_status as any) || undefined,
                    motif_category: (newFilters.motif_category as any) || undefined,
                    confidence_level: (newFilters.confidence_level as any) || undefined,
                });
                setParallels(results);
            } catch {
                setError("Couldn't load parallels for these filters. Try again.");
            }
        });
    };

    // Stats: count by tradition
    const statsByTradition = traditions.map((t) => ({
        tradition: t,
        count: stats.filter((s: any) => s.tradition === t.name).reduce((a: number, b: any) => a + Number(b.count), 0),
    }));

    // Stats carry true counts; initialParallels is one page of results.
    const totalParallels = stats.reduce((sum: number, row: any) => sum + Number(row.count), 0);

    return (
        <main className="wrap pb-12 text-ink">
            <div>
                {/* Header */}
                <div className="page-header mb-8">
                    <h1 className="type-h1">Comparative studies</h1>
                </div>

                {/* Overview stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <Card className="pb-6">
                        <p className="type-h2 tabular-nums text-ink">{totalParallels.toLocaleString()}</p>
                        <p className="text-sm text-ink-muted">Parallels recorded</p>
                    </Card>
                    {statsByTradition.slice(0, 3).map(({ tradition, count }) => (
                        <Card key={tradition.id} className="pb-6">
                            <p className="type-h2 tabular-nums text-ink">{count}</p>
                            <p className="text-sm text-ink-muted">{tradition.name} parallels</p>
                        </Card>
                    ))}
                </div>

                {/* View toggle */}
                <div className="flex gap-3 mb-6" role="group" aria-label="View">
                    <Button
                        onClick={() => setActiveView('results')}
                        aria-pressed={activeView === 'results'}
                        variant="outline"
                        className={activeView === 'results' ? 'bg-ink text-paper' : ''}
                    >
                        Browse Parallels
                    </Button>
                    <Button
                        onClick={() => setActiveView('regional')}
                        aria-pressed={activeView === 'regional'}
                        variant="outline"
                        className={activeView === 'regional' ? 'bg-ink text-paper' : ''}
                    >
                        Regional Context
                    </Button>
                </div>

                {activeView === 'regional' ? (
                    /* Regional Context View */
                    <section aria-labelledby="regional-context-heading" className="space-y-4">
                        <h2 id="regional-context-heading" className="text-xl font-semibold text-ink">
                            Regional context
                        </h2>
                        {REGIONAL_CONTEXT.map((region) => (
                            <Card key={region.school} className="pb-4">
                                <CardContent className="pt-5">
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                        <div>
                                            <p className="type-label mb-1">
                                                Transmission School
                                            </p>
                                            <p className="text-ink font-semibold">{region.school}</p>
                                        </div>
                                        <div>
                                            <p className="type-label mb-1">
                                                Traditions Present
                                            </p>
                                            <div className="flex flex-wrap gap-1">
                                                {region.traditions.map((t) => (
                                                    <span key={t} className="type-label">
                                                        {t}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="type-label mb-1">
                                                Key Narrators
                                            </p>
                                            <div className="space-y-0.5">
                                                {region.narrators.map((n) => (
                                                    <p key={n} className="text-sm text-ink">{n}</p>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="type-label mb-1">
                                                Notes
                                            </p>
                                            <p className="text-sm text-ink-muted leading-relaxed">{region.notes}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </section>
                ) : (
                    /* Parallel Browse View */
                    <div className="flex flex-col gap-6 md:flex-row">
                        {/* Filter sidebar */}
                        <div className="space-y-5 md:w-56 md:shrink-0">
                            <Card className="pb-6">
                                <h3 className="text-sm font-semibold text-ink mb-3">Tradition</h3>
                                <div className="space-y-1.5">
                                    <button
                                        type="button"
                                        aria-pressed={!filters.tradition_id}
                                        onClick={() => applyFilters({ ...filters, tradition_id: '' })}
                                        className={`w-full text-left text-sm px-2 py-1.5  transition-colors ${!filters.tradition_id ? 'bg-accent-wash text-ink shadow-[inset_2px_0_0_var(--color-accent)]' : 'text-ink-muted hover:text-ink'}`}
                                    >
                                        All Traditions
                                    </button>
                                    {traditions.map((t) => (
                                        <button key={t.id}
                                            type="button"
                                            aria-pressed={filters.tradition_id === t.id}
                                            onClick={() => applyFilters({ ...filters, tradition_id: t.id })}
                                            className={`w-full text-left text-sm px-2 py-1.5  transition-colors ${filters.tradition_id === t.id ? 'bg-accent-wash text-ink shadow-[inset_2px_0_0_var(--color-accent)]' : 'text-ink-muted hover:text-ink'}`}
                                        >
                                            {t.name}
                                        </button>
                                    ))}
                                </div>
                            </Card>

                            {SELECT_FILTERS.map(({ key, label, options }) => (
                                <Card key={key} className="pb-6">
                                    <label htmlFor={`parallel-filter-${key}`} className="block text-sm font-semibold text-ink mb-3">
                                        {label}
                                    </label>
                                    <select
                                        id={`parallel-filter-${key}`}
                                        value={filters[key]}
                                        onChange={(e) => applyFilters({ ...filters, [key]: e.target.value })}
                                        className="h-10 w-full bg-surface border border-control text-ink px-3 text-sm"
                                    >
                                        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                </Card>
                            ))}

                            {(filters.tradition_id || filters.parallel_type || filters.isra_iliyyat_status || filters.motif_category || filters.confidence_level) && (
                                <Button
                                    onClick={() => applyFilters({ tradition_id: '', parallel_type: '', isra_iliyyat_status: '', motif_category: '', confidence_level: '' })}
                                    variant="outline"
                                    className="w-full border-rule text-ink text-sm"
                                >
                                    Clear Filters
                                </Button>
                            )}
                        </div>

                        {/* Results */}
                        <div className="flex-1" aria-busy={isPending}>
                            <p role="status" className="text-sm text-ink-muted mb-4">
                                {isPending ? 'Searching...' : `${parallels.length} parallel${parallels.length !== 1 ? 's' : ''} found`}
                            </p>

                            {error && (
                                <div role="alert" className="mb-4 flex items-center justify-between gap-3 border border-danger bg-transparent px-4 py-3 text-sm text-danger">
                                    <span>{error}</span>
                                    <Button type="button" size="sm" variant="outline" onClick={() => applyFilters(filters)} disabled={isPending}>
                                        Retry
                                    </Button>
                                </div>
                            )}

                            {parallels.length > 0 ? (
                                <div className={`space-y-4 transition-opacity ${isPending ? 'opacity-60' : ''}`}>
                                    {parallels.map((p) => (
                                        <CrossCulturalParallelCard
                                            key={p.id}
                                            parallel={p}
                                            tradition={p.tradition}
                                            sourceText={p.source_text}
                                            hadith={p.hadith}
                                            motifTags={p.motif_tags}
                                            showHadithLink
                                        />
                                    ))}
                                </div>
                            ) : (
                                <Card className="border-rule border-dashed py-8">
                                    <p className="text-center text-ink-muted">
                                        {isPending ? 'Searching...' : 'No parallels match these filters.'}
                                    </p>
                                </Card>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </main>
    );
}
