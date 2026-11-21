'use client';

import { useId, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    createReligiousTradition,
    deleteTradition,
    createSourceText,
    deleteSourceText,
    createCrossParallel,
    deleteParallel,
    publishParallel,
    createMotifTag,
    deleteMotifTag,
    linkNarratorToTradition,
} from '@/app/actions/curation/comparative';
import { searchHadithsForCuration } from '@/app/actions/curation/search';
import type { ActionResult } from '@/app/actions/curation/result';
import { describeActionError, unwrapAction } from '@/app/admin/_components/actionError';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { TraditionBadge, ParallelTypeBadge, IsraIliyyatBadge } from '@/components/TraditionBadge';
import { isMachineProposed, MachineProposedBadge } from '@/components/CrossCulturalParallelCard';
import { Plus, Archive, BookOpen } from 'lucide-react';

const PARALLEL_TYPES = ['CONDEMNATION', 'CULTURAL_BLEED', 'SHARED_SOURCE', 'DIRECT_BORROWING', 'APOLOGETIC', 'DISPUTED'];
const ISRA_STATUSES = ['MUWAFIQ', 'MUKHALIF', 'MASKUT_ANHU', 'NONE'];
const CONFIDENCE_LEVELS = ['HIGH', 'MEDIUM', 'LOW'];
const MOTIF_CATEGORIES = ['ESCHATOLOGY', 'CREATION', 'PROPHETIC_STORIES', 'LEGAL', 'WISDOM', 'PERSIAN_INFLUENCE', 'COSMOLOGY'];

const STATUS_LABELS: Record<string, string> = { proposed: 'Proposed', verified: 'Verified', published: 'Published' };

const hadithLabel = (hadith: { title?: string | null; source?: string; hadith_no?: string | null }): string =>
    hadith.title || [hadith.source, hadith.hadith_no].filter(Boolean).join(' ') || 'Untitled hadith';

const SELECT_CLASS = 'w-full mt-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm';
const FIELD_CLASS = 'mt-1 bg-slate-800 border-slate-700 text-white';

interface Props {
    traditions: any[];
    sourceTexts: any[];
    parallels: any[];
    motifTags: any[];
    narrators: any[];
}

// ─── Shared hooks and primitives ─────────────────────────────────────────────

