'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

interface Commentary {
    id: string;
    author: string;
    text: string;
    source_work: string;
    reference?: string;
    type: 'HADITH_COMMENTARY' | 'NARRATOR_BIOGRAPHY' | 'CHAIN_ANALYSIS' | 'OTHER';
}

interface CommentarySectionProps {
    commentaries: Commentary[];
    narratorId: string;
}

const COMMENTARY_TYPE_LABELS = {
    HADITH_COMMENTARY: 'Hadith Commentary',
    NARRATOR_BIOGRAPHY: 'Narrator Biography',
    CHAIN_ANALYSIS: 'Chain Analysis',
    OTHER: 'Other',
};

const COMMENTARY_TYPE_COLORS = {
    HADITH_COMMENTARY: {
        bg: 'bg-blue-500/20',
        border: 'border-blue-500/40',
        text: 'text-blue-300',
    },
    NARRATOR_BIOGRAPHY: {
        bg: 'bg-purple-500/20',
        border: 'border-purple-500/40',
        text: 'text-purple-300',
    },
    CHAIN_ANALYSIS: {
        bg: 'bg-orange-500/20',
        border: 'border-orange-500/40',
        text: 'text-orange-300',
    },
    OTHER: {
        bg: 'bg-gray-500/20',
        border: 'border-gray-500/40',
        text: 'text-gray-300',
    },
};

