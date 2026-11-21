'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Download, X } from 'lucide-react';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';
import { getSourceFilterOptions } from '@/lib/constants/sources';
import { HADITH_TRADITION_OPTIONS } from '@/lib/constants/traditions';
import { ArabicText } from '@/components/ArabicText';
import { TraditionBadge } from '@/components/TraditionBadge';

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

interface HadithManagerClientProps {
    hadiths: HadithListItem[];
    pagination: PaginationInfo;
}

export function HadithManagerClient({ hadiths, pagination }: HadithManagerClientProps) {
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
    const [exportTradition, setExportTradition] = useState('');
    const [exportSource, setExportSource] = useState('');

    const toggleField = (key: string) => setExportFields((prev) => ({ ...prev, [key]: !prev[key] }));
    const toggleEdge = (key: string) => setExportEdges((prev) => ({ ...prev, [key]: !prev[key] }));

    const handleExport = useCallback(async () => {
        setIsExporting(true);
        setError(null);
        try {
            const query = new URLSearchParams({
                fields: Object.entries(exportFields).filter(([, on]) => on).map(([key]) => key).join(','),
                edges: Object.entries(exportEdges).filter(([, on]) => on).map(([key]) => key).join(','),
            });
            if (exportSource) query.set('source', exportSource);
            if (exportTradition) query.set('tradition', exportTradition);
            const response = await fetch(`/api/export/hadiths?${query}`);
            if (response.status === 204) {
                setError('No hadiths matched the selected filters.');
                return;
            }
            if (!response.ok) {
                setError(response.status === 401 ? 'Sign in again to export.' : 'Export failed. Try again.');
                return;
            }
            const url = URL.createObjectURL(await response.blob());
            const a = document.createElement('a');
            a.href = url;
            a.download = `hadith-export-${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            setError('Export failed. Try again.');
        } finally {
            setIsExporting(false);
        }
    }, [exportFields, exportEdges, exportTradition, exportSource]);

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-3xl font-bold text-ink">Hadiths</h1>
                <div className="flex gap-3">
                    <Button
                        onClick={() => setShowExport(true)}
                        variant="outline"
                        className="border-rule text-ink hover:text-ink hover:bg-sunken"
                    >
                        <Download className="w-4 h-4 mr-2" />
                        Export CSV
                    </Button>
                </div>
            </div>

            {showExport && (
                <Card className="pb-6 mb-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold text-ink">Export Hadiths to CSV</h2>
                        <Button size="sm" variant="ghost" onClick={() => setShowExport(false)} aria-label="Close export panel" className="text-ink-muted hover:text-ink">
                            <X className="w-4 h-4" aria-hidden="true" />
                        </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Filters */}
                        <div>
                            <h3 className="text-sm font-medium text-ink mb-3">Export Filters</h3>
                            <div className="space-y-3">
                                <div>
                                    <Label htmlFor="export-tradition" className="text-xs text-ink-muted">Tradition</Label>
                                    <select id="export-tradition" value={exportTradition} onChange={(e) => setExportTradition(e.target.value)}
                                        className="w-full min-h-11 mt-1 px-3 py-2 bg-surface border border-control text-ink text-sm">
                                        {HADITH_TRADITION_OPTIONS.map((opt) => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <Label htmlFor="export-source" className="text-xs text-ink-muted">Source</Label>
                                    <select id="export-source" value={exportSource} onChange={(e) => setExportSource(e.target.value)}
                                        className="w-full min-h-11 mt-1 px-3 py-2 bg-surface border border-control text-ink text-sm">
                                        {getSourceFilterOptions().map((opt) => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Metadata Fields */}
                        <div>
                            <h3 className="text-sm font-medium text-ink mb-3">Metadata Fields</h3>
                            <div className="space-y-2">
                                {Object.entries(exportFields).map(([key, checked]) => (
                                    <label key={key} className="flex items-center gap-2 text-sm text-ink cursor-pointer">
                                        <input type="checkbox" checked={checked} onChange={() => toggleField(key)}
                                            className="border-rule bg-sunken text-accent" />
                                        {key.replace(/_/g, ' ')}
                                    </label>
                                ))}
                            </div>
                        </div>

                        {/* Edge Data */}
                        <div>
                            <h3 className="text-sm font-medium text-ink mb-3">Related Data (Edges)</h3>
                            <div className="space-y-2">
                                {([
                                    ['narrators', 'Narrators & reliability'],
                                    ['commentaries', 'Commentaries'],
                                    ['variations', 'Matn variations (Arabic & English)'],
                                    ['school', 'School of thought'],
                                ] as const).map(([key, label]) => (
                                    <label key={key} className="flex items-center gap-2 text-sm text-ink cursor-pointer">
                                        <input type="checkbox" checked={exportEdges[key]} onChange={() => toggleEdge(key)}
                                            className="border-rule bg-sunken text-accent" />
                                        {label}
                                    </label>
                                ))}
                            </div>
                            <p className="text-xs text-ink-muted mt-3">
                                Including edges increases export time for large datasets.
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-rule">
                        <Button variant="outline" onClick={() => setShowExport(false)} className="border-rule text-ink">
                            Cancel
                        </Button>
                        <Button onClick={handleExport} disabled={isExporting} aria-busy={isExporting} className="bg-accent text-on-accent hover:bg-ink hover:text-paper">
                            <Download className="w-4 h-4 mr-2" />
                            {isExporting ? 'Exporting...' : 'Download CSV'}
                        </Button>
                    </div>
                </Card>
            )}

            {error && (
                <div role="alert" className="mb-4 p-3 bg-transparent border border-danger text-danger text-sm flex items-center justify-between">
                    <span>{error}</span>
                    <button type="button" onClick={() => setError(null)} aria-label="Dismiss error" className="text-danger hover:text-danger ml-4">
                        <X className="w-4 h-4" aria-hidden="true" />
                    </button>
                </div>
            )}

            <SearchFilterBar
                searchPlaceholder="Search hadiths by title, topic, or text..."
                totalResults={pagination.total}
                filters={[
                    {
                        key: 'tradition',
                        label: 'Tradition',
                        options: HADITH_TRADITION_OPTIONS,
                        legacyKeys: ['school'],
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
                        <Card key={hadith.id} className="pb-6">
                            <div className="flex items-start justify-between gap-6">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-3 mb-2">
                                        <h3 className="text-lg font-semibold text-ink">{hadith.title}</h3>
                                        {hadith.tradition && (
                                            <TraditionBadge tradition={hadith.tradition} />
                                        )}
                                    </div>
                                    {referenceParts.length > 0 && (
                                        <p className="text-sm text-ink-muted">
                                            {referenceParts.map((part, i) => (
                                                <span key={i}>
                                                    {i > 0 && <span className="text-ink-muted mx-2">·</span>}
                                                    <span className={i === 0 ? 'text-ink' : ''}>{part}</span>
                                                </span>
                                            ))}
                                        </p>
                                    )}
                                    {matnAr && (
                                        <ArabicText as="p" className="mt-3 line-clamp-2 text-lg text-ink">
                                            {matnAr}
                                        </ArabicText>
                                    )}
                                </div>

                                <div className="flex gap-2 shrink-0">
                                    <Button asChild size="sm" variant="outline" className="border-rule bg-transparent text-ink hover:bg-sunken">
                                        <Link href={`/hadith/${hadith.id}`} aria-label={`View details: ${hadith.title}`}>
                                            Open
                                        </Link>
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    );
                })}

                {hadiths.length === 0 && (
                    <Card className="border-rule border-dashed py-8">
                        <p className="text-center text-ink-muted">No hadiths match the current filters.</p>
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
