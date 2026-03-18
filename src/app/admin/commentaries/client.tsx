'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    createCommentary,
    deleteCommentary,
    updateCommentary,
    searchHadiths,
    searchNarrators,
} from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Trash2, Edit2 } from 'lucide-react';

interface CommentariesManagerClientProps {
    commentaries: any[];
    hadiths: any[];
    narrators: any[];
}

const COMMENTARY_TYPES = ['Explanation', 'Critique', 'Translation', 'Historical Context', 'Legal Ruling'];

export function CommentariesManagerClient({
    commentaries: initialCommentaries,
    hadiths,
    narrators,
}: CommentariesManagerClientProps) {
    const router = useRouter();
    const [commentaries, setCommentaries] = useState(initialCommentaries);
    const [isCreating, setIsCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
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
                const results = await searchHadiths(hadithSearch);
                setHadithResults(results);
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
                const results = await searchNarrators(narratorSearch);
                setNarratorResults(results);
                setIsSearching(false);
            } else {
                setNarratorResults([]);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [narratorSearch]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await createCommentary(formData as any);
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
            console.error('Error creating commentary:', error);
        }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingId) return;
        try {
            await updateCommentary(editingId, formData as any);
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
            console.error('Error updating commentary:', error);
        }
    };

    const handleDelete = async (commentaryId: string) => {
        if (confirm('Are you sure you want to delete this commentary?')) {
            try {
                await deleteCommentary(commentaryId);
                setCommentaries(commentaries.filter((c) => c.id !== commentaryId));
            } catch (error) {
                console.error('Error deleting commentary:', error);
            }
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
        setIsCreating(false);
    };

    const getTypeBadgeColor = (type: string): string => {
        const colors: Record<string, string> = {
            Explanation: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            Critique: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
            Translation: 'bg-green-500/20 text-green-400 border-green-500/30',
            'Historical Context': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
            'Legal Ruling': 'bg-red-500/20 text-red-400 border-red-500/30',
        };
        return colors[type] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Commentaries Manager</h1>
                    <p className="text-slate-400 mt-1">Manage scholarly commentaries on hadiths and narrators</p>
                </div>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
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
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4">
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
                            <Input
                                id="hadith-search"
                                value={hadithSearch}
                                onChange={(e) => setHadithSearch(e.target.value)}
                                placeholder="Search hadith by title or topic..."
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />

                            {formData.hadith_id && (
                                <div className="mt-2 p-2 bg-slate-800 rounded border border-slate-700">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-300">
                                            {
                                                hadiths.find((h) => h.id === formData.hadith_id)?.title ||
                                                'Hadith selected'
                                            }
                                        </span>
                                        <button
                                            type="button"
                                            onClick={() => setFormData({ ...formData, hadith_id: '' })}
                                            className="text-xs text-red-400 hover:text-red-300"
                                        >
                                            Remove
                                        </button>
                                    </div>
                                </div>
                            )}

                            {hadithSearch && (
                                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                                    {hadithResults.map((hadith) => (
                                        <button
                                            key={hadith.id}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, hadith_id: hadith.id });
                                                setHadithSearch('');
                                            }}
                                            className="w-full text-left p-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-sm text-slate-300"
                                        >
                                            {hadith.title}
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
                            <Input
                                id="narrator-search"
                                value={narratorSearch}
                                onChange={(e) => setNarratorSearch(e.target.value)}
                                placeholder="Search narrator by name..."
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />

                            {formData.narrator_id && (
                                <div className="mt-2 p-2 bg-slate-800 rounded border border-slate-700">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-300">
                                            {
                                                narrators.find((n) => n.id === formData.narrator_id)?.name_english ||
                                                'Narrator selected'
                                            }
                                        </span>
                                        <button
                                            type="button"
                                            onClick={() => setFormData({ ...formData, narrator_id: '' })}
                                            className="text-xs text-red-400 hover:text-red-300"
                                        >
                                            Remove
                                        </button>
                                    </div>
                                </div>
                            )}

                            {narratorSearch && (
                                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                                    {narratorResults.map((narrator) => (
                                        <button
                                            key={narrator.id}
                                            type="button"
                                            onClick={() => {
                                                setFormData({ ...formData, narrator_id: narrator.id });
                                                setNarratorSearch('');
                                            }}
                                            className="w-full text-left p-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-sm text-slate-300"
                                        >
                                            {narrator.name_english} ({narrator.tabaqah})
                                        </button>
                                    ))}
                                </div>
                            )}
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

            {/* Commentaries List */}
            <div className="space-y-4">
                {commentaries.map((commentary) => (
                    <Card key={commentary.id} className="bg-slate-900 border-slate-700 p-6">
                        <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h3 className="text-lg font-semibold text-white">{commentary.source_work}</h3>
                                    <Badge className={getTypeBadgeColor(commentary.type)}>
                                        {commentary.type}
                                    </Badge>
                                </div>
                                <p className="text-sm text-slate-400 mb-3">By {commentary.author}</p>
                                <p className="text-sm text-slate-300 mb-3">{commentary.text}</p>
                                {commentary.text_arabic && (
                                    <p className="text-sm text-slate-400 mb-3 font-arabic">{commentary.text_arabic}</p>
                                )}
                                <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                                    {commentary.hadith && (
                                        <span className="bg-blue-500/10 px-2 py-1 rounded">
                                            📖 Hadith: {commentary.hadith.title}
                                        </span>
                                    )}
                                    {commentary.narrator && (
                                        <span className="bg-green-500/10 px-2 py-1 rounded">
                                            👤 Narrator: {commentary.narrator.name_english}
                                        </span>
                                    )}
                                    {commentary.reference && (
                                        <span className="bg-purple-500/10 px-2 py-1 rounded">
                                            📍 {commentary.reference}
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleStartEdit(commentary)}
                                    className="border-slate-600 text-slate-300"
                                >
                                    <Edit2 className="w-4 h-4" />
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleDelete(commentary.id)}
                                    className="border-red-600/30 text-red-400 hover:bg-red-500/10"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </Button>
                            </div>
                        </div>
                    </Card>
                ))}

                {commentaries.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">
                            No commentaries yet. Click "New Commentary" to create one.
                        </p>
                    </Card>
                )}
            </div>
        </div>
    );
}
