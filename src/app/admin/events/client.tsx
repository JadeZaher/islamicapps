'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createHistoricalEvent, deleteHistoricalEvent, updateHistoricalEvent } from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Trash2, Edit2 } from 'lucide-react';

interface EventsManagerClientProps {
    events: any[];
}

const EVENT_CATEGORIES = [
    'Political',
    'Religious',
    'Military',
    'Scientific',
    'Cultural',
    'Economic',
    'Social',
];

export function EventsManagerClient({ events }: EventsManagerClientProps) {
    const router = useRouter();
    const [isCreating, setIsCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [filterCategory, setFilterCategory] = useState<string>('');
    const [filterYearMin, setFilterYearMin] = useState<number | ''>('');
    const [filterYearMax, setFilterYearMax] = useState<number | ''>('');
    const [formData, setFormData] = useState({
        title: '',
        title_arabic: '',
        description: '',
        year_hijri: '',
        year_gregorian: '',
        category: '',
        significance: '',
        location_name: '',
    });

    const filteredEvents = events.filter((event) => {
        if (filterCategory && event.category !== filterCategory) return false;
        if (filterYearMin && event.year_gregorian && event.year_gregorian < filterYearMin) return false;
        if (filterYearMax && event.year_gregorian && event.year_gregorian > filterYearMax) return false;
        return true;
    });

    const groupedEvents = filteredEvents.reduce((acc, event) => {
        const category = event.category || 'Uncategorized';
        if (!acc[category]) acc[category] = [];
        acc[category].push(event);
        return acc;
    }, {} as Record<string, any[]>);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const submitData = {
                ...formData,
                year_hijri: formData.year_hijri ? parseInt(formData.year_hijri as string) : undefined,
                year_gregorian: formData.year_gregorian ? parseInt(formData.year_gregorian as string) : undefined,
            };
            await createHistoricalEvent(submitData as any);
            setFormData({
                title: '',
                title_arabic: '',
                description: '',
                year_hijri: '',
                year_gregorian: '',
                category: '',
                significance: '',
                location_name: '',
            });
            setIsCreating(false);
            router.refresh();
        } catch (error) {
            console.error('Error creating event:', error);
        }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingId) return;
        try {
            const submitData = {
                ...formData,
                year_hijri: formData.year_hijri ? parseInt(formData.year_hijri as string) : undefined,
                year_gregorian: formData.year_gregorian ? parseInt(formData.year_gregorian as string) : undefined,
            };
            await updateHistoricalEvent(editingId, submitData as any);
            setFormData({
                title: '',
                title_arabic: '',
                description: '',
                year_hijri: '',
                year_gregorian: '',
                category: '',
                significance: '',
                location_name: '',
            });
            setEditingId(null);
            router.refresh();
        } catch (error) {
            console.error('Error updating event:', error);
        }
    };

    const handleDelete = async (eventId: string) => {
        if (confirm('Are you sure you want to delete this event?')) {
            try {
                await deleteHistoricalEvent(eventId);
                router.refresh();
            } catch (error) {
                console.error('Error deleting event:', error);
            }
        }
    };

    const handleStartEdit = (event: any) => {
        setEditingId(event.id);
        setFormData({
            title: event.title || '',
            title_arabic: event.title_arabic || '',
            description: event.description || '',
            year_hijri: event.year_hijri || '',
            year_gregorian: event.year_gregorian || '',
            category: event.category || '',
            significance: event.significance || '',
            location_name: event.location_name || '',
        });
        setIsCreating(false);
    };

    const getCategoryBadgeColor = (category: string): string => {
        const colors: Record<string, string> = {
            Political: 'bg-red-500/20 text-red-400 border-red-500/30',
            Religious: 'bg-green-500/20 text-green-400 border-green-500/30',
            Military: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
            Scientific: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            Cultural: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
            Economic: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
            Social: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
        };
        return colors[category] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Events Manager</h1>
                    <p className="text-slate-400 mt-1">Manage historical Islamic events</p>
                </div>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
                        setFormData({
                            title: '',
                            title_arabic: '',
                            description: '',
                            year_hijri: '',
                            year_gregorian: '',
                            category: '',
                            significance: '',
                            location_name: '',
                        });
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    New Event
                </Button>
            </div>

            {/* Filters */}
            <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                <h3 className="text-lg font-semibold text-white mb-4">Filters</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <Label htmlFor="category-filter" className="text-slate-300">
                            Category
                        </Label>
                        <select
                            id="category-filter"
                            value={filterCategory}
                            onChange={(e) => setFilterCategory(e.target.value)}
                            className="w-full mt-2 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2"
                        >
                            <option value="">All Categories</option>
                            {EVENT_CATEGORIES.map((cat) => (
                                <option key={cat} value={cat}>
                                    {cat}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <Label htmlFor="year-min" className="text-slate-300">
                            Year From
                        </Label>
                        <Input
                            id="year-min"
                            type="number"
                            value={filterYearMin}
                            onChange={(e) => setFilterYearMin(e.target.value ? parseInt(e.target.value) : '')}
                            placeholder="Start year"
                            className="mt-2 bg-slate-800 border-slate-700 text-white"
                        />
                    </div>
                    <div>
                        <Label htmlFor="year-max" className="text-slate-300">
                            Year To
                        </Label>
                        <Input
                            id="year-max"
                            type="number"
                            value={filterYearMax}
                            onChange={(e) => setFilterYearMax(e.target.value ? parseInt(e.target.value) : '')}
                            placeholder="End year"
                            className="mt-2 bg-slate-800 border-slate-700 text-white"
                        />
                    </div>
                </div>
            </Card>

            {/* Create/Edit Form */}
            {(isCreating || editingId) && (
                <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-white mb-4">
                        {editingId ? 'Edit Event' : 'Create New Event'}
                    </h2>
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4">
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
                                        <option key={cat} value={cat}>
                                            {cat}
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

                        <div className="flex gap-3">
                            <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700">
                                {editingId ? 'Update' : 'Create'}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setIsCreating(false);
                                    setEditingId(null);
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
                {(Object.entries(groupedEvents) as [string, any[]][]).map(([category, categoryEvents]) => (
                    <div key={category}>
                        <h2 className="text-xl font-semibold text-white mb-3">{category}</h2>
                        <div className="space-y-3">
                            {categoryEvents.map((event) => (
                                <Card key={event.id} className="bg-slate-900 border-slate-700 p-6">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <h3 className="text-lg font-semibold text-white">{event.title}</h3>
                                                <Badge className={getCategoryBadgeColor(event.category)}>
                                                    {event.category}
                                                </Badge>
                                            </div>
                                            {event.title_arabic && (
                                                <p className="text-sm text-slate-400 mb-2">{event.title_arabic}</p>
                                            )}
                                            <p className="text-sm text-slate-300 mb-3">{event.description}</p>
                                            <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                                                {event.year_gregorian && (
                                                    <span>📅 {event.year_gregorian} CE</span>
                                                )}
                                                {event.year_hijri && (
                                                    <span>☪️ {event.year_hijri} AH</span>
                                                )}
                                                {event.location_name && (
                                                    <span>📍 {event.location_name}</span>
                                                )}
                                                {event.significance && (
                                                    <span>⭐ {event.significance}</span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleStartEdit(event)}
                                                className="border-slate-600 text-slate-300"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleDelete(event.id)}
                                                className="border-red-600/30 text-red-400 hover:bg-red-500/10"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                ))}

                {filteredEvents.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">
                            No events found. Click "New Event" to create one.
                        </p>
                    </Card>
                )}
            </div>
        </div>
    );
}
