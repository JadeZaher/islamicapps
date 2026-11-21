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
        <main className="px-6 py-10 text-slate-100">
            <div className="mx-auto max-w-6xl">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-semibold">Comparative studies</h1>
                </div>

                {/* Overview stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <Card className="bg-white/5 border-white/10 p-4">
                        <p className="text-2xl font-bold text-white">{totalParallels.toLocaleString()}</p>
                        <p className="text-sm text-slate-400">Parallels recorded</p>
                    </Card>
                    {statsByTradition.slice(0, 3).map(({ tradition, count }) => (
                        <Card key={tradition.id} className="bg-white/5 border-white/10 p-4">
                            <p className="text-2xl font-bold text-white">{count}</p>
                            <p className="text-sm text-slate-400">{tradition.name} parallels</p>
                        </Card>
                    ))}
                </div>

                {/* View toggle */}
                <div className="flex gap-3 mb-6" role="group" aria-label="View">
                    <Button
                        onClick={() => setActiveView('results')}
                        aria-pressed={activeView === 'results'}
                        className={activeView === 'results' ? 'bg-cyan-700 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'}
                    >
                        Browse Parallels
                    </Button>
                    <Button
                        onClick={() => setActiveView('regional')}
                        aria-pressed={activeView === 'regional'}
                        className={activeView === 'regional' ? 'bg-cyan-700 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'}
                    >
                        Regional Context
                    </Button>
                </div>

                {activeView === 'regional' ? (
                    /* Regional Context View */
                    <section aria-labelledby="regional-context-heading" className="space-y-4">
                        <h2 id="regional-context-heading" className="text-xl font-semibold text-white">
                            Regional context
                        </h2>
                        {REGIONAL_CONTEXT.map((region) => (
                            <Card key={region.school} className="bg-white/5 border-white/10">
                                <CardContent className="pt-5">
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                        <div>
                                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                                                Transmission School
                                            </p>
                                            <p className="text-white font-semibold">{region.school}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                                                Traditions Present
                                            </p>
                                            <div className="flex flex-wrap gap-1">
                                                {region.traditions.map((t) => (
                                                    <span key={t} className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                                        {t}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                                                Key Narrators
                                            </p>
                                            <div className="space-y-0.5">
                                                {region.narrators.map((n) => (
                                                    <p key={n} className="text-sm text-slate-300">{n}</p>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                                                Notes
                                            </p>
                                            <p className="text-sm text-slate-400 leading-relaxed">{region.notes}</p>
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
                            <Card className="bg-white/5 border-white/10 p-4">
                                <h3 className="text-sm font-semibold text-white mb-3">Tradition</h3>
                                <div className="space-y-1.5">
                                    <button
                                        type="button"
                                        aria-pressed={!filters.tradition_id}
                                        onClick={() => applyFilters({ ...filters, tradition_id: '' })}
                                        className={`w-full text-left text-sm px-2 py-1.5 rounded transition-colors ${!filters.tradition_id ? 'bg-cyan-700/50 text-white' : 'text-slate-400 hover:text-white'}`}
                                    >
                                        All Traditions
                                    </button>
                                    {traditions.map((t) => (
                                        <button key={t.id}
                                            type="button"
                                            aria-pressed={filters.tradition_id === t.id}
                                            onClick={() => applyFilters({ ...filters, tradition_id: t.id })}
                                            className={`w-full text-left text-sm px-2 py-1.5 rounded transition-colors ${filters.tradition_id === t.id ? 'bg-cyan-700/50 text-white' : 'text-slate-400 hover:text-white'}`}
                                        >
                                            {t.name}
                                        </button>
                                    ))}
                                </div>
                            </Card>

                            {SELECT_FILTERS.map(({ key, label, options }) => (
                                <Card key={key} className="bg-white/5 border-white/10 p-4">
                                    <label htmlFor={`parallel-filter-${key}`} className="block text-sm font-semibold text-white mb-3">
                                        {label}
                                    </label>
                                    <select
                                        id={`parallel-filter-${key}`}
                                        value={filters[key]}
                                        onChange={(e) => applyFilters({ ...filters, [key]: e.target.value })}
                                        className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1.5 text-sm"
                                    >
                                        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                </Card>
                            ))}

                            {(filters.tradition_id || filters.parallel_type || filters.isra_iliyyat_status || filters.motif_category || filters.confidence_level) && (
                                <Button
                                    onClick={() => applyFilters({ tradition_id: '', parallel_type: '', isra_iliyyat_status: '', motif_category: '', confidence_level: '' })}
                                    variant="outline"
                                    className="w-full border-slate-600 text-slate-300 text-sm"
                                >
                                    Clear Filters
                                </Button>
                            )}
                        </div>

                        {/* Results */}
                        <div className="flex-1" aria-busy={isPending}>
                            <p role="status" className="text-sm text-slate-400 mb-4">
                                {isPending ? 'Searching...' : `${parallels.length} parallel${parallels.length !== 1 ? 's' : ''} found`}
                            </p>

                            {error && (
                                <div role="alert" className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
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
                                <Card className="bg-white/5 border-white/10 border-dashed p-12">
                                    <p className="text-center text-slate-400">
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
