'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { HistoricalEventRecord } from '@/db/queries/contracts';
import { createHistoricalEvent, deleteHistoricalEvent, updateHistoricalEvent } from '@/app/actions/curation/history';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Edit2 } from 'lucide-react';
import { ConfirmDelete } from '@/app/admin/_components/ConfirmDelete';
import { describeActionError, unwrapAction } from '@/app/admin/_components/actionError';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';

interface PaginationInfo {
    page: number;
    totalPages: number;
    total: number;
    pageSize: number;
}

interface EventsManagerClientProps {
    events: HistoricalEventRecord[];
    pagination: PaginationInfo;
}

/** Canonical `event_category` codes; the action accepts these (and legacy title case). */
const EVENT_CATEGORIES = [
    { value: 'PROPHETIC_ERA', label: 'Prophetic era' },
    { value: 'RASHIDUN', label: 'First four caliphs (11–40 AH)' },
    { value: 'UMAYYAD', label: 'Umayyad' },
    { value: 'ABBASID', label: 'Abbasid' },
    { value: 'SCHOLARLY', label: 'Scholarly' },
    { value: 'MILITARY', label: 'Military' },
    { value: 'POLITICAL', label: 'Political' },
    { value: 'SOCIAL', label: 'Social' },
    { value: 'RELIGIOUS', label: 'Religious' },
    { value: 'SCIENTIFIC', label: 'Scientific' },
    { value: 'CULTURAL', label: 'Cultural' },
    { value: 'ECONOMIC', label: 'Economic' },
];

const categoryLabel = (code: string): string => EVENT_CATEGORIES.find((c) => c.value === code)?.label ?? code;

/** Review states a curator can set; publishing also needs a citation source and a locator or URL (check constraint). */
const VERIFICATION_STATES = [
    { value: 'unverified_seed', label: 'Seed, unverified' },
    { value: 'unverified', label: 'Curator entry, not yet reviewed' },
    { value: 'human_verified', label: 'Reviewed by a curator' },
    { value: 'source_verified', label: 'Checked against the source' },
];

const verificationLabel = (value: string): string => VERIFICATION_STATES.find((state) => state.value === value)?.label ?? value;

const EMPTY_FORM = {
    title: '',
    title_arabic: '',
    description: '',
    year_hijri: '',
    end_year_hijri: '',
    year_gregorian: '',
    category: '',
    significance: '',
    location_name: '',
    verification_status: 'unverified',
    publication_ready: false,
    citation_source: '',
    citation_locator: '',
    citation_url: '',
};

