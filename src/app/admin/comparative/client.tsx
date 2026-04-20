'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    createReligiousTradition,
    deleteTradition,
    createSourceText,
    deleteSourceText,
    linkSourceTextToTradition,
    createCrossParallel,
    deleteParallel,
    updateParallel,
    createMotifTag,
    deleteMotifTag,
    linkNarratorToTradition,
    unlinkNarratorFromTradition,
} from '@/app/actions/comparative-actions';
import { searchHadiths } from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { TraditionBadge, ParallelTypeBadge, IsraIliyyatBadge } from '@/components/TraditionBadge';
import { Plus, Trash2, Edit2, BookOpen } from 'lucide-react';

const PARALLEL_TYPES = ['CONDEMNATION', 'CULTURAL_BLEED', 'SHARED_SOURCE', 'DIRECT_BORROWING', 'APOLOGETIC', 'DISPUTED'];
const ISRA_STATUSES = ['MUWAFIQ', 'MUKHALIF', 'MASKUT_ANHU', 'NONE'];
const CONFIDENCE_LEVELS = ['HIGH', 'MEDIUM', 'LOW'];
const MOTIF_CATEGORIES = ['ESCHATOLOGY', 'CREATION', 'PROPHETIC_STORIES', 'LEGAL', 'WISDOM', 'PERSIAN_INFLUENCE', 'COSMOLOGY'];

interface Props {
    traditions: any[];
    sourceTexts: any[];
    parallels: any[];
    motifTags: any[];
    narrators: any[];
}

// ─── Tradition Manager ───────────────────────────────────────────────────────
function TraditionManager({ traditions, narrators, onRefresh }: { traditions: any[]; narrators: any[]; onRefresh: () => void }) {
    const [isCreating, setIsCreating] = useState(false);
    const [form, setForm] = useState({ name: '', name_arabic: '', description: '', geographic_heartlands: '' });
    const [narratorSearch, setNarratorSearch] = useState('');
    const [selectedTradition, setSelectedTradition] = useState<string | null>(null);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        await createReligiousTradition({
            ...form,
            geographic_heartlands: form.geographic_heartlands ? form.geographic_heartlands.split(',').map((s) => s.trim()) : [],
        });
        setForm({ name: '', name_arabic: '', description: '', geographic_heartlands: '' });
        setIsCreating(false);
        onRefresh();
    };

    const handleDelete = async (id: string) => {
        if (confirm('Delete this tradition? This will also remove all links.')) {
            await deleteTradition(id);
            onRefresh();
        }
    };

    const handleLinkNarrator = async (narratorId: string) => {
        if (!selectedTradition) return;
        await linkNarratorToTradition(narratorId, selectedTradition);
        setNarratorSearch('');
        onRefresh();
    };

    const handleUnlinkNarrator = async (narratorId: string) => {
        if (!selectedTradition) return;
        await unlinkNarratorFromTradition(narratorId, selectedTradition);
        onRefresh();
    };

    const currentTradition = traditions.find((t) => t.id === selectedTradition);

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-white">Religious Traditions</h2>
                <Button onClick={() => setIsCreating(true)} className="bg-amber-600 hover:bg-amber-700">
                    <Plus className="w-4 h-4 mr-2" /> Add Tradition
                </Button>
            </div>

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-5">
                    <form onSubmit={handleCreate} className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-slate-300">Name</Label>
                                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    placeholder="e.g., Zoroastrianism" required className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                            <div>
                                <Label className="text-slate-300">Name (Arabic)</Label>
                                <Input value={form.name_arabic} onChange={(e) => setForm({ ...form, name_arabic: e.target.value })}
                                    placeholder="e.g., الزرادشتية" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                        </div>
                        <div>
                            <Label className="text-slate-300">Description</Label>
                            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                                placeholder="Brief description of the tradition" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                        </div>
                        <div>
                            <Label className="text-slate-300">Geographic Heartlands (comma-separated)</Label>
                            <Input value={form.geographic_heartlands} onChange={(e) => setForm({ ...form, geographic_heartlands: e.target.value })}
                                placeholder="e.g., Persia, Khorasan, Sogdia" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                        </div>
                        <div className="flex gap-2">
                            <Button type="submit" className="bg-amber-600 hover:bg-amber-700">Create</Button>
                            <Button type="button" variant="outline" onClick={() => setIsCreating(false)} className="border-slate-600 text-slate-300">Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            <div className="space-y-3">
                {traditions.map((t) => (
                    <Card key={t.id} className={`bg-slate-900 border-slate-700 p-4 cursor-pointer transition-all ${selectedTradition === t.id ? 'border-amber-500/50' : ''}`}>
                        <div className="flex items-start justify-between">
                            <div className="flex-1" onClick={() => setSelectedTradition(selectedTradition === t.id ? null : t.id)}>
                                <div className="flex items-center gap-3 mb-1">
                                    <TraditionBadge tradition={t.name} size="md" />
                                    {t.name_arabic && <span className="text-slate-400 font-arabic">{t.name_arabic}</span>}
                                </div>
                                {t.description && <p className="text-sm text-slate-400 mt-1">{t.description}</p>}
                                {t.geographic_heartlands?.length > 0 && (
                                    <p className="text-xs text-slate-400 mt-1">📍 {t.geographic_heartlands.join(', ')}</p>
                                )}
                                <div className="flex gap-4 mt-2 text-xs text-slate-400">
                                    <span>{t.source_count} source texts</span>
                                    <span>{t.narrator_count} narrators linked</span>
                                </div>
                            </div>
                            <Button size="sm" variant="outline" onClick={() => handleDelete(t.id)}
                                className="border-red-600/30 text-red-400 hover:bg-red-500/10">
                                <Trash2 className="w-4 h-4" />
                            </Button>
                        </div>

                        {/* Narrator linking panel */}
                        {selectedTradition === t.id && (
                            <div className="mt-4 pt-4 border-t border-slate-700">
                                <p className="text-sm font-medium text-slate-300 mb-2">Link Narrators as Tradition Transmitters</p>
                                <div className="flex gap-2 mb-3">
                                    <select
                                        value={narratorSearch}
                                        onChange={(e) => setNarratorSearch(e.target.value)}
                                        className="flex-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm"
                                    >
                                        <option value="">Select a narrator...</option>
                                        {narrators.map((n) => (
                                            <option key={n.id} value={n.id}>{n.name_english} ({n.tabaqah})</option>
                                        ))}
                                    </select>
                                    <Button size="sm" onClick={() => narratorSearch && handleLinkNarrator(narratorSearch)}
                                        className="bg-amber-700 hover:bg-amber-600">Link</Button>
                                </div>
                            </div>
                        )}
                    </Card>
                ))}
            </div>
        </div>
    );
}