export function CommentarySection({ commentaries, narratorId }: CommentarySectionProps) {
    const [showForm, setShowForm] = useState(false);
    const [filterType, setFilterType] = useState<string>('ALL');
    const [formData, setFormData] = useState({
        author: '',
        text: '',
        source_work: '',
        reference: '',
        type: 'HADITH_COMMENTARY' as const,
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Group commentaries by source work
    const groupedCommentaries = commentaries.reduce(
        (acc, commentary) => {
            const source = commentary.source_work || 'Unknown Source';
            if (!acc[source]) {
                acc[source] = [];
            }
            acc[source].push(commentary);
            return acc;
        },
        {} as Record<string, Commentary[]>
    );

    // Filter commentaries
    const filteredCommentaries =
        filterType === 'ALL'
            ? commentaries
            : commentaries.filter((c) => c.type === filterType);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);

        try {
            // TODO: Implement API call to save commentary
            // const response = await fetch('/api/commentaries', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({
            //         ...formData,
            //         narrator_id: narratorId,
            //     }),
            // });
            // if (response.ok) {
            //     // Reset form and refresh data
            //     setShowForm(false);
            //     setFormData({...});
            // }

            // For now, just show a success message
            alert('Commentary form prepared. API integration needed.');
            setShowForm(false);
        } catch (error) {
            console.error('Error submitting commentary:', error);
            alert('Error submitting commentary');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleInputChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    return (
        <div className="space-y-6">
            {/* Header with Action Button */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-white">Scholarly Commentaries</h2>
                    <p className="text-white/60 text-sm mt-1">
                        {filteredCommentaries.length} commentary
                        {filteredCommentaries.length !== 1 ? 'ies' : ''}
                    </p>
                </div>
                <Button
                    onClick={() => setShowForm(!showForm)}
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                >
                    {showForm ? 'Cancel' : '+ Add Commentary'}
                </Button>
            </div>

            {/* Add Commentary Form */}
            {showForm && (
                <Card className="bg-white/5 border-white/10">
                    <CardHeader>
                        <CardTitle className="text-white">Add New Commentary</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-white/80">Author Name</Label>
                                    <Input
                                        name="author"
                                        value={formData.author}
                                        onChange={handleInputChange}
                                        placeholder="Scholar name"
                                        className="bg-white/5 border-white/20 text-white placeholder:text-white/40"
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-white/80">Source Work</Label>
                                    <Input
                                        name="source_work"
                                        value={formData.source_work}
                                        onChange={handleInputChange}
                                        placeholder="Book or manuscript title"
                                        className="bg-white/5 border-white/20 text-white placeholder:text-white/40"
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-white/80">Commentary Type</Label>
                                    <select
                                        name="type"
                                        value={formData.type}
                                        onChange={handleInputChange}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/20 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                                    >
                                        {Object.entries(COMMENTARY_TYPE_LABELS).map(([key, label]) => (
                                            <option key={key} value={key} className="bg-slate-900">
                                                {label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-white/80">Reference</Label>
                                    <Input
                                        name="reference"
                                        value={formData.reference}
                                        onChange={handleInputChange}
                                        placeholder="Page number, volume, etc."
                                        className="bg-white/5 border-white/20 text-white placeholder:text-white/40"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-white/80">Commentary Text</Label>
                                <Textarea
                                    name="text"
                                    value={formData.text}
                                    onChange={handleInputChange}
                                    placeholder="Commentary details..."
                                    className="bg-white/5 border-white/20 text-white placeholder:text-white/40 min-h-32"
                                    required
                                />
                            </div>

                            <div className="flex gap-3 justify-end">
                                <Button
                                    type="button"
                                    onClick={() => setShowForm(false)}
                                    className="bg-white/10 hover:bg-white/20 text-white border border-white/20"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="bg-purple-600 hover:bg-purple-700 text-white"
                                >
                                    {isSubmitting ? 'Submitting...' : 'Add Commentary'}
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            )}

            {/* Filter Tabs */}
            {commentaries.length > 0 && (
                <div className="flex flex-wrap gap-2 pb-4 border-b border-white/10">
                    <button
                        onClick={() => setFilterType('ALL')}
                        className={`px-4 py-2 rounded-lg border transition-all ${
                            filterType === 'ALL'
                                ? 'bg-purple-600 border-purple-500 text-white'
                                : 'bg-white/5 border-white/20 text-white/70 hover:bg-white/10'
                        }`}
                    >
                        All ({commentaries.length})
                    </button>
                    {Object.entries(COMMENTARY_TYPE_LABELS).map(([type, label]) => {
                        const count = commentaries.filter((c) => c.type === type).length;
                        return count > 0 ? (
                            <button
                                key={type}
                                onClick={() => setFilterType(type)}
                                className={`px-4 py-2 rounded-lg border transition-all ${
                                    filterType === type
                                        ? 'bg-purple-600 border-purple-500 text-white'
                                        : 'bg-white/5 border-white/20 text-white/70 hover:bg-white/10'
                                }`}
                            >
                                {label} ({count})
                            </button>
                        ) : null;
                    })}
                </div>
            )}

            {/* Commentaries Display */}
            {filteredCommentaries.length > 0 ? (
                <div className="space-y-4">
                    {Object.entries(groupedCommentaries).map(([source, sourceCommentaries]) => {
                        const filtered = filterType === 'ALL'
                            ? sourceCommentaries
                            : sourceCommentaries.filter((c) => c.type === filterType);

                        if (filtered.length === 0) return null;

                        return (
                            <div key={source} className="space-y-3">
                                <h3 className="text-lg font-semibold text-purple-300 px-1">{source}</h3>
                                <div className="space-y-3">
                                    {filtered.map((commentary) => {
                                        const typeColors =
                                            COMMENTARY_TYPE_COLORS[commentary.type];

                                        return (
                                            <Card
                                                key={commentary.id}
                                                className="bg-white/5 border-white/10 hover:border-white/20 transition-all"
                                            >
                                                <CardContent className="pt-6">
                                                    <div className="space-y-3">
                                                        {/* Header */}
                                                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                                            <div>
                                                                <h4 className="font-semibold text-white">
                                                                    {commentary.author}
                                                                </h4>
                                                                {commentary.reference && (
                                                                    <p className="text-sm text-white/60 mt-1">
                                                                        {commentary.reference}
                                                                    </p>
                                                                )}
                                                            </div>
                                                            <div
                                                                className={`inline-flex px-3 py-1 rounded-md border text-xs font-semibold
                                                                    ${typeColors.bg} ${typeColors.border} ${typeColors.text}`}
                                                            >
                                                                {COMMENTARY_TYPE_LABELS[commentary.type]}
                                                            </div>
                                                        </div>

                                                        {/* Commentary Text */}
                                                        <p className="text-white/80 leading-relaxed text-sm">
                                                            {commentary.text}
                                                        </p>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <Card className="bg-white/5 border-white/10">
                    <CardContent className="py-12">
                        <div className="text-center">
                            <p className="text-white/60 mb-4">
                                {filterType === 'ALL'
                                    ? 'No commentaries available yet.'
                                    : `No ${COMMENTARY_TYPE_LABELS[filterType as keyof typeof COMMENTARY_TYPE_LABELS]} commentaries found.`}
                            </p>
                            <Button
                                onClick={() => setShowForm(true)}
                                className="bg-purple-600 hover:bg-purple-700 text-white"
                            >
                                Be the first to add a commentary
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
