'use client';

import { useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { exportHadiths, type ExportConfig } from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Download, X } from 'lucide-react';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';
import { getSourceFilterOptions } from '@/lib/constants/sources';

interface PaginationInfo {
    page: number;
    totalPages: number;
    total: number;
    pageSize: number;
}

interface HadithListItem {
    id: string;
    title: string;
    source?: string;
    primary_topic?: string;
    text_english?: string;
    text_arabic?: string;
    tradition?: string;
    hadith_no?: string;
    chapter?: string;
    chapter_no?: string;
    volume?: string;
    matn_ar?: string;
    matn_en?: string;
    text_ar?: string;
    text_en?: string;
}

const SCHOOL_OPTIONS = [
    { label: 'All Schools', value: '' },
    { label: 'Sunni', value: 'Sunni' },
    { label: 'Twelver Shia', value: 'Shia Imami' },
    { label: 'Zaydi Shia', value: 'Shia Zaydi' },
    { label: 'Ibadi', value: 'Ibadi' },
];

interface HadithManagerClientProps {
    hadiths: HadithListItem[];
    pagination: PaginationInfo;
}

export function HadithManagerClient({ hadiths, pagination }: HadithManagerClientProps) {
    const router = useRouter();
    const searchParams = useSearchParams();

    const [error, setError] = useState<string | null>(null);

    // ── Export ──
    const [showExport, setShowExport] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [exportFields, setExportFields] = useState<Record<string, boolean>>({
        id: true,
        title: true,
        source: true,
        hadith_no: true,
        primary_topic: true,
        text_english: true,
        text_arabic: false,
        tradition: true,
    });
    const [exportEdges, setExportEdges] = useState<Record<string, boolean>>({
        narrators: false,
        commentaries: false,
        variations: false,
        school: false,
    });
    const [exportSchool, setExportSchool] = useState('');
    const [exportSource, setExportSource] = useState('');

    const toggleField = (key: string) => setExportFields((prev) => ({ ...prev, [key]: !prev[key] }));
    const toggleEdge = (key: string) => setExportEdges((prev) => ({ ...prev, [key]: !prev[key] }));

    const handleExport = useCallback(async () => {
        setIsExporting(true);
        try {
            const config: ExportConfig = {
                filters: {
                    source: exportSource || undefined,
                    school: exportSchool || undefined,
                },
                fields: Object.entries(exportFields).filter(([, v]) => v).map(([k]) => k),
                edges: Object.entries(exportEdges).filter(([, v]) => v).map(([k]) => k),
            };
            const rows = await exportHadiths(config);
            if (rows.length === 0) {
                setError('No hadiths matched the selected filters.');
                return;
            }
            const headers = Object.keys(rows[0]);
            const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
            const csv = [
                headers.map(escape).join(','),
                ...rows.map((row) => headers.map((h) => escape(row[h] || '')).join(',')),
            ].join('\n');

            const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `hadith-export-${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } finally {
            setIsExporting(false);
        }
    }, [exportFields, exportEdges, exportSchool, exportSource]);

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Hadith Manager</h1>
                    <p className="text-slate-400 mt-1">Browse and export Hadith entries. Manual grading and authoring are paused pending a v2 grading-UX redesign.</p>
                </div>
                <div className="flex gap-3">
                    <Button
                        onClick={() => setShowExport(true)}
                        variant="outline"
                        className="border-slate-600 text-slate-300 hover:text-white hover:bg-slate-800"
                    >
                        <Download className="w-4 h-4 mr-2" />
                        Export CSV
                    </Button>
                </div>
            </div>

            {showExport && (
                <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold text-white">Export Hadiths to CSV</h2>
                        <Button size="sm" variant="ghost" onClick={() => setShowExport(false)} className="text-slate-400 hover:text-white">
                            <X className="w-4 h-4" />
                        </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Filters */}
                        <div>
                            <h3 className="text-sm font-medium text-slate-300 mb-3">Export Filters</h3>
                            <div className="space-y-3">
                                <div>
                                    <Label className="text-xs text-slate-400">School</Label>
                                    <select value={exportSchool} onChange={(e) => setExportSchool(e.target.value)}
                                        className="w-full mt-1 px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white text-sm">
                                        {SCHOOL_OPTIONS.map((opt) => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <Label className="text-xs text-slate-400">Source</Label>
                                    <select value={exportSource} onChange={(e) => setExportSource(e.target.value)}
                                        className="w-full mt-1 px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white text-sm">
                                        {getSourceFilterOptions().map((opt) => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Metadata Fields */}
                        <div>
                            <h3 className="text-sm font-medium text-slate-300 mb-3">Metadata Fields</h3>
                            <div className="space-y-2">
                                {Object.entries(exportFields).map(([key, checked]) => (
                                    <label key={key} className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                                        <input type="checkbox" checked={checked} onChange={() => toggleField(key)}
                                            className="rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/25" />
                                        {key.replace(/_/g, ' ')}
                                    </label>
                                ))}
                            </div>
                        </div>

                        {/* Edge Data */}
                        <div>
                            <h3 className="text-sm font-medium text-slate-300 mb-3">Related Data (Edges)</h3>
                            <div className="space-y-2">
                                {([
                                    ['narrators', 'Narrators & reliability'],
                                    ['commentaries', 'Commentaries'],
                                    ['variations', 'Matn variations (Arabic & English)'],
                                    ['school', 'School of thought'],
                                ] as const).map(([key, label]) => (
                                    <label key={key} className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                                        <input type="checkbox" checked={exportEdges[key]} onChange={() => toggleEdge(key)}
                                            className="rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/25" />
                                        {label}
                                    </label>
                                ))}
                            </div>
                            <p className="text-xs text-slate-500 mt-3">
                                Including edges increases export time for large datasets.
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-slate-700">
                        <Button variant="outline" onClick={() => setShowExport(false)} className="border-slate-600 text-slate-300">
                            Cancel
                        </Button>
                        <Button onClick={handleExport} disabled={isExporting} className="bg-emerald-600 hover:bg-emerald-700">
                            <Download className="w-4 h-4 mr-2" />
                            {isExporting ? 'Exporting...' : 'Download CSV'}
                        </Button>
                    </div>
                </Card>
            )}

            {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center justify-between">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">&times;</button>
                </div>
            )}

            <SearchFilterBar
                searchPlaceholder="Search hadiths by title, topic, or text..."
                totalResults={pagination.total}
                filters={[
                    {
                        key: 'school',
                        label: 'School',
                        options: SCHOOL_OPTIONS,
                    },
                    {
                        key: 'source',
                        label: 'Source',
                        options: getSourceFilterOptions(),
                    },
                ]}
            />

            {/* Hadith List */}
            <div className="space-y-4">
                {hadiths.map((hadith) => {
                    // Prefer matn (prophetic narrative only) over text (full row incl. isnad).
                    // matn_ar covers ~36% of rows; text_ar covers 100%, so this falls back gracefully.
                    const matnAr = hadith.matn_ar || hadith.text_ar || hadith.text_arabic || '';
                    const referenceParts = [
                        hadith.source,
                        hadith.hadith_no ? `#${hadith.hadith_no}` : null,
                        hadith.chapter || hadith.primary_topic,
                        hadith.volume ? `Vol. ${hadith.volume}` : null,
                    ].filter(Boolean);

                    return (
                        <Card key={hadith.id} className="bg-slate-900 border-slate-700 p-6">
                            <div className="flex items-start justify-between gap-6">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-3 mb-2">
                                        <h3 className="text-lg font-semibold text-white">{hadith.title}</h3>
                                        {hadith.tradition && (
                                            <Badge className={
                                                hadith.tradition === 'Shia Imami'
                                                    ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                                                    : hadith.tradition === 'Shia Zaydi'
                                                        ? 'bg-violet-500/20 text-violet-400 border-violet-500/30'
                                                        : hadith.tradition === 'Ibadi'
                                                            ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                                                            : 'bg-teal-500/20 text-teal-400 border-teal-500/30'
                                            }>
                                                {hadith.tradition === 'Shia Imami' ? 'Twelver Shia'
                                                    : hadith.tradition === 'Shia Zaydi' ? 'Zaydi Shia'
                                                    : hadith.tradition}
                                            </Badge>
                                        )}
                                    </div>
                                    {referenceParts.length > 0 && (
                                        <p className="text-sm text-slate-400">
                                            {referenceParts.map((part, i) => (
                                                <span key={i}>
                                                    {i > 0 && <span className="text-slate-600 mx-2">·</span>}
                                                    <span className={i === 0 ? 'text-slate-300' : ''}>{part}</span>
                                                </span>
                                            ))}
                                        </p>
                                    )}
                                    {matnAr && (
                                        <p
                                            dir="rtl"
                                            lang="ar"
                                            className="text-base text-slate-200 mt-3 line-clamp-2 leading-loose font-arabic"
                                        >
                                            {matnAr}
                                        </p>
                                    )}
                                </div>

                                <div className="flex gap-2 shrink-0">
                                    <Button
                                        size="sm"
                                        onClick={() => router.push(`/hadith/${hadith.id}`)}
                                        className="bg-blue-600 hover:bg-blue-700"
                                    >
                                        View Details
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    );
                })}

                {hadiths.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">No hadiths match the current filters.</p>
                    </Card>
                )}

                <PaginationControls
                    page={pagination.page}
                    totalPages={pagination.totalPages}
                    total={pagination.total}
                    pageSize={pagination.pageSize}
                    onPageChange={(p) => {
                        const params = new URLSearchParams(searchParams.toString());
                        params.set('page', String(p));
                        router.push(`?${params.toString()}`);
                    }}
                />
            </div>
        </div>
    );
}