// ─── Source Text Manager ─────────────────────────────────────────────────────
function SourceTextManager({ sourceTexts, traditions, onRefresh }: { sourceTexts: any[]; traditions: any[]; onRefresh: () => void }) {
    const [isCreating, setIsCreating] = useState(false);
    const [form, setForm] = useState({
        title: '', title_original: '', tradition_name: '', author: '',
        approximate_date_ce: '', canonical_reference: '', description: '', tradition_id: '',
    });

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const id = await createSourceText(form);
        if (form.tradition_id) {
            await linkSourceTextToTradition(id, form.tradition_id);
        }
        setForm({ title: '', title_original: '', tradition_name: '', author: '', approximate_date_ce: '', canonical_reference: '', description: '', tradition_id: '' });
        setIsCreating(false);
        onRefresh();
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-white">Source Texts</h2>
                <Button onClick={() => setIsCreating(true)} className="bg-sky-600 hover:bg-sky-700">
                    <Plus className="w-4 h-4 mr-2" /> Add Source Text
                </Button>
            </div>

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-5">
                    <form onSubmit={handleCreate} className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-slate-300">Title (English)</Label>
                                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                                    placeholder="e.g., Judgment of the Dead" required className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                            <div>
                                <Label className="text-slate-300">Title (Original Language)</Label>
                                <Input value={form.title_original} onChange={(e) => setForm({ ...form, title_original: e.target.value })}
                                    placeholder="e.g., Chinvat Bridge passage" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-slate-300">Tradition</Label>
                                <select value={form.tradition_id}
                                    onChange={(e) => {
                                        const t = traditions.find((t) => t.id === e.target.value);
                                        setForm({ ...form, tradition_id: e.target.value, tradition_name: t?.name || '' });
                                    }}
                                    required className="w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                                    <option value="">Select Tradition</option>
                                    {traditions.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label className="text-slate-300">Canonical Reference</Label>
                                <Input value={form.canonical_reference} onChange={(e) => setForm({ ...form, canonical_reference: e.target.value })}
                                    placeholder="e.g., Avesta, Yasna 49.11" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-slate-300">Author / Compiler</Label>
                                <Input value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })}
                                    placeholder="e.g., Unknown / Talmudic Sages" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                            <div>
                                <Label className="text-slate-300">Approx. Date (CE)</Label>
                                <Input value={form.approximate_date_ce} onChange={(e) => setForm({ ...form, approximate_date_ce: e.target.value })}
                                    placeholder="e.g., 3rd–5th century CE" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            </div>
                        </div>
                        <div>
                            <Label className="text-slate-300">Description / Context</Label>
                            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                                placeholder="Brief context about this text and its significance" className="mt-1 bg-slate-800 border-slate-700 text-white" />
                        </div>
                        <div className="flex gap-2">
                            <Button type="submit" className="bg-sky-600 hover:bg-sky-700">Create</Button>
                            <Button type="button" variant="outline" onClick={() => setIsCreating(false)} className="border-slate-600 text-slate-300">Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            <div className="space-y-3">
                {sourceTexts.map((s) => (
                    <Card key={s.id} className="bg-slate-900 border-slate-700 p-4">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <h3 className="text-white font-medium">{s.title}</h3>
                                    {s.tradition && <TraditionBadge tradition={s.tradition.name} />}
                                </div>
                                {s.title_original && <p className="text-sm text-slate-400 italic">{s.title_original}</p>}
                                {s.canonical_reference && <p className="text-xs text-slate-400 mt-1">📖 {s.canonical_reference}</p>}
                                {s.author && <p className="text-xs text-slate-400">By {s.author}</p>}
                                {s.approximate_date_ce && <p className="text-xs text-slate-400">~{s.approximate_date_ce}</p>}
                                {s.description && <p className="text-sm text-slate-400 mt-2">{s.description}</p>}
                            </div>
                            <Button size="sm" variant="outline" onClick={() => deleteSourceText(s.id).then(onRefresh)}
                                className="border-red-600/30 text-red-400 hover:bg-red-500/10">
                                <Trash2 className="w-4 h-4" />
                            </Button>
                        </div>
                    </Card>
                ))}
                {sourceTexts.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                        <p className="text-center text-slate-400">No source texts yet. Add one above.</p>
                    </Card>
                )}
            </div>
        </div>
    );
}