/** Runs one server action at a time: exposes `pending`, an inline `error`, and refreshes on success. */
function useActionRunner(onRefresh: () => void) {
    const [pending, setPending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const inFlight = useRef(false);

    const run = async (task: () => Promise<ActionResult<unknown>>, failureMessage: string): Promise<boolean> => {
        if (inFlight.current) return false;
        inFlight.current = true;
        setPending(true);
        setError(null);
        try {
            await unwrapAction(task());
            onRefresh();
            return true;
        } catch (cause) {
            setError(describeActionError(cause, failureMessage));
            return false;
        } finally {
            inFlight.current = false;
            setPending(false);
        }
    };

    return { pending, error, run, clearError: () => setError(null) };
}

function ErrorBanner({ message, onDismiss }: { message: string | null; onDismiss: () => void }) {
    if (!message) return null;
    return (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <span>{message}</span>
            <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="text-red-300 hover:text-white">
                &times;
            </button>
        </div>
    );
}

/** Two-step retire (nothing is erased): archive icon first, then explicit Retire / Cancel. */
function DeleteButton({ label, consequence, onConfirm, disabled, compact = false }: {
    label: string;
    consequence?: string;
    onConfirm: () => void;
    disabled?: boolean;
    compact?: boolean;
}) {
    const [confirming, setConfirming] = useState(false);

    if (!confirming) {
        return (
            <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={disabled}
                aria-label={label}
                onClick={() => setConfirming(true)}
                className={compact
                    ? 'h-6 w-6 p-0 border-0 text-red-400 hover:bg-red-500/10'
                    : 'border-red-600/30 text-red-400 hover:bg-red-500/10'}
            >
                <Archive aria-hidden="true" className={compact ? 'w-3 h-3' : 'w-4 h-4'} />
            </Button>
        );
    }

    return (
        <div role="group" aria-label={`Confirm: ${label}`} className="flex flex-col items-end gap-1">
            {consequence && <p className="text-xs text-red-300 max-w-48 text-right">{consequence}</p>}
            <div className="flex gap-1">
                <Button
                    type="button"
                    size="sm"
                    disabled={disabled}
                    autoFocus
                    onClick={() => { setConfirming(false); onConfirm(); }}
                    className="bg-red-600 hover:bg-red-700 text-white"
                >
                    Retire
                </Button>
                <Button type="button" size="sm" variant="outline" onClick={() => setConfirming(false)} className="border-slate-600 text-slate-300">
                    Cancel
                </Button>
            </div>
        </div>
    );
}

// ─── Tradition Manager ───────────────────────────────────────────────────────
function TraditionManager({ traditions, narrators, onRefresh }: { traditions: any[]; narrators: any[]; onRefresh: () => void }) {
    const formId = useId();
    const { pending, error, run, clearError } = useActionRunner(onRefresh);
    const [isCreating, setIsCreating] = useState(false);
    const [form, setForm] = useState({ name: '', name_arabic: '', description: '', geographic_heartlands: '' });
    const [narratorId, setNarratorId] = useState('');
    const [selectedTradition, setSelectedTradition] = useState<string | null>(null);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const created = await run(
            () => createReligiousTradition({
                ...form,
                geographic_heartlands: form.geographic_heartlands.split(',').map((s) => s.trim()).filter(Boolean),
            }),
            "Couldn't create the tradition. Try again.",
        );
        if (created) {
            setForm({ name: '', name_arabic: '', description: '', geographic_heartlands: '' });
            setIsCreating(false);
        }
    };

    const handleDelete = (id: string) => {
        if (selectedTradition === id) setSelectedTradition(null);
        return run(() => deleteTradition(id), "Couldn't retire the tradition. Try again.");
    };

    const handleLinkNarrator = async () => {
        if (!selectedTradition || !narratorId) return;
        const linked = await run(
            () => linkNarratorToTradition(narratorId, selectedTradition),
            "Couldn't link the narrator. Try again.",
        );
        if (linked) setNarratorId('');
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-white">Religious Traditions</h2>
                <Button type="button" onClick={() => setIsCreating(true)} disabled={isCreating} className="bg-amber-600 hover:bg-amber-700">
                    <Plus className="w-4 h-4 mr-2" /> Add Tradition
                </Button>
            </div>

            <ErrorBanner message={error} onDismiss={clearError} />

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-5">
                    <form onSubmit={handleCreate} className="space-y-3" aria-busy={pending}>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-name`} className="text-slate-300">Name</Label>
                                <Input id={`${formId}-name`} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    placeholder="e.g., Zoroastrianism" required className={FIELD_CLASS} />
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-name-ar`} className="text-slate-300">Name (Arabic)</Label>
                                <Input id={`${formId}-name-ar`} lang="ar" dir="rtl" value={form.name_arabic} onChange={(e) => setForm({ ...form, name_arabic: e.target.value })}
                                    placeholder="e.g., الزرادشتية" className={`${FIELD_CLASS} font-arabic`} />
                            </div>
                        </div>
                        <div>
                            <Label htmlFor={`${formId}-description`} className="text-slate-300">Description</Label>
                            <Textarea id={`${formId}-description`} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                                placeholder="Brief description of the tradition" className={FIELD_CLASS} />
                        </div>
                        <div>
                            <Label htmlFor={`${formId}-heartlands`} className="text-slate-300">Geographic Heartlands (comma-separated)</Label>
                            <Input id={`${formId}-heartlands`} value={form.geographic_heartlands} onChange={(e) => setForm({ ...form, geographic_heartlands: e.target.value })}
                                placeholder="e.g., Persia, Khorasan, Sogdia" className={FIELD_CLASS} />
                        </div>
                        <div className="flex gap-2">
                            <Button type="submit" disabled={pending} className="bg-amber-600 hover:bg-amber-700">
                                {pending ? 'Creating...' : 'Create'}
                            </Button>
                            <Button type="button" variant="outline" disabled={pending} onClick={() => setIsCreating(false)} className="border-slate-600 text-slate-300">Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            <div className="space-y-3">
                {traditions.map((t) => (
                    <Card key={t.id} className={`bg-slate-900 border-slate-700 p-4 transition-all ${selectedTradition === t.id ? 'border-amber-500/50' : ''}`}>
                        <div className="flex items-start justify-between gap-3">
                            <button
                                type="button"
                                aria-expanded={selectedTradition === t.id}
                                aria-controls={`${formId}-link-${t.id}`}
                                onClick={() => setSelectedTradition(selectedTradition === t.id ? null : t.id)}
                                className="flex-1 text-left rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/60"
                            >
                                <span className="flex items-center gap-3 mb-1">
                                    <TraditionBadge tradition={t.name} size="md" />
                                    {t.name_arabic && <span lang="ar" dir="rtl" className="text-slate-400 font-arabic">{t.name_arabic}</span>}
                                </span>
                                {t.description && <span className="block text-sm text-slate-400 mt-1">{t.description}</span>}
                                {t.geographic_heartlands?.length > 0 && (
                                    <span className="block text-xs text-slate-400 mt-1">Heartlands: {t.geographic_heartlands.join(', ')}</span>
                                )}
                                <span className="flex gap-4 mt-2 text-xs text-slate-400">
                                    <span>{t.source_count} source texts</span>
                                    <span>{t.narrator_count} narrators linked</span>
                                </span>
                            </button>
                            <DeleteButton
                                label={`Retire tradition ${t.name}`}
                                consequence="Hidden, not erased. Refused while parallels or source texts still use it."
                                disabled={pending}
                                onConfirm={() => handleDelete(t.id)}
                            />
                        </div>

                        {selectedTradition === t.id && (
                            <div id={`${formId}-link-${t.id}`} className="mt-4 pt-4 border-t border-slate-700">
                                <Label htmlFor={`${formId}-narrator-${t.id}`} className="text-sm font-medium text-slate-300 mb-2">
                                    Link a narrator as transmitter
                                </Label>
                                <div className="flex gap-2 mt-2">
                                    <select
                                        id={`${formId}-narrator-${t.id}`}
                                        value={narratorId}
                                        onChange={(e) => setNarratorId(e.target.value)}
                                        className="flex-1 bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm"
                                    >
                                        <option value="">Select a narrator...</option>
                                        {narrators.map((n) => (
                                            <option key={n.id} value={n.id}>{n.name_english} ({n.tabaqah})</option>
                                        ))}
                                    </select>
                                    <Button type="button" size="sm" disabled={!narratorId || pending} onClick={handleLinkNarrator}
                                        className="bg-amber-700 hover:bg-amber-600">
                                        {pending ? 'Linking...' : 'Link'}
                                    </Button>
                                </div>
                            </div>
                        )}
                    </Card>
                ))}
                {traditions.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                        <p className="text-center text-slate-400">No traditions yet.</p>
                    </Card>
                )}
            </div>
        </div>
    );
}

