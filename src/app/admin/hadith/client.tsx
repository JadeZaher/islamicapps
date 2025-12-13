'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createHadith, calculateAutoGrade, calculateTransmissionType } from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, BarChart3, Award } from 'lucide-react';

interface HadithManagerClientProps {
    hadiths: any[];
}

export function HadithManagerClient({ hadiths }: HadithManagerClientProps) {
    const router = useRouter();
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

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const hadithId = await createHadith(formData);
        setFormData({ title: '', primary_topic: '' });
        setIsCreating(false);
        router.refresh();
        router.push(`/hadith/${hadithId}`);
    };

    const handleRunAutoAnalysis = async (hadithId: string) => {
        await calculateAutoGrade(hadithId);
        await calculateTransmissionType(hadithId);
        router.refresh();
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Hadith Manager</h1>
                    <p className="text-slate-400 mt-1">Manage Hadith entries and grading</p>
                </div>
                <Button
                    onClick={() => setIsCreating(true)}
                    className="bg-emerald-600 hover:bg-emerald-700"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    New Hadith
                </Button>
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

            {/* Hadith List */}
            <div className="space-y-4">
                {hadiths.map((hadith) => (
                    <Card key={hadith.id} className="bg-slate-900 border-slate-700 p-6">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h3 className="text-lg font-semibold text-white">{hadith.title}</h3>
                                    {hadith.display_grade && (
                                        <Badge className={getGradeBadgeColor(hadith.display_grade)}>
                                            {hadith.display_grade}
                                        </Badge>
                                    )}
                                    {hadith.transmission_type === 'MUTAWATIR' && (
                                        <Badge className="bg-amber-500/20 text-amber-400">
                                            ⭐ Mutawatir
                                        </Badge>
                                    )}
                                </div>
                                <p className="text-sm text-slate-400">{hadith.primary_topic}</p>
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
                            No Hadiths yet. Click "New Hadith" to create one.
                        </p>
                    </Card>
                )}
            </div>
        </div>
    );
}
