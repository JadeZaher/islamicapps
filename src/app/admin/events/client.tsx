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
            POLITICAL: 'bg-transparent text-danger border-danger',
            RELIGIOUS: 'bg-sunken text-accent border-rule',
            MILITARY: 'bg-sunken text-ink-muted border-rule',
            SCIENTIFIC: 'bg-sunken text-ink-muted border-rule',
            CULTURAL: 'bg-accent-wash text-accent border-accent',
            ECONOMIC: 'bg-sunken text-ink-muted border-rule',
            SOCIAL: 'bg-sunken text-ink-muted border-rule',
        };
        return colors[category] || 'bg-sunken text-ink-muted border-gray-500/30';
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-ink">Events</h1>
                    <a href="/admin/epochs" className="text-sm text-ink-muted underline underline-offset-4 hover:text-ink">Eras</a>
                </div>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
                        setFormError(null);
                        setFormData(EMPTY_FORM);
                    }}
                    className="bg-accent text-on-accent hover:bg-ink hover:text-paper"
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
                <Card className="pb-6 mb-6">
                    <h2 className="text-xl font-semibold text-ink mb-4">
                        {editingId ? 'Edit Event' : 'Create New Event'}
                    </h2>
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4" aria-busy={isSaving}>
                        {formError && (
                            <div role="alert" className="border border-danger bg-transparent p-3 text-sm text-danger">
                                {formError}
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="title" className="text-ink">
                                    Title (English)
                                </Label>
                                <Input
                                    id="title"
                                    value={formData.title}
                                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                    placeholder="e.g., Battle of Badr"
                                    required
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="title_arabic" className="text-ink">
                                    Title (Arabic)
                                </Label>
                                <Input
                                    id="title_arabic"
                                    value={formData.title_arabic}
                                    onChange={(e) => setFormData({ ...formData, title_arabic: e.target.value })}
                                    placeholder="e.g., غزوة بدر"
                                    lang="ar"
                                    dir="rtl"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                        </div>

                        <div>
                            <Label htmlFor="description" className="text-ink">
                                Description
                            </Label>
                            <Textarea
                                id="description"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Detailed description of the event"
                                required
                                className="mt-2 bg-surface border-control text-ink"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="category" className="text-ink">
                                    Category
                                </Label>
                                <select
                                    id="category"
                                    value={formData.category}
                                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                    required
                                    className="w-full mt-2 bg-surface border border-control text-ink px-3 py-2"
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
                                <Label htmlFor="location" className="text-ink">
                                    Location
                                </Label>
                                <Input
                                    id="location"
                                    value={formData.location_name}
                                    onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                                    placeholder="e.g., Badr"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <Label htmlFor="year_gregorian" className="text-ink">
                                    Gregorian Year
                                </Label>
                                <Input
                                    id="year_gregorian"
                                    type="number"
                                    value={formData.year_gregorian}
                                    onChange={(e) => setFormData({ ...formData, year_gregorian: e.target.value })}
                                    placeholder="e.g., 625"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="year_hijri" className="text-ink">
                                    Hijri Year
                                </Label>
                                <Input
                                    id="year_hijri"
                                    type="number"
                                    value={formData.year_hijri}
                                    onChange={(e) => setFormData({ ...formData, year_hijri: e.target.value })}
                                    placeholder="e.g., 2"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="significance" className="text-ink">
                                    Significance
                                </Label>
                                <Input
                                    id="significance"
                                    value={formData.significance}
                                    onChange={(e) => setFormData({ ...formData, significance: e.target.value })}
                                    placeholder="e.g., First major victory"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                        </div>

                        <fieldset className="grid grid-cols-1 gap-4 border-t border-rule pt-4 md:grid-cols-2">
                            <legend className="text-sm font-medium text-ink">Review and citation</legend>
                            {editingId && events.find((event) => event.id === editingId)?.verification_status === 'unverified_seed' && (
                                <p className="text-xs text-ink-muted md:col-span-2">
                                    This is seed data. Saving an edit takes it out of the seed, so later seed runs leave it alone.
                                </p>
                            )}
                            <div>
                                <Label htmlFor="verification_status" className="text-ink">Review state</Label>
                                <select
                                    id="verification_status"
                                    value={formData.verification_status}
                                    onChange={(e) => setFormData({ ...formData, verification_status: e.target.value })}
                                    className="w-full mt-2 bg-surface border border-control text-ink px-3 py-2"
                                >
                                    {VERIFICATION_STATES.map((state) => (
                                        <option key={state.value} value={state.value}>{state.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor="end_year_hijri" className="text-ink">End year (Hijri)</Label>
                                <Input
                                    id="end_year_hijri"
                                    type="number"
                                    value={formData.end_year_hijri}
                                    onChange={(e) => setFormData({ ...formData, end_year_hijri: e.target.value })}
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="citation_source" className="text-ink">Citation: work</Label>
                                <Input
                                    id="citation_source"
                                    value={formData.citation_source}
                                    onChange={(e) => setFormData({ ...formData, citation_source: e.target.value })}
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="citation_locator" className="text-ink">Citation: volume and page</Label>
                                <Input
                                    id="citation_locator"
                                    value={formData.citation_locator}
                                    onChange={(e) => setFormData({ ...formData, citation_locator: e.target.value })}
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="citation_url" className="text-ink">Citation: URL</Label>
                                <Input
                                    id="citation_url"
                                    type="url"
                                    value={formData.citation_url}
                                    onChange={(e) => setFormData({ ...formData, citation_url: e.target.value })}
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <label className="flex items-center gap-2 self-end text-sm text-ink">
                                <input
                                    type="checkbox"
                                    checked={formData.publication_ready}
                                    onChange={(e) => setFormData({ ...formData, publication_ready: e.target.checked })}
                                />
                                Ready to publish (needs a reviewed state and a citation)
                            </label>
                        </fieldset>

                        <div className="flex gap-3">
                            <Button type="submit" disabled={isSaving} className="bg-accent text-on-accent hover:bg-ink hover:text-paper">
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
                                className="border-rule text-ink"
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
                        <h2 className="text-xl font-semibold text-ink mb-3">{categoryLabel(category)}</h2>
                        <div className="space-y-3">
                            {categoryEvents.map((event) => (
                                <Card key={event.id} className="pb-6">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <h3 className="text-lg font-semibold text-ink">{event.title}</h3>
                                                {event.category && (
                                                    <Badge className={getCategoryBadgeColor(event.category)}>
                                                        {categoryLabel(event.category)}
                                                    </Badge>
                                                )}
                                            </div>
                                            {event.title_arabic && (
                                                <p className="text-sm text-ink-muted mb-2 font-arabic" lang="ar" dir="rtl">{event.title_arabic}</p>
                                            )}
                                            <p className="text-sm text-ink mb-3">{event.description}</p>
                                            <div className="flex flex-wrap gap-2 text-xs text-ink-muted">
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
                                                className="border-rule text-ink"
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
                    <Card className="border-rule border-dashed py-8">
                        <p className="text-center text-ink-muted">
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