// ─── Source Text Manager ─────────────────────────────────────────────────────
const EMPTY_SOURCE_FORM = {
    title: '', title_original: '', tradition_name: '', author: '',
    approximate_date_ce: '', canonical_reference: '', description: '', tradition_id: '',
};

function SourceTextManager({ sourceTexts, traditions, onRefresh }: { sourceTexts: any[]; traditions: any[]; onRefresh: () => void }) {
    const formId = useId();
    const { pending, error, run, clearError } = useActionRunner(onRefresh);
    const [isCreating, setIsCreating] = useState(false);
    const [form, setForm] = useState(EMPTY_SOURCE_FORM);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const created = await run(() => createSourceText(form), "Couldn't create the source text. Try again.");
        if (created) {
            setForm(EMPTY_SOURCE_FORM);
            setIsCreating(false);
        }
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-white">Source Texts</h2>
                <Button type="button" onClick={() => setIsCreating(true)} disabled={isCreating} className="bg-sky-600 hover:bg-sky-700">
                    <Plus className="w-4 h-4 mr-2" /> Add Source Text
                </Button>
            </div>

            <ErrorBanner message={error} onDismiss={clearError} />

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-5">
                    <form onSubmit={handleCreate} className="space-y-3" aria-busy={pending}>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-title`} className="text-slate-300">Title (English)</Label>
                                <Input id={`${formId}-title`} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                                    placeholder="e.g., Judgment of the Dead" required className={FIELD_CLASS} />
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-title-original`} className="text-slate-300">Title (Original Language)</Label>
                                <Input id={`${formId}-title-original`} dir="auto" value={form.title_original} onChange={(e) => setForm({ ...form, title_original: e.target.value })}
                                    placeholder="e.g., Chinvat Bridge passage" className={FIELD_CLASS} />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-tradition`} className="text-slate-300">Tradition</Label>
                                <select id={`${formId}-tradition`} value={form.tradition_id}
                                    onChange={(e) => {
                                        const t = traditions.find((t) => t.id === e.target.value);
                                        setForm({ ...form, tradition_id: e.target.value, tradition_name: t?.name || '' });
                                    }}
                                    required className={SELECT_CLASS}>
                                    <option value="">Select Tradition</option>
                                    {traditions.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-reference`} className="text-slate-300">Canonical Reference</Label>
                                <Input id={`${formId}-reference`} value={form.canonical_reference} onChange={(e) => setForm({ ...form, canonical_reference: e.target.value })}
                                    placeholder="e.g., Avesta, Yasna 49.11" className={FIELD_CLASS} />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-author`} className="text-slate-300">Author / Compiler</Label>
                                <Input id={`${formId}-author`} value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })}
                                    placeholder="e.g., Unknown / Talmudic Sages" className={FIELD_CLASS} />
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-date`} className="text-slate-300">Approx. Date (CE)</Label>
                                <Input id={`${formId}-date`} value={form.approximate_date_ce} onChange={(e) => setForm({ ...form, approximate_date_ce: e.target.value })}
                                    placeholder="e.g., 3rd–5th century CE" className={FIELD_CLASS} />
                            </div>
                        </div>
                        <div>
                            <Label htmlFor={`${formId}-description`} className="text-slate-300">Description / Context</Label>
                            <Textarea id={`${formId}-description`} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                                placeholder="Brief context about this text and its significance" className={FIELD_CLASS} />
                        </div>
                        <div className="flex gap-2">
                            <Button type="submit" disabled={pending} className="bg-sky-600 hover:bg-sky-700">
                                {pending ? 'Creating...' : 'Create'}
                            </Button>
                            <Button type="button" variant="outline" disabled={pending} onClick={() => setIsCreating(false)} className="border-slate-600 text-slate-300">Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            <div className="space-y-3">
                {sourceTexts.map((s) => (
                    <Card key={s.id} className="bg-slate-900 border-slate-700 p-4">
                        <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <h3 className="text-white font-medium">{s.title}</h3>
                                    {s.tradition && <TraditionBadge tradition={s.tradition.name} />}
                                </div>
                                {s.title_original && <p dir="auto" className="text-sm text-slate-400 italic text-start">{s.title_original}</p>}
                                {s.canonical_reference && <p className="text-xs text-slate-400 mt-1">Reference: {s.canonical_reference}</p>}
                                {s.author && <p className="text-xs text-slate-400">By {s.author}</p>}
                                {s.approximate_date_ce && <p className="text-xs text-slate-400">~{s.approximate_date_ce}</p>}
                                {s.description && <p className="text-sm text-slate-400 mt-2">{s.description}</p>}
                            </div>
                            <DeleteButton
                                label={`Retire source text ${s.title}`}
                                consequence="Hidden, not erased. Refused while parallels still cite it."
                                disabled={pending}
                                onConfirm={() => run(() => deleteSourceText(s.id), "Couldn't retire the source text. Try again.")}
                            />
                        </div>
                    </Card>
                ))}
                {sourceTexts.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                        <p className="text-center text-slate-400">No source texts yet.</p>
                    </Card>
                )}
            </div>
        </div>
    );
}

