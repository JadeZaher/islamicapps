'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { searchParallels } from '@/app/actions/comparative-actions';
import { CrossCulturalParallelCard } from '@/components/CrossCulturalParallelCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

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
    { value: 'MASKUT_ANHU', label: 'Maskut Anhu (Unknown)' },
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

// Regional context table - no external map needed
const REGIONAL_CONTEXT = [
    {
        school: 'Damascus (Syria)',
        traditions: ['Judaism', 'Christianity'],
        narrators: ["Ka'b al-Ahbar", 'Wahb ibn Munabbih'],
        notes: 'Primary conduit for Isra\'iliyyat. Ka\'b al-Ahbar was a Jewish convert who settled in Damascus under the Umayyads.',
    },
    {
        school: 'Kufa (Iraq)',
        traditions: ['Judaism', 'Zoroastrianism'],
        narrators: ['Salman al-Farisi', 'Ibn Mas\'ud students'],
        notes: 'Persian cultural contact. Active Jewish diaspora communities. Ra\'y methodology may have been influenced by both.',
    },
    {
        school: 'Basra (Iraq)',
        traditions: ['Zoroastrianism', 'Manichaeism'],
        narrators: ['Al-Hasan al-Basri'],
        notes: 'Gateway to Persia. Zoroastrian converts common in the early Islamic period. Ascetic themes may show Zoroastrian/Manichaean parallels.',
    },
    {
        school: 'Medina (Hijaz)',
        traditions: ['Judaism', 'Christianity'],
        narrators: ['Abdullah ibn Salam'],
        notes: 'Jewish tribes of Banu Qaynuqa, Banu Nadir, Banu Qurayza had historical presence. Christian contact via trade routes.',
    },
    {
        school: 'Khorasan / Persia',
        traditions: ['Zoroastrianism'],
        narrators: ['Late Tabi\'in chains'],
        notes: 'Abbasid-era expansion. Zoroastrian conceptual vocabulary entered Islamic theological discourse during translation movement.',
    },
    {
        school: 'Yemen',
        traditions: ['Judaism', 'Christianity'],
        narrators: ['Wahb ibn Munabbih', 'Ka\'b al-Ahbar (origin)'],
        notes: 'Wahb ibn Munabbih was of Yemeni/South Arabian origin with Jewish background. Yemen had ancient Jewish and Christian communities.',
    },
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

    const applyFilters = (newFilters: typeof filters) => {
        setFilters(newFilters);
        startTransition(async () => {
            const results = await searchParallels({
                tradition_id: newFilters.tradition_id || undefined,
                parallel_type: (newFilters.parallel_type as any) || undefined,
                isra_iliyyat_status: (newFilters.isra_iliyyat_status as any) || undefined,
                motif_category: (newFilters.motif_category as any) || undefined,
                confidence_level: (newFilters.confidence_level as any) || undefined,
            });
            setParallels(results);
        });
    };

    // Stats: count by tradition
    const statsByTradition = traditions.map((t) => ({
        tradition: t,
        count: stats.filter((s: any) => s.tradition === t.name).reduce((a: number, b: any) => a + Number(b.count), 0),
    }));

    return (
        <div className="min-h-screen bg-slate-950 py-12 px-4">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-10">
                    <Link href="/" className="inline-flex items-center gap-2 text-cyan-300 hover:text-cyan-200 mb-4">
                        ← Back to Home
                    </Link>
                    <h1 className="text-4xl font-bold text-white mb-2">Comparative Religious Studies</h1>
                    <p className="text-slate-400 max-w-2xl">
                        Explore cross-cultural parallels between hadith narratives and Jewish, Christian, and Zoroastrian traditions.
                        Examine Isra'iliyyat transmission, regional cultural contact, and the scholarly classification of these parallels.
                    </p>
                </div>

                {/* Overview stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <Card className="bg-white/5 border-white/10 p-4">
                        <p className="text-2xl font-bold text-white">{initialParallels.length}</p>
                        <p className="text-sm text-slate-400">Total Parallels</p>
                    </Card>
                    {statsByTradition.slice(0, 3).map(({ tradition, count }) => (
                        <Card key={tradition.id} className="bg-white/5 border-white/10 p-4">
                            <p className="text-2xl font-bold text-white">{count}</p>
                            <p className="text-sm text-slate-400">{tradition.name} parallels</p>
                        </Card>
                    ))}
                </div>

                {/* View toggle */}
                <div className="flex gap-3 mb-6">
                    <Button
                        onClick={() => setActiveView('results')}
                        className={activeView === 'results' ? 'bg-cyan-700 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'}
                    >
                        Browse Parallels
                    </Button>
                    <Button
                        onClick={() => setActiveView('regional')}
                        className={activeView === 'regional' ? 'bg-amber-700 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'}
                    >
                        Regional Context
                    </Button>
                </div>

                {activeView === 'regional' ? (
                    /* Regional Context View */
                    <div className="space-y-4">
                        <p className="text-slate-400 text-sm mb-4">
                            The following table shows how different religious traditions were geographically positioned relative to
                            major hadith transmission centers, explaining the vectors through which cross-cultural influences entered
                            the hadith corpus.
                        </p>
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
                    </div>
                ) : (
                    /* Parallel Browse View */
                    <div className="flex gap-6">
                        {/* Filter sidebar */}
                        <div className="w-56 flex-shrink-0 space-y-5">
                            <Card className="bg-white/5 border-white/10 p-4">
                                <h3 className="text-sm font-semibold text-white mb-3">Tradition</h3>
                                <div className="space-y-1.5">
                                    <button
                                        onClick={() => applyFilters({ ...filters, tradition_id: '' })}
                                        className={`w-full text-left text-sm px-2 py-1.5 rounded transition-colors ${!filters.tradition_id ? 'bg-cyan-700/50 text-white' : 'text-slate-400 hover:text-white'}`}
                                    >
                                        All Traditions
                                    </button>
                                    {traditions.map((t) => (
                                        <button key={t.id}
                                            onClick={() => applyFilters({ ...filters, tradition_id: t.id })}
                                            className={`w-full text-left text-sm px-2 py-1.5 rounded transition-colors ${filters.tradition_id === t.id ? 'bg-cyan-700/50 text-white' : 'text-slate-400 hover:text-white'}`}
                                        >
                                            {t.name}
                                        </button>
                                    ))}
                                </div>
                            </Card>

                            <Card className="bg-white/5 border-white/10 p-4">
                                <h3 className="text-sm font-semibold text-white mb-3">Parallel Type</h3>
                                <select
                                    value={filters.parallel_type}
                                    onChange={(e) => applyFilters({ ...filters, parallel_type: e.target.value })}
                                    className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1.5 text-sm"
                                >
                                    {PARALLEL_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                                </select>
                            </Card>

                            <Card className="bg-white/5 border-white/10 p-4">
                                <h3 className="text-sm font-semibold text-white mb-3">Isra'iliyyat Status</h3>
                                <select
                                    value={filters.isra_iliyyat_status}
                                    onChange={(e) => applyFilters({ ...filters, isra_iliyyat_status: e.target.value })}
                                    className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1.5 text-sm"
                                >
                                    {ISRA_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                                </select>
                            </Card>

                            <Card className="bg-white/5 border-white/10 p-4">
                                <h3 className="text-sm font-semibold text-white mb-3">Motif Category</h3>
                                <select
                                    value={filters.motif_category}
                                    onChange={(e) => applyFilters({ ...filters, motif_category: e.target.value })}
                                    className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1.5 text-sm"
                                >
                                    {MOTIF_CATEGORIES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                                </select>
                            </Card>

                            <Card className="bg-white/5 border-white/10 p-4">
                                <h3 className="text-sm font-semibold text-white mb-3">Confidence</h3>
                                <select
                                    value={filters.confidence_level}
                                    onChange={(e) => applyFilters({ ...filters, confidence_level: e.target.value })}
                                    className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1.5 text-sm"
                                >
                                    {CONFIDENCE_LEVELS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                                </select>
                            </Card>

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
                        <div className="flex-1">
                            <p className="text-sm text-slate-400 mb-4">
                                {isPending ? 'Searching...' : `${parallels.length} parallel${parallels.length !== 1 ? 's' : ''} found`}
                            </p>

                            {parallels.length > 0 ? (
                                <div className="space-y-4">
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
                                        {isPending ? 'Searching...' : 'No parallels found. Add some via the Admin → Comparative Studies section.'}
                                    </p>
                                </Card>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
