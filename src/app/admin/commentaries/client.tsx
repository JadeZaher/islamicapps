'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    createCommentary,
    deleteCommentary,
    publishCommentary,
    updateCommentary,
} from '@/app/actions/curation/commentary';
import { searchHadithsForCuration } from '@/app/actions/curation/search';
import { searchNarratorsTypeahead } from '@/app/actions/read/narrator';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Edit2 } from 'lucide-react';
import { ConfirmDelete } from '@/app/admin/_components/ConfirmDelete';
import { describeActionError } from '@/app/admin/_components/actionError';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';

interface PaginationInfo {
    page: number;
    totalPages: number;
    total: number;
    pageSize: number;
}

interface CommentariesManagerClientProps {
    commentaries: any[];
    hadiths: any[];
    narrators: any[];
    pagination: PaginationInfo;
    filterType?: string;
}

const STATUS_LABELS: Record<string, string> = { proposed: 'Proposed', verified: 'Verified', published: 'Published' };

const hadithLabel = (hadith: { title?: string | null; source?: string; hadith_no?: string | null }): string =>
    hadith.title || [hadith.source, hadith.hadith_no].filter(Boolean).join(' ') || 'Untitled hadith';

const COMMENTARY_TYPES = ['Explanation', 'Critique', 'Translation', 'Historical Context', 'Legal Ruling'];