// ─── Parallel Manager ────────────────────────────────────────────────────────
const EMPTY_PARALLEL_FORM = {
    hadith_id: '', hadith_title: '',
    source_text_id: '', tradition_id: '',
    parallel_type: '', isra_iliyyat_status: 'NONE', confidence_level: 'MEDIUM',
    hadith_excerpt_en: '', source_text_original: '', source_text_en: '',
    scholarly_analysis: '', motif_tag_ids: [] as string[],
};

function ParallelManager({ parallels, traditions, sourceTexts, motifTags, onRefresh }: {
    parallels: any[]; traditions: any[]; sourceTexts: any[]; motifTags: any[]; onRefresh: () => void;
}) {
    const formId = useId();
    const { pending, error, run, clearError } = useActionRunner(onRefresh);
    const [isCreating, setIsCreating] = useState(false);
    const [hadithSearch, setHadithSearch] = useState('');
    const [hadithResults, setHadithResults] = useState<any[]>([]);
    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState<string | null>(null);
    const latestSearch = useRef(0);
    const [form, setForm] = useState(EMPTY_PARALLEL_FORM);

    const searchForHadiths = async (term: string) => {
        const ticket = ++latestSearch.current;
        setSearchError(null);
        if (term.length < 2) { setHadithResults([]); setSearching(false); return; }
        setSearching(true);
        try {
            const results = await unwrapAction(searchHadithsForCuration(term));
            if (ticket === latestSearch.current) setHadithResults(results.items);
        } catch (cause) {
            if (ticket === latestSearch.current) setSearchError(describeActionError(cause, "Couldn't search hadiths. Try again."));
        } finally {
            if (ticket === latestSearch.current) setSearching(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const created = await run(() => createCrossParallel({
            hadith_id: form.hadith_id,
            source_text_id: form.source_text_id,
            tradition_id: form.tradition_id,
            parallel_type: form.parallel_type,
            isra_iliyyat_status: form.isra_iliyyat_status,
            confidence_level: form.confidence_level,
            hadith_excerpt_en: form.hadith_excerpt_en,
            source_text_original: form.source_text_original,
            source_text_en: form.source_text_en,
            scholarly_analysis: form.scholarly_analysis,
            motif_tag_ids: form.motif_tag_ids,
        }), "Couldn't create the parallel. Try again.");
        if (created) {
            setForm(EMPTY_PARALLEL_FORM);
            setHadithSearch('');
            setHadithResults([]);
            setIsCreating(false);
        }
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
                <Button type="button" onClick={() => setIsCreating(true)} disabled={isCreating} className="bg-emerald-600 hover:bg-emerald-700">
                    <Plus className="w-4 h-4 mr-2" /> New Parallel
                </Button>
            </div>

            <ErrorBanner message={error} onDismiss={clearError} />

            {isCreating && (
                <Card className="bg-slate-900 border-slate-700 p-5">
                    <h3 className="text-lg font-semibold text-white mb-4">Create Cross-Cultural Parallel</h3>
                    <form onSubmit={handleCreate} className="space-y-4" aria-busy={pending}>
                        <div>
                            <Label htmlFor={`${formId}-hadith`} className="text-slate-300">Hadith</Label>
                            <Input id={`${formId}-hadith`} value={hadithSearch}
                                onChange={(e) => { setHadithSearch(e.target.value); searchForHadiths(e.target.value); }}
                                placeholder="Search hadith by title..." className={FIELD_CLASS} />
                            {searching && <p role="status" className="mt-1 text-xs text-slate-400">Searching...</p>}
                            {searchError && <p role="alert" className="mt-1 text-xs text-red-300">{searchError}</p>}
                            {form.hadith_id && (
                                <div className="mt-1 flex items-center justify-between p-2 bg-slate-800 rounded text-sm text-white">
                                    <span>{form.hadith_title}</span>
                                    <button type="button" onClick={() => setForm({ ...form, hadith_id: '', hadith_title: '' })}
                                        aria-label={`Remove selected hadith ${form.hadith_title}`}
                                        className="text-xs text-red-400">Remove</button>
                                </div>
                            )}
                            {hadithResults.length > 0 && !form.hadith_id && (
                                <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
                                    {hadithResults.map((h) => (
                                        <button key={h.id} type="button"
                                            onClick={() => { setForm({ ...form, hadith_id: h.id, hadith_title: hadithLabel(h) }); setHadithResults([]); setHadithSearch(''); }}
                                            className="w-full text-left p-2 bg-slate-800 hover:bg-slate-700 rounded text-sm text-slate-300">
                                            {hadithLabel(h)}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-tradition`} className="text-slate-300">Tradition</Label>
                                <select id={`${formId}-tradition`} value={form.tradition_id}
                                    onChange={(e) => setForm({ ...form, tradition_id: e.target.value })}
                                    required className={SELECT_CLASS}>
                                    <option value="">Select Tradition</option>
                                    {traditions.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-source`} className="text-slate-300">Source Text</Label>
                                <select id={`${formId}-source`} value={form.source_text_id}
                                    onChange={(e) => setForm({ ...form, source_text_id: e.target.value })}
                                    required className={SELECT_CLASS}>
                                    <option value="">Select Source Text</option>
                                    {sourceTexts
                                        .filter((s) => !form.tradition_id || traditions.find((t) => t.id === form.tradition_id)?.name === s.tradition_name)
                                        .map((s) => <option key={s.id} value={s.id}>{s.title} — {s.canonical_reference}</option>)}
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-type`} className="text-slate-300">Parallel Type</Label>
                                <select id={`${formId}-type`} value={form.parallel_type}
                                    onChange={(e) => setForm({ ...form, parallel_type: e.target.value })}
                                    required className={SELECT_CLASS}>
                                    <option value="">Select Type</option>
                                    {PARALLEL_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-isra`} className="text-slate-300">Isra'iliyyat Status</Label>
                                <select id={`${formId}-isra`} value={form.isra_iliyyat_status}
                                    onChange={(e) => setForm({ ...form, isra_iliyyat_status: e.target.value })}
                                    className={SELECT_CLASS}>
                                    {ISRA_STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                                </select>
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-confidence`} className="text-slate-300">Confidence</Label>
                                <select id={`${formId}-confidence`} value={form.confidence_level}
                                    onChange={(e) => setForm({ ...form, confidence_level: e.target.value })}
                                    className={SELECT_CLASS}>
                                    {CONFIDENCE_LEVELS.map((c) => <option key={c} value={c}>{c}</option>)}
                                </select>
                            </div>
                        </div>

                        <div>
                            <Label htmlFor={`${formId}-excerpt`} className="text-slate-300">Hadith Excerpt (English)</Label>
                            <Textarea id={`${formId}-excerpt`} value={form.hadith_excerpt_en}
                                onChange={(e) => setForm({ ...form, hadith_excerpt_en: e.target.value })}
                                placeholder="The relevant portion of the hadith text..." className={FIELD_CLASS} rows={3} />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label htmlFor={`${formId}-source-original`} className="text-slate-300">Source Text (Original Language)</Label>
                                <Textarea id={`${formId}-source-original`} dir="auto" value={form.source_text_original}
                                    onChange={(e) => setForm({ ...form, source_text_original: e.target.value })}
                                    placeholder="The parallel text in its original language..." className={FIELD_CLASS} rows={3} />
                            </div>
                            <div>
                                <Label htmlFor={`${formId}-source-en`} className="text-slate-300">Source Text (English Translation)</Label>
                                <Textarea id={`${formId}-source-en`} value={form.source_text_en}
                                    onChange={(e) => setForm({ ...form, source_text_en: e.target.value })}
                                    placeholder="English translation of the parallel text..." className={FIELD_CLASS} rows={3} />
                            </div>
                        </div>

                        <div>
                            <Label htmlFor={`${formId}-analysis`} className="text-slate-300">Scholarly Analysis</Label>
                            <Textarea id={`${formId}-analysis`} value={form.scholarly_analysis}
                                onChange={(e) => setForm({ ...form, scholarly_analysis: e.target.value })}
                                placeholder="Scholarly notes on the nature of this parallel, transmission vectors, debates..." className={FIELD_CLASS} rows={4} />
                        </div>

                        {motifTags.length > 0 && (
                            <fieldset>
                                <legend className="text-sm font-medium text-slate-300 mb-2">Motif Tags</legend>
                                <div className="flex flex-wrap gap-2">
                                    {motifTags.map((tag) => (
                                        <button key={tag.id} type="button"
                                            aria-pressed={form.motif_tag_ids.includes(tag.id)}
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
                            </fieldset>
                        )}

                        <div className="flex gap-2">
                            <Button type="submit" disabled={pending || !form.hadith_id || !form.tradition_id || !form.source_text_id || !form.parallel_type}
                                className="bg-emerald-600 hover:bg-emerald-700">
                                {pending ? 'Creating...' : 'Create Parallel'}
                            </Button>
                            <Button type="button" variant="outline" disabled={pending} onClick={() => setIsCreating(false)} className="border-slate-600 text-slate-300">Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            <div className="space-y-3">
                {parallels.map((p) => (
                    <Card key={p.id} className="bg-slate-900 border-slate-700 p-4">
                        <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                                <div className="flex flex-wrap gap-2 mb-2">
                                    <TraditionBadge tradition={p.tradition?.name ?? ''} />
                                    <ParallelTypeBadge type={p.parallel_type} />
                                    <IsraIliyyatBadge status={p.isra_iliyyat_status} />
                                    {isMachineProposed(p) && <MachineProposedBadge />}
                                    <span className="text-xs text-slate-400">{p.confidence_level} confidence</span>
                                    <span
                                        className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${
                                            p.status === 'published'
                                                ? 'border-emerald-500/30 bg-emerald-500/15 text-emerald-300'
                                                : 'border-slate-600 bg-slate-800 text-slate-300'
                                        }`}
                                    >
                                        {STATUS_LABELS[p.status] ?? p.status}
                                    </span>
                                </div>
                                <p className="text-sm font-medium text-white">
                                    <BookOpen aria-hidden="true" className="inline w-3.5 h-3.5 mr-1 text-cyan-400" />
                                    {p.hadith ? hadithLabel(p.hadith) : ''}
                                </p>
                                <p className="text-xs text-slate-400 mt-0.5">
                                    ↔ {p.source_text?.title}{p.source_text?.canonical_reference ? ` · ${p.source_text.canonical_reference}` : ''}
                                </p>
                                {p.scholarly_analysis && (
                                    <p className="text-xs text-slate-400 mt-2 line-clamp-2">{p.scholarly_analysis}</p>
                                )}
                            </div>
                            <div className="flex items-start gap-2">
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    disabled={pending}
                                    onClick={() =>
                                        p.status === 'published'
                                            ? run(() => publishParallel(p.id, 'proposed'), "Couldn't unpublish the parallel.")
                                            : run(() => publishParallel(p.id, 'published'), "Couldn't publish the parallel.")
                                    }
                                    className="border-slate-600 text-slate-300"
                                >
                                    {p.status === 'published' ? 'Unpublish' : 'Publish'}
                                </Button>
                                <DeleteButton
                                    label={`Retire parallel ${p.hadith ? hadithLabel(p.hadith) : ''}`.trim()}
                                    consequence="Hidden, not erased."
                                    disabled={pending}
                                    onConfirm={() => run(() => deleteParallel(p.id), "Couldn't retire the parallel. Try again.")}
                                />
                            </div>
                        </div>
                    </Card>
                ))}
                {parallels.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                        <p className="text-center text-slate-400">No parallels yet.</p>
                    </Card>
                )}
            </div>
        </div>
    );
}

// ─── Motif Tag Manager ───────────────────────────────────────────────────────
function MotifTagManager({ motifTags, onRefresh }: { motifTags: any[]; onRefresh: () => void }) {
    const formId = useId();
    const { pending, error, run, clearError } = useActionRunner(onRefresh);
    const [form, setForm] = useState({ name: '', category: '', description: '' });

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const created = await run(() => createMotifTag(form), "Couldn't add the tag. Try again.");
        if (created) setForm({ name: '', category: '', description: '' });
    };

    const grouped = MOTIF_CATEGORIES.reduce((acc, cat) => {
        acc[cat] = motifTags.filter((t) => t.category === cat);
        return acc;
    }, {} as Record<string, any[]>);

    return (
        <div className="space-y-4">
            <h2 className="text-xl font-semibold text-white">Motif Tags</h2>

            <ErrorBanner message={error} onDismiss={clearError} />

            <Card className="bg-slate-900 border-slate-700 p-5">
                <form onSubmit={handleCreate} className="flex gap-3" aria-busy={pending}>
                    <Input id={`${formId}-name`} aria-label="Tag name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                        placeholder="Tag name (e.g., Dajjal / Antichrist)" required className="bg-slate-800 border-slate-700 text-white" />
                    <select id={`${formId}-category`} aria-label="Tag category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                        required className="bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm">
                        <option value="">Category</option>
                        {MOTIF_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <Button type="submit" disabled={pending} className="bg-cyan-700 hover:bg-cyan-800 whitespace-nowrap">
                        <Plus className="w-4 h-4 mr-1" /> {pending ? 'Adding...' : 'Add'}
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
                                        <DeleteButton
                                            compact
                                            label={`Retire tag ${tag.name}`}
                                            disabled={pending}
                                            onConfirm={() => run(() => deleteMotifTag(tag.id), "Couldn't retire the tag. Try again.")}
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>
                    )
                ))}
                {motifTags.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                        <p className="text-center text-slate-400">No motif tags yet.</p>
                    </Card>
                )}
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
            <h1 className="text-3xl font-bold text-white mb-8">Comparative Studies</h1>

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