// ─── Parallel Manager ────────────────────────────────────────────────────────
function ParallelManager({ parallels, traditions, sourceTexts, motifTags, onRefresh }: {
    parallels: any[]; traditions: any[]; sourceTexts: any[]; motifTags: any[]; onRefresh: () => void;
}) {
    const [isCreating, setIsCreating] = useState(false);
    const [hadithSearch, setHadithSearch] = useState('');
    const [hadithResults, setHadithResults] = useState<any[]>([]);
    const [form, setForm] = useState({
        hadith_id: '', hadith_title: '',
        source_text_id: '', tradition_id: '',
        parallel_type: '', isra_iliyyat_status: 'NONE', confidence_level: 'MEDIUM',
        hadith_excerpt_en: '', source_text_original: '', source_text_en: '',
        scholarly_analysis: '', motif_tag_ids: [] as string[],
    });

    const searchForHadiths = async (term: string) => {
        if (term.length < 2) { setHadithResults([]); return; }
        const results = await searchHadiths(term);
        setHadithResults(results.items);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        await createCrossParallel({
            hadith_id: form.hadith_id,
            source_text_id: form.source_text_id,
            tradition_id: form.tradition_id,
            parallel_type: form.parallel_type as any,
            isra_iliyyat_status: form.isra_iliyyat_status as any,
            confidence_level: form.confidence_level as any,
            hadith_excerpt_en: form.hadith_excerpt_en,
            source_text_original: form.source_text_original,
            source_text_en: form.source_text_en,
            scholarly_analysis: form.scholarly_analysis,
            motif_tag_ids: form.motif_tag_ids,
        });
        setForm({
            hadith_id: '', hadith_title: '', source_text_id: '', tradition_id: '',
            parallel_type: '', isra_iliyyat_status: 'NONE', confidence_level: 'MEDIUM',
            hadith_excerpt_en: '', source_text_original: '', source_text_en: '',
            scholarly_analysis: '', motif_tag_ids: [],
        });
        setHadithSearch('');
        setHadithResults([]);
        setIsCreating(false);
        onRefresh();
    };

    const toggleMotifTag = (tagId: string) => {
        setForm((f) => ({
            ...f,
            motif_tag_ids: f.motif_tag_ids.includes(tagId)
                ? f.motif_tag_ids.filter((id) => id !== tagId)
                : [...f.motif_tag_ids, tagId],
        }));
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-white">Cross-Cultural Parallels</h2>
                <Button onClick={() => setIsCreating(true)} className="bg-emerald-600 hover:bg-emerald-700">
                    <Plus className="w-4 h-4 mr-2" /> New Parallel
                </Button>
            </div>

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-5">
                    <h3 className="text-lg font-semibold text-white mb-4">Create Cross-Cultural Parallel</h3>
                    <form onSubmit={handleCreate} className="space-y-4">
                        {/* Hadith search */}
                        <div>
                            <Label className="text-slate-300">Hadith</Label>
                            <Input value={hadithSearch}
                                onChange={(e) => { setHadithSearch(e.target.value); searchForHadiths(e.target.value); }}
                                placeholder="Search hadith by title..." className="mt-1 bg-slate-800 border-slate-700 text-white" />
                            {form.hadith_id && (
                                <div className="mt-1 flex items-center justify-between p-2 bg-slate-800 rounded text-sm text-white">
                                    <span>{form.hadith_title}</span>
                                    <button type="button" onClick={() => setForm({ ...form, hadith_id: '', hadith_title: '' })}
                                        className="text-xs text-red-400">Remove</button>
                                </div>
                            )}
                            {hadithResults.length > 0 && !form.hadith_id && (
                                <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
                                    {hadithResults.map((h) => (
                                        <button key={h.id} type="button"
                                            onClick={() => { setForm({ ...form, hadith_id: h.id, hadith_title: h.title }); setHadithResults([]); setHadithSearch(''); }}
                                            className="w-full text-left p-2 bg-slate-800 hover:bg-slate-700 rounded text-sm text-slate-300">
                                            {h.title}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            {/* Tradition */}
                            <div>
                                <Label className="text-slate-300">Tradition</Label>
                                <select value={form.tradition_id}
                                    onChange={(e) => setForm({ ...form, tradition_id: e.target.value })}
                                    required className="w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                                    <option value="">Select Tradition</option>
                                    {traditions.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                                </select>
                            </div>
                            {/* Source text */}
                            <div>
                                <Label className="text-slate-300">Source Text</Label>
                                <select value={form.source_text_id}
                                    onChange={(e) => setForm({ ...form, source_text_id: e.target.value })}
                                    required className="w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                                    <option value="">Select Source Text</option>
                                    {sourceTexts
                                        .filter((s) => !form.tradition_id || traditions.find((t) => t.id === form.tradition_id)?.name === s.tradition_name)
                                        .map((s) => <option key={s.id} value={s.id}>{s.title} — {s.canonical_reference}</option>)}
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label className="text-slate-300">Parallel Type</Label>
                                <select value={form.parallel_type}
                                    onChange={(e) => setForm({ ...form, parallel_type: e.target.value })}
                                    required className="w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                                    <option value="">Select Type</option>
                                    {PARALLEL_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label className="text-slate-300">Isra'iliyyat Status</Label>
                                <select value={form.isra_iliyyat_status}
                                    onChange={(e) => setForm({ ...form, isra_iliyyat_status: e.target.value })}
                                    className="w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                                    {ISRA_STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label className="text-slate-300">Confidence</Label>
                                <select value={form.confidence_level}
                                    onChange={(e) => setForm({ ...form, confidence_level: e.target.value })}
                                    className="w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                                    {CONFIDENCE_LEVELS.map((c) => <option key={c} value={c}>{c}</option>)}
                                </select>
                            </div>
                        </div>

                        <div>
                            <Label className="text-slate-300">Hadith Excerpt (English)</Label>
                            <Textarea value={form.hadith_excerpt_en}
                                onChange={(e) => setForm({ ...form, hadith_excerpt_en: e.target.value })}
                                placeholder="The relevant portion of the hadith text..." className="mt-1 bg-slate-800 border-slate-700 text-white" rows={3} />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-slate-300">Source Text (Original Language)</Label>
                                <Textarea value={form.source_text_original}
                                    onChange={(e) => setForm({ ...form, source_text_original: e.target.value })}
                                    placeholder="The parallel text in its original language..." className="mt-1 bg-slate-800 border-slate-700 text-white" rows={3} />
                            </div>
                            <div>
                                <Label className="text-slate-300">Source Text (English Translation)</Label>
                                <Textarea value={form.source_text_en}
                                    onChange={(e) => setForm({ ...form, source_text_en: e.target.value })}
                                    placeholder="English translation of the parallel text..." className="mt-1 bg-slate-800 border-slate-700 text-white" rows={3} />
                            </div>
                        </div>

                        <div>
                            <Label className="text-slate-300">Scholarly Analysis</Label>
                            <Textarea value={form.scholarly_analysis}
                                onChange={(e) => setForm({ ...form, scholarly_analysis: e.target.value })}
                                placeholder="Scholarly notes on the nature of this parallel, transmission vectors, debates..." className="mt-1 bg-slate-800 border-slate-700 text-white" rows={4} />
                        </div>

                        {/* Motif tags */}
                        {motifTags.length > 0 && (
                            <div>
                                <Label className="text-slate-300 mb-2 block">Motif Tags</Label>
                                <div className="flex flex-wrap gap-2">
                                    {motifTags.map((tag) => (
                                        <button key={tag.id} type="button"
                                            onClick={() => toggleMotifTag(tag.id)}
                                            className={`text-xs px-2 py-1 rounded border transition-all ${
                                                form.motif_tag_ids.includes(tag.id)
                                                    ? 'bg-cyan-700 border-cyan-500 text-white'
                                                    : 'bg-slate-800 border-slate-600 text-slate-400 hover:border-slate-400'
                                            }`}>
                                            {tag.name}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2">
                            <Button type="submit" disabled={!form.hadith_id || !form.tradition_id || !form.source_text_id || !form.parallel_type}
                                className="bg-emerald-600 hover:bg-emerald-700">Create Parallel</Button>
                            <Button type="button" variant="outline" onClick={() => setIsCreating(false)} className="border-slate-600 text-slate-300">Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            <div className="space-y-3">
                {parallels.map((p) => (
                    <Card key={p.id} className="bg-slate-900 border-slate-700 p-4">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <div className="flex flex-wrap gap-2 mb-2">
                                    <TraditionBadge tradition={p.tradition?.name ?? ''} />
                                    <ParallelTypeBadge type={p.parallel_type} />
                                    <IsraIliyyatBadge status={p.isra_iliyyat_status} />
                                    <span className="text-xs text-slate-400">{p.confidence_level} confidence</span>
                                </div>
                                <p className="text-sm font-medium text-white">
                                    <BookOpen className="inline w-3.5 h-3.5 mr-1 text-cyan-400" />
                                    {p.hadith?.title}
                                </p>
                                <p className="text-xs text-slate-400 mt-0.5">
                                    ↔ {p.source_text?.title}{p.source_text?.canonical_reference ? ` · ${p.source_text.canonical_reference}` : ''}
                                </p>
                                {p.scholarly_analysis && (
                                    <p className="text-xs text-slate-400 mt-2 line-clamp-2">{p.scholarly_analysis}</p>
                                )}
                            </div>
                            <Button size="sm" variant="outline" onClick={() => deleteParallel(p.id).then(onRefresh)}
                                className="border-red-600/30 text-red-400 hover:bg-red-500/10 ml-3">
                                <Trash2 className="w-4 h-4" />
                            </Button>
                        </div>
                    </Card>
                ))}
                {parallels.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                        <p className="text-center text-slate-400">No parallels yet. Create one above.</p>
                    </Card>
                )}
            </div>
        </div>
    );
}

// ─── Motif Tag Manager ───────────────────────────────────────────────────────
function MotifTagManager({ motifTags, onRefresh }: { motifTags: any[]; onRefresh: () => void }) {
    const [form, setForm] = useState({ name: '', category: '', description: '' });

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        await createMotifTag(form as any);
        setForm({ name: '', category: '', description: '' });
        onRefresh();
    };

    const grouped = MOTIF_CATEGORIES.reduce((acc, cat) => {
        acc[cat] = motifTags.filter((t) => t.category === cat);
        return acc;
    }, {} as Record<string, any[]>);

    return (
        <div className="space-y-4">
            <h2 className="text-xl font-semibold text-white">Motif Tags</h2>

            <Card className="bg-slate-900 border-slate-700 p-5">
                <form onSubmit={handleCreate} className="flex gap-3">
                    <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                        placeholder="Tag name (e.g., Dajjal / Antichrist)" required className="bg-slate-800 border-slate-700 text-white" />
                    <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                        required className="bg-slate-800 border border-slate-700 text-white rounded px-3 py-2">
                        <option value="">Category</option>
                        {MOTIF_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <Button type="submit" className="bg-cyan-700 hover:bg-cyan-800 whitespace-nowrap">
                        <Plus className="w-4 h-4 mr-1" /> Add
                    </Button>
                </form>
            </Card>

            <div className="space-y-4">
                {MOTIF_CATEGORIES.map((cat) => (
                    grouped[cat].length > 0 && (
                        <div key={cat}>
                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">{cat}</p>
                            <div className="flex flex-wrap gap-2">
                                {grouped[cat].map((tag) => (
                                    <div key={tag.id} className="flex items-center gap-1 bg-slate-800 border border-slate-700 rounded px-2 py-1">
                                        <span className="text-sm text-slate-300">{tag.name}</span>
                                        <button onClick={() => deleteMotifTag(tag.id).then(onRefresh)}
                                            className="text-red-400 hover:text-red-300 ml-1">
                                            <Trash2 className="w-3 h-3" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )
                ))}
            </div>
        </div>
    );
}

// ─── Main Export ─────────────────────────────────────────────────────────────
export function ComparativeManagerClient({ traditions, sourceTexts, parallels, motifTags, narrators }: Props) {
    const router = useRouter();
    const refresh = () => router.refresh();

    return (
        <div>
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white">Comparative Studies Manager</h1>
                <p className="text-slate-400 mt-1">
                    Manage cross-cultural parallels between hadiths and Jewish, Christian, and Zoroastrian sources
                </p>
            </div>

            <Tabs defaultValue="parallels" className="w-full">
                <TabsList className="mb-6 bg-slate-900 border border-slate-700 p-1 rounded-lg">
                    <TabsTrigger value="parallels" className="data-[state=active]:bg-emerald-700 data-[state=active]:text-white text-slate-400">
                        Parallels ({parallels.length})
                    </TabsTrigger>
                    <TabsTrigger value="sources" className="data-[state=active]:bg-sky-700 data-[state=active]:text-white text-slate-400">
                        Source Texts ({sourceTexts.length})
                    </TabsTrigger>
                    <TabsTrigger value="traditions" className="data-[state=active]:bg-amber-700 data-[state=active]:text-white text-slate-400">
                        Traditions ({traditions.length})
                    </TabsTrigger>
                    <TabsTrigger value="motifs" className="data-[state=active]:bg-slate-700 data-[state=active]:text-white text-slate-400">
                        Motif Tags ({motifTags.length})
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="parallels">
                    <ParallelManager parallels={parallels} traditions={traditions} sourceTexts={sourceTexts} motifTags={motifTags} onRefresh={refresh} />
                </TabsContent>
                <TabsContent value="sources">
                    <SourceTextManager sourceTexts={sourceTexts} traditions={traditions} onRefresh={refresh} />
                </TabsContent>
                <TabsContent value="traditions">
                    <TraditionManager traditions={traditions} narrators={narrators} onRefresh={refresh} />
                </TabsContent>
                <TabsContent value="motifs">
                    <MotifTagManager motifTags={motifTags} onRefresh={refresh} />
                </TabsContent>
            </Tabs>
        </div>
    );
}