export function CommentariesManagerClient({
    commentaries: initialCommentaries,
    hadiths,
    narrators,
    pagination,
    filterType = '',
}: CommentariesManagerClientProps) {
    const router = useRouter();
    // Retired rows leave the list at once; everything else follows the server props after router.refresh().
    const [retiredIds, setRetiredIds] = useState<Set<string>>(new Set());
    const commentaries = initialCommentaries.filter(
        (c) => !retiredIds.has(c.id) && (!filterType || c.type === filterType)
    );
    const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
    const [publishingId, setPublishingId] = useState<string | null>(null);
    const [linkedLabels, setLinkedLabels] = useState({ hadith: '', narrator: '' });
    const [isCreating, setIsCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [hadithSearch, setHadithSearch] = useState('');
    const [narratorSearch, setNarratorSearch] = useState('');
    const [hadithResults, setHadithResults] = useState<any[]>([]);
    const [narratorResults, setNarratorResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [formData, setFormData] = useState({
        source_work: '',
        author: '',
        text: '',
        text_arabic: '',
        type: '',
        reference: '',
        hadith_id: '',
        narrator_id: '',
    });

    // Search hadiths with debounce
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (hadithSearch.trim()) {
                setIsSearching(true);
                try {
                    const results = await searchHadithsForCuration(hadithSearch);
                    setHadithResults(results.items);
                } catch (error) {
                    setHadithResults([]);
                    setFormError(describeActionError(error, 'Hadith search failed. Try again.'));
                }
                setIsSearching(false);
            } else {
                setHadithResults([]);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [hadithSearch]);

    // Search narrators with debounce
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (narratorSearch.trim()) {
                setIsSearching(true);
                try {
                    setNarratorResults(await searchNarratorsTypeahead(narratorSearch));
                } catch (error) {
                    setNarratorResults([]);
                    setFormError(describeActionError(error, 'Narrator search failed. Try again.'));
                }
                setIsSearching(false);
            } else {
                setNarratorResults([]);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [narratorSearch]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setFormError(null);
        try {
            await createCommentary(formData);
            setFormData({
                source_work: '',
                author: '',
                text: '',
                text_arabic: '',
                type: '',
                reference: '',
                hadith_id: '',
                narrator_id: '',
            });
            setIsCreating(false);
            setHadithSearch('');
            setNarratorSearch('');
            router.refresh();
        } catch (error) {
            setFormError(describeActionError(error, 'Could not create the commentary. Check the fields and try again.'));
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
            // Links are fixed at creation: the update action takes content fields only.
            const content: Partial<typeof formData> = { ...formData };
            delete content.hadith_id;
            delete content.narrator_id;
            await updateCommentary(editingId, content);
            setFormData({
                source_work: '',
                author: '',
                text: '',
                text_arabic: '',
                type: '',
                reference: '',
                hadith_id: '',
                narrator_id: '',
            });
            setEditingId(null);
            setHadithSearch('');
            setNarratorSearch('');
            router.refresh();
        } catch (error) {
            setFormError(describeActionError(error, 'Could not update the commentary. Check the fields and try again.'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (commentaryId: string) => {
        await deleteCommentary(commentaryId);
        setRetiredIds((ids) => new Set(ids).add(commentaryId));
    };

    const handleTogglePublished = async (commentary: any) => {
        const target = commentary.status === 'published' ? 'proposed' : 'published';
        setPublishingId(commentary.id);
        setRowErrors((errors) => {
            const next = { ...errors };
            delete next[commentary.id];
            return next;
        });
        try {
            await publishCommentary(commentary.id, target);
            router.refresh();
        } catch (error) {
            const fallback = target === 'published' ? 'Could not publish this commentary.' : 'Could not unpublish this commentary.';
            setRowErrors((errors) => ({ ...errors, [commentary.id]: describeActionError(error, fallback) }));
        } finally {
            setPublishingId(null);
        }
    };

    const handleStartEdit = (commentary: any) => {
        setEditingId(commentary.id);
        setFormData({
            source_work: commentary.source_work || '',
            author: commentary.author || '',
            text: commentary.text || '',
            text_arabic: commentary.text_arabic || '',
            type: commentary.type || '',
            reference: commentary.reference || '',
            hadith_id: commentary.hadith?.id || '',
            narrator_id: commentary.narrator?.id || '',
        });
        setLinkedLabels({
            hadith: commentary.hadith ? hadithLabel(commentary.hadith) : '',
            narrator: commentary.narrator?.name_english || '',
        });
        setIsCreating(false);
        setFormError(null);
    };

    const getTypeBadgeColor = (type: string): string => {
        const colors: Record<string, string> = {
            Explanation: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            Critique: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
            Translation: 'bg-green-500/20 text-green-400 border-green-500/30',
            'Historical Context': 'bg-teal-500/20 text-teal-400 border-teal-500/30',
            'Legal Ruling': 'bg-red-500/20 text-red-400 border-red-500/30',
        };
        return colors[type] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-3xl font-bold text-white">Commentaries</h1>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
                        setFormError(null);
                        setLinkedLabels({ hadith: '', narrator: '' });
                        setFormData({
                            source_work: '',
                            author: '',
                            text: '',
                            text_arabic: '',
                            type: '',
                            reference: '',
                            hadith_id: '',
                            narrator_id: '',
                        });
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    New Commentary
                </Button>
            </div>

            {/* Create/Edit Form */}
            {(isCreating || editingId) && (
                <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-white mb-4">
                        {editingId ? 'Edit Commentary' : 'Create New Commentary'}
                    </h2>
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4" aria-busy={isSaving}>
                        {formError && (
                            <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                                {formError}
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="source_work" className="text-slate-300">
                                    Source Work
                                </Label>
                                <Input
                                    id="source_work"
                                    value={formData.source_work}
                                    onChange={(e) => setFormData({ ...formData, source_work: e.target.value })}
                                    placeholder="e.g., Fath al-Bari"
                                    required
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="author" className="text-slate-300">
                                    Author
                                </Label>
                                <Input
                                    id="author"
                                    value={formData.author}
                                    onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                                    placeholder="e.g., Ibn Hajar al-Asqalani"
                                    required
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                        </div>

                        <div>
                            <Label htmlFor="type" className="text-slate-300">
                                Type
                            </Label>
                            <select
                                id="type"
                                value={formData.type}
                                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                required
                                className="w-full mt-2 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2"
                            >
                                <option value="">Select Type</option>
                                {COMMENTARY_TYPES.map((type) => (
                                    <option key={type} value={type}>
                                        {type}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <Label htmlFor="text" className="text-slate-300">
                                Commentary Text (English)
                            </Label>
                            <Textarea
                                id="text"
                                value={formData.text}
                                onChange={(e) => setFormData({ ...formData, text: e.target.value })}
                                placeholder="The commentary text"
                                required
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />
                        </div>

                        <div>
                            <Label htmlFor="text_arabic" className="text-slate-300">
                                Commentary Text (Arabic)
                            </Label>
                            <Textarea
                                id="text_arabic"
                                value={formData.text_arabic}
                                onChange={(e) => setFormData({ ...formData, text_arabic: e.target.value })}
                                placeholder="النص العربي"
                                lang="ar"
                                dir="rtl"
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />
                        </div>

                        <div>
                            <Label htmlFor="reference" className="text-slate-300">
                                Reference
                            </Label>
                            <Input
                                id="reference"
                                value={formData.reference}
                                onChange={(e) => setFormData({ ...formData, reference: e.target.value })}
                                placeholder="e.g., Vol. 1, Page 45"
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />
                        </div>

                        {/* Search and Select Hadith */}
                        <div>
                            <Label htmlFor="hadith-search" className="text-slate-300">
                                Link to Hadith (Optional)
                            </Label>
                            {!editingId && (
                                <Input
                                    id="hadith-search"
                                    value={hadithSearch}
                                    onChange={(e) => setHadithSearch(e.target.value)}
                                    placeholder="Search hadith by title or topic..."
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            )}

                            {formData.hadith_id && (
                                <div className="mt-2 p-2 bg-slate-800 rounded border border-slate-700">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-300">
                                            {linkedLabels.hadith ||
                                                (() => {
                                                    const found = hadiths.find((h) => h.id === formData.hadith_id);
                                                    return found ? hadithLabel(found) : 'Hadith selected';
                                                })()}
                                        </span>
                                        {!editingId && (
                                            <button
                                                type="button"
                                                onClick={() => setFormData({ ...formData, hadith_id: '' })}
                                                aria-label="Remove linked hadith"
                                                className="text-xs text-red-400 hover:text-red-300"
                                            >
                                                Remove
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}

                            {!editingId && hadithSearch && (
                                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                                    {hadithResults.map((hadith) => (
                                        <button
                                            key={hadith.id}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, hadith_id: hadith.id });
                                                setLinkedLabels((labels) => ({ ...labels, hadith: hadithLabel(hadith) }));
                                                setHadithSearch('');
                                            }}
                                            className="w-full text-left p-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-sm text-slate-300"
                                        >
                                            {hadithLabel(hadith)}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Search and Select Narrator */}
                        <div>
                            <Label htmlFor="narrator-search" className="text-slate-300">
                                Link to Narrator (Optional)
                            </Label>
                            {!editingId && (
                                <Input
                                    id="narrator-search"
                                    value={narratorSearch}
                                    onChange={(e) => setNarratorSearch(e.target.value)}
                                    placeholder="Search narrator by name..."
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            )}

                            {formData.narrator_id && (
                                <div className="mt-2 p-2 bg-slate-800 rounded border border-slate-700">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-300">
                                            {linkedLabels.narrator ||
                                                narrators.find((n) => n.id === formData.narrator_id)?.name_english ||
                                                'Narrator selected'}
                                        </span>
                                        {!editingId && (
                                            <button
                                                type="button"
                                                onClick={() => setFormData({ ...formData, narrator_id: '' })}
                                                aria-label="Remove linked narrator"
                                                className="text-xs text-red-400 hover:text-red-300"
                                            >
                                                Remove
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}

                            {!editingId && narratorSearch && (
                                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                                    {narratorResults.map((narrator) => (
                                        <button
                                            key={narrator.id}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, narrator_id: narrator.id });
                                                setLinkedLabels((labels) => ({ ...labels, narrator: narrator.name_english }));
                                                setNarratorSearch('');
                                            }}
                                            className="w-full text-left p-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-sm text-slate-300"
                                        >
                                            {narrator.name_english}
                                            {narrator.tabaqah ? ` (${narrator.tabaqah})` : ''}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

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

            <SearchFilterBar
                showSearch={false}
                filters={[
                    {
                        key: 'type',
                        label: 'Type',
                        options: [
                            { label: 'All Types', value: '' },
                            ...COMMENTARY_TYPES.map((t) => ({ label: t, value: t })),
                        ],
                    },
                ]}
                totalResults={pagination.total}
            />

            {/* Commentaries List */}
            <div className="space-y-4">
                {commentaries.map((commentary) => (
                    <Card key={commentary.id} className="bg-slate-900 border-slate-700 p-6">
                        <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h3 className="text-lg font-semibold text-white">{commentary.source_work}</h3>
                                    {commentary.type && (
                                        <Badge className={getTypeBadgeColor(commentary.type)}>
                                            {commentary.type}
                                        </Badge>
                                    )}
                                    <Badge
                                        className={
                                            commentary.status === 'published'
                                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                                : 'bg-slate-800 text-slate-300 border-slate-600'
                                        }
                                    >
                                        {STATUS_LABELS[commentary.status] ?? commentary.status}
                                    </Badge>
                                </div>
                                {commentary.author && <p className="text-sm text-slate-400 mb-3">By {commentary.author}</p>}
                                <p className="text-sm text-slate-300 mb-3">{commentary.text}</p>
                                {commentary.text_arabic && (
                                    <p className="text-sm text-slate-400 mb-3 font-arabic" lang="ar" dir="rtl">{commentary.text_arabic}</p>
                                )}
                                <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                                    {commentary.hadith && (
                                        <span className="bg-blue-500/10 px-2 py-1 rounded">
                                            Hadith: {hadithLabel(commentary.hadith)}
                                        </span>
                                    )}
                                    {commentary.narrator && (
                                        <span className="bg-green-500/10 px-2 py-1 rounded">
                                            Narrator: {commentary.narrator.name_english}
                                        </span>
                                    )}
                                    {commentary.reference && (
                                        <span className="bg-slate-600/15 px-2 py-1 rounded">
                                            {commentary.reference}
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-start gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={publishingId === commentary.id}
                                    onClick={() => handleTogglePublished(commentary)}
                                    className="border-slate-600 text-slate-300"
                                >
                                    {publishingId === commentary.id
                                        ? 'Saving...'
                                        : commentary.status === 'published'
                                          ? 'Unpublish'
                                          : 'Publish'}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleStartEdit(commentary)}
                                    aria-label={`Edit commentary: ${commentary.source_work}`}
                                    className="border-slate-600 text-slate-300"
                                >
                                    <Edit2 className="w-4 h-4" aria-hidden="true" />
                                </Button>
                                <ConfirmDelete
                                    itemName="commentary"
                                    consequence={`Retire the commentary from "${commentary.source_work ?? 'this work'}"? It is hidden from every page. Nothing is erased and an audit record is kept.`}
                                    onConfirm={() => handleDelete(commentary.id)}
                                />
                            </div>
                        </div>
                        {rowErrors[commentary.id] && (
                            <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                                {rowErrors[commentary.id]}
                            </p>
                        )}
                    </Card>
                ))}

                {commentaries.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">
                            No commentaries yet. Click "New Commentary" to create one.
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