export function EventsManagerClient({ events, pagination }: EventsManagerClientProps) {
    const router = useRouter();
    const [isCreating, setIsCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [formData, setFormData] = useState(EMPTY_FORM);

    const groupedEvents = events.reduce((acc, event) => {
        const category = event.category || 'Uncategorized';
        if (!acc[category]) acc[category] = [];
        acc[category].push(event);
        return acc;
    }, {} as Record<string, HistoricalEventRecord[]>);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setFormError(null);
        try {
            await unwrapAction(createHistoricalEvent(formData));
            setFormData(EMPTY_FORM);
            setIsCreating(false);
            router.refresh();
        } catch (error) {
            setFormError(describeActionError(error, 'Could not create the event. Check the fields and try again.'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingId) return;
        setIsSaving(true);
        setFormError(null);
        try {
            await unwrapAction(updateHistoricalEvent(editingId, formData));
            setFormData(EMPTY_FORM);
            setEditingId(null);
            router.refresh();
        } catch (error) {
            setFormError(describeActionError(error, 'Could not update the event. Check the fields and try again.'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (eventId: string) => {
        await unwrapAction(deleteHistoricalEvent(eventId));
        router.refresh();
    };

    const handleStartEdit = (event: HistoricalEventRecord) => {
        setEditingId(event.id);
        setFormData({
            title: event.title || '',
            title_arabic: event.title_arabic || '',
            description: event.description || '',
            year_hijri: event.year_hijri == null ? '' : String(event.year_hijri),
            year_gregorian: event.year_gregorian == null ? '' : String(event.year_gregorian),
            category: event.category || '',
            significance: event.significance || '',
            location_name: event.location_name || '',
            end_year_hijri: event.end_year_hijri == null ? '' : String(event.end_year_hijri),
            // Editing a seed row takes it out of the seed, so a later seed run never overwrites the curator's change.
            verification_status: event.verification_status === 'unverified_seed' ? 'unverified' : event.verification_status,
            publication_ready: Boolean(event.publication_ready),
            citation_source: event.citation_source || '',
            citation_locator: event.citation_locator || '',
            citation_url: event.citation_url || '',
        });
        setIsCreating(false);
        setFormError(null);
    };

    const getCategoryBadgeColor = (category: string): string => {
        const colors: Record<string, string> = {
            POLITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
            RELIGIOUS: 'bg-green-500/20 text-green-400 border-green-500/30',
            MILITARY: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
            SCIENTIFIC: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            CULTURAL: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
            ECONOMIC: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
            SOCIAL: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
        };
        return colors[category] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Events</h1>
                    <a href="/admin/epochs" className="text-sm text-slate-400 underline underline-offset-4 hover:text-slate-200">Eras</a>
                </div>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
                        setFormError(null);
                        setFormData(EMPTY_FORM);
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    New Event
                </Button>
            </div>

            <SearchFilterBar
                showSearch={false}
                filters={[
                    {
                        key: 'category',
                        label: 'Category',
                        options: [
                            { label: 'All Categories', value: '' },
                            ...EVENT_CATEGORIES,
                        ],
                    },
                ]}
                totalResults={pagination.total}
            />

            {/* Create/Edit Form */}
            {(isCreating || editingId) && (
                <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-white mb-4">
                        {editingId ? 'Edit Event' : 'Create New Event'}
                    </h2>
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4" aria-busy={isSaving}>
                        {formError && (
                            <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                                {formError}
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="title" className="text-slate-300">
                                    Title (English)
                                </Label>
                                <Input
                                    id="title"
                                    value={formData.title}
                                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                    placeholder="e.g., Battle of Badr"
                                    required
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="title_arabic" className="text-slate-300">
                                    Title (Arabic)
                                </Label>
                                <Input
                                    id="title_arabic"
                                    value={formData.title_arabic}
                                    onChange={(e) => setFormData({ ...formData, title_arabic: e.target.value })}
                                    placeholder="e.g., غزوة بدر"
                                    lang="ar"
                                    dir="rtl"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                        </div>

                        <div>
                            <Label htmlFor="description" className="text-slate-300">
                                Description
                            </Label>
                            <Textarea
                                id="description"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Detailed description of the event"
                                required
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="category" className="text-slate-300">
                                    Category
                                </Label>
                                <select
                                    id="category"
                                    value={formData.category}
                                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                    required
                                    className="w-full mt-2 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2"
                                >
                                    <option value="">Select Category</option>
                                    {EVENT_CATEGORIES.map((cat) => (
                                        <option key={cat.value} value={cat.value}>
                                            {cat.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor="location" className="text-slate-300">
                                    Location
                                </Label>
                                <Input
                                    id="location"
                                    value={formData.location_name}
                                    onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                                    placeholder="e.g., Badr"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <Label htmlFor="year_gregorian" className="text-slate-300">
                                    Gregorian Year
                                </Label>
                                <Input
                                    id="year_gregorian"
                                    type="number"
                                    value={formData.year_gregorian}
                                    onChange={(e) => setFormData({ ...formData, year_gregorian: e.target.value })}
                                    placeholder="e.g., 625"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="year_hijri" className="text-slate-300">
                                    Hijri Year
                                </Label>
                                <Input
                                    id="year_hijri"
                                    type="number"
                                    value={formData.year_hijri}
                                    onChange={(e) => setFormData({ ...formData, year_hijri: e.target.value })}
                                    placeholder="e.g., 2"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="significance" className="text-slate-300">
                                    Significance
                                </Label>
                                <Input
                                    id="significance"
                                    value={formData.significance}
                                    onChange={(e) => setFormData({ ...formData, significance: e.target.value })}
                                    placeholder="e.g., First major victory"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                        </div>

                        <fieldset className="grid grid-cols-1 gap-4 border-t border-slate-800 pt-4 md:grid-cols-2">
                            <legend className="text-sm font-medium text-slate-300">Review and citation</legend>
                            {editingId && events.find((event) => event.id === editingId)?.verification_status === 'unverified_seed' && (
                                <p className="text-xs text-slate-400 md:col-span-2">
                                    This is seed data. Saving an edit takes it out of the seed, so later seed runs leave it alone.
                                </p>
                            )}
                            <div>
                                <Label htmlFor="verification_status" className="text-slate-300">Review state</Label>
                                <select
                                    id="verification_status"
                                    value={formData.verification_status}
                                    onChange={(e) => setFormData({ ...formData, verification_status: e.target.value })}
                                    className="w-full mt-2 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2"
                                >
                                    {VERIFICATION_STATES.map((state) => (
                                        <option key={state.value} value={state.value}>{state.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor="end_year_hijri" className="text-slate-300">End year (Hijri)</Label>
                                <Input
                                    id="end_year_hijri"
                                    type="number"
                                    value={formData.end_year_hijri}
                                    onChange={(e) => setFormData({ ...formData, end_year_hijri: e.target.value })}
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="citation_source" className="text-slate-300">Citation: work</Label>
                                <Input
                                    id="citation_source"
                                    value={formData.citation_source}
                                    onChange={(e) => setFormData({ ...formData, citation_source: e.target.value })}
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="citation_locator" className="text-slate-300">Citation: volume and page</Label>
                                <Input
                                    id="citation_locator"
                                    value={formData.citation_locator}
                                    onChange={(e) => setFormData({ ...formData, citation_locator: e.target.value })}
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="citation_url" className="text-slate-300">Citation: URL</Label>
                                <Input
                                    id="citation_url"
                                    type="url"
                                    value={formData.citation_url}
                                    onChange={(e) => setFormData({ ...formData, citation_url: e.target.value })}
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <label className="flex items-center gap-2 self-end text-sm text-slate-300">
                                <input
                                    type="checkbox"
                                    checked={formData.publication_ready}
                                    onChange={(e) => setFormData({ ...formData, publication_ready: e.target.checked })}
                                />
                                Ready to publish (needs a reviewed state and a citation)
                            </label>
                        </fieldset>

                        <div className="flex gap-3">
                            <Button type="submit" disabled={isSaving} className="bg-emerald-600 hover:bg-emerald-700">
                                {isSaving ? 'Saving...' : editingId ? 'Update' : 'Create'}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                disabled={isSaving}
                                onClick={() => {
                                    setIsCreating(false);
                                    setEditingId(null);
                                    setFormError(null);
                                }}
                                className="border-slate-600 text-slate-300"
                            >
                                Cancel
                            </Button>
                        </div>
                    </form>
                </Card>
            )}

            {/* Events List Grouped by Category */}
            <div className="space-y-6">
                {(Object.entries(groupedEvents) as [string, HistoricalEventRecord[]][]).map(([category, categoryEvents]) => (
                    <div key={category}>
                        <h2 className="text-xl font-semibold text-white mb-3">{categoryLabel(category)}</h2>
                        <div className="space-y-3">
                            {categoryEvents.map((event) => (
                                <Card key={event.id} className="bg-slate-900 border-slate-700 p-6">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <h3 className="text-lg font-semibold text-white">{event.title}</h3>
                                                {event.category && (
                                                    <Badge className={getCategoryBadgeColor(event.category)}>
                                                        {categoryLabel(event.category)}
                                                    </Badge>
                                                )}
                                            </div>
                                            {event.title_arabic && (
                                                <p className="text-sm text-slate-400 mb-2 font-arabic" lang="ar" dir="rtl">{event.title_arabic}</p>
                                            )}
                                            <p className="text-sm text-slate-300 mb-3">{event.description}</p>
                                            <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                                                {event.year_gregorian != null && (
                                                    <span>{event.year_gregorian} CE</span>
                                                )}
                                                {event.year_hijri != null && (
                                                    <span>{event.year_hijri} AH</span>
                                                )}
                                                {event.location_name && (
                                                    <span>{event.location_name}</span>
                                                )}
                                                <span>{verificationLabel(event.verification_status)}{event.publication_ready ? ', published' : ''}</span>
                                                {event.significance && (
                                                    <span>Significance: {event.significance}</span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex items-start gap-2">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleStartEdit(event)}
                                                aria-label={`Edit ${event.title}`}
                                                className="border-slate-600 text-slate-300"
                                            >
                                                <Edit2 className="w-4 h-4" aria-hidden="true" />
                                            </Button>
                                            <ConfirmDelete
                                                itemName="event"
                                                consequence={`Retire "${event.title}"? It is hidden from every page. Nothing is erased and an audit record is kept.`}
                                                onConfirm={() => handleDelete(event.id)}
                                            />
                                        </div>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                ))}

                {events.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">
                            No events found. Choose New Event to create one.
                        </p>
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
