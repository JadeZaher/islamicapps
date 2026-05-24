'use client';

import { useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createHadith, calculateAutoGrade, calculateTransmissionType, exportHadiths, type ExportConfig } from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, BarChart3, Download, X } from 'lucide-react';
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
    display_grade?: string;
    transmission_type?: string;
    tradition?: string;
    hadith_no?: string;
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
    const [isCreating, setIsCreating] = useState(false);
    const [formData, setFormData] = useState({
        title: '',
        primary_topic: '',
    });

    const getGradeBadgeColor = (grade: string) => {
        switch (grade) {
            case 'SAHIH':
                return 'bg-green-500/20 text-green-400 border-green-500/30';
            case 'HASAN':
                return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
            case 'DAIF':
                return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
            case 'MAWDU':
                return 'bg-red-500/20 text-red-400 border-red-500/30';
            default:
                return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    const [error, setError] = useState<string | null>(null);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setError(null);
            const hadithId = await createHadith(formData);
            setFormData({ title: '', primary_topic: '' });
            setIsCreating(false);
            router.refresh();
            router.push(`/hadith/${hadithId}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create hadith');
        }
    };

    const handleRunAutoAnalysis = async (hadithId: string) => {
        try {
            await calculateAutoGrade(hadithId);
            await calculateTransmissionType(hadithId);
            router.refresh();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Auto-analysis failed');
        }
    };

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
        display_grade: true,
        transmission_type: false,
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
    const [exportGrade, setExportGrade] = useState('');

    const toggleField = (key: string) => setExportFields((prev) => ({ ...prev, [key]: !prev[key] }));
    const toggleEdge = (key: string) => setExportEdges((prev) => ({ ...prev, [key]: !prev[key] }));

    const handleExport = useCallback(async () => {
        setIsExporting(true);
        try {
            const config: ExportConfig = {
                filters: {
                    source: exportSource || undefined,
                    grade: exportGrade || undefined,
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
            // Build CSV
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
    }, [exportFields, exportEdges, exportSchool, exportSource, exportGrade]);

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Hadith Manager</h1>
                    <p className="text-slate-400 mt-1">Manage Hadith entries and grading</p>
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
                    <Button
                        onClick={() => setIsCreating(true)}
                        className="bg-emerald-600 hover:bg-emerald-700"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        New Hadith
                    </Button>
                </div>
            </div>

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-white mb-4">Create New Hadith</h2>
                    <form onSubmit={handleCreate} className="space-y-4">
                        <div>
                            <Label htmlFor="title" className="text-slate-300">Title</Label>
                            <Input
                                id="title"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                placeholder="e.g., Hadith of Jibril"
                                required
                                className="bg-slate-800 border-slate-700 text-white"
                            />
                        </div>
                        <div>
                            <Label htmlFor="topic" className="text-slate-300">Primary Topic</Label>
                            <Textarea
                                id="topic"
                                value={formData.primary_topic}
                                onChange={(e) => setFormData({ ...formData, primary_topic: e.target.value })}
                                placeholder="e.g., Pillars of Islam, Iman, Ihsan"
                                required
                                className="bg-slate-800 border-slate-700 text-white"
                            />
                        </div>
                        <div className="flex gap-3">
                            <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700">
                                Create
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setIsCreating(false)}
                                className="border-slate-600 text-slate-300"
                            >
                                Cancel
                            </Button>
                        </div>
                    </form>
                </Card>
            )}

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
                                <div>
                                    <Label className="text-xs text-slate-400">Grade</Label>
                                    <select value={exportGrade} onChange={(e) => setExportGrade(e.target.value)}
                                        className="w-full mt-1 px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white text-sm">
                                        <option value="">All Grades</option>
                                        <option value="SAHIH">Sahih</option>
                                        <option value="HASAN">Hasan</option>
                                        <option value="DAIF">Daif</option>
                                        <option value="MAWDU">Mawdu</option>
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
                    {
                        key: 'grade',
                        label: 'Grade',
                        options: [
                            { label: 'All Grades', value: '' },
                            { label: 'Sahih', value: 'SAHIH' },
                            { label: 'Hasan', value: 'HASAN' },
                            { label: 'Daif', value: 'DAIF' },
                            { label: 'Mawdu', value: 'MAWDU' },
                        ],
                    },
                ]}
            />

            {/* Hadith List */}
            <div className="space-y-4">
                {hadiths.map((hadith) => (
                    <Card key={hadith.id} className="bg-slate-900 border-slate-700 p-6">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
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
                                    {hadith.display_grade && (
                                        <Badge className={getGradeBadgeColor(hadith.display_grade)}>
                                            {hadith.display_grade}
                                        </Badge>
                                    )}
                                    {hadith.transmission_type === 'MUTAWATIR' && (
                                        <Badge className="bg-amber-500/20 text-amber-400">
                                            Mutawatir
                                        </Badge>
                                    )}
                                </div>
                                <p className="text-sm text-slate-400">
                                    {hadith.source && <span className="text-slate-300">{hadith.source}</span>}
                                    {hadith.source && hadith.primary_topic && ' — '}
                                    {hadith.primary_topic}
                                </p>
                                {hadith.text_english && (
                                    <p className="text-sm text-slate-300/80 mt-2 line-clamp-2 leading-relaxed">
                                        {hadith.text_english}
                                    </p>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleRunAutoAnalysis(hadith.id)}
                                    className="border-slate-600 text-slate-300"
                                >
                                    <BarChart3 className="w-4 h-4 mr-2" />
                                    Auto-Analysis
                                </Button>
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
                ))}

                {hadiths.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">
                            No Hadiths yet. Click &ldquo;New Hadith&rdquo; to create one.
                        </p>
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
