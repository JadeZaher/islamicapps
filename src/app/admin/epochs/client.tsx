'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { retireEpoch, updateEpoch } from '@/app/actions/curation/history';
import type { EpochRecord } from '@/db/queries/epoch';
import { formatHijri } from '@/db/queries/timeline-rules';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ConfirmDelete } from '@/app/admin/_components/ConfirmDelete';
import { describeActionError, unwrapAction } from '@/app/admin/_components/actionError';

const VERIFICATION_STATES = [
    { value: 'unverified_seed', label: 'Seed, unverified' },
    { value: 'unverified', label: 'Curator entry, not yet reviewed' },
    { value: 'human_verified', label: 'Reviewed by a curator' },
    { value: 'source_verified', label: 'Checked against the source' },
];

const stateLabel = (value: string) => VERIFICATION_STATES.find((state) => state.value === value)?.label ?? value;

function yearRange(low: number | null, high: number | null): string {
    if (low === null) return 'not recorded';
    return high === null ? formatHijri(low) : `${formatHijri(low)} to ${formatHijri(high)}`;
}

type FormState = {
    name: string;
    name_arabic: string;
    start_year_hijri: string;
    start_year_hijri_latest: string;
    end_year_hijri: string;
    end_year_hijri_latest: string;
    boundary_note: string;
    overview: string;
    verification_status: string;
    publication_ready: boolean;
    citation_id: string;
};

function toForm(epoch: EpochRecord): FormState {
    const text = (value: number | string | null) => (value === null ? '' : String(value));
    return {
        name: epoch.name,
        name_arabic: text(epoch.name_arabic),
        start_year_hijri: text(epoch.start_year_hijri),
        start_year_hijri_latest: text(epoch.start_year_hijri_latest),
        end_year_hijri: text(epoch.end_year_hijri),
        end_year_hijri_latest: text(epoch.end_year_hijri_latest),
        boundary_note: text(epoch.boundary_note),
        overview: text(epoch.overview),
        // Editing a seed row takes it out of the seed, so a later seed run never overwrites the change.
        verification_status: epoch.verification_status === 'unverified_seed' ? 'unverified' : epoch.verification_status,
        publication_ready: epoch.publication_ready,
        citation_id: text(epoch.citation_id),
    };
}

const FIELD = 'mt-1 bg-surface border-control text-ink';

/** Era list grouped by reckoning, with an inline editor for one era at a time. */
export function EpochsManagerClient({ available, epochs }: { available: boolean; epochs: EpochRecord[] }) {
    const router = useRouter();
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<FormState | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    if (!available) {
        return (
            <div>
                <h1 className="mb-4 text-3xl font-bold text-ink">Eras</h1>
                <p className="text-ink-muted">
                    The eras table is not in this database yet. Its migration is pending (src/db/ops/pending/epochs.pending.sql).
                </p>
            </div>
        );
    }

    const groups = new Map<string, EpochRecord[]>();
    for (const epoch of epochs) {
        const key = epoch.tradition_context ? `${epoch.tradition_context} reckoning` : 'Shared periods';
        groups.set(key, [...(groups.get(key) ?? []), epoch]);
    }

    const save = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!editingId || !form) return;
        setSaving(true);
        setError(null);
        try {
            await unwrapAction(updateEpoch(editingId, form));
            setEditingId(null);
            setForm(null);
            router.refresh();
        } catch (failure) {
            setError(describeActionError(failure, 'Could not save the era. Check the fields and try again.'));
        } finally {
            setSaving(false);
        }
    };

    const input = (key: keyof FormState, label: string, type = 'text') => (
        <div>
            <Label htmlFor={`epoch-${key}`} className="text-ink">{label}</Label>
            <Input id={`epoch-${key}`} type={type} value={String(form?.[key] ?? '')} className={FIELD}
                onChange={(event) => setForm((current) => (current ? { ...current, [key]: event.target.value } : current))} />
        </div>
    );

    return (
        <div>
            <h1 className="mb-2 text-3xl font-bold text-ink">Eras</h1>
            <p className="mb-8 text-sm text-ink-muted">
                Hijri years. Where a boundary is disputed it is a range. Publishing needs a reviewed state and a citation.
            </p>
            {[...groups.entries()].map(([group, rows]) => (
                <section key={group} className="mb-10">
                    <h2 className="mb-3 type-label">{group}</h2>
                    <ul className="divide-y divide-rule border-y border-rule">
                        {rows.map((epoch) => (
                            <li key={epoch.id} className={`py-3 ${epoch.parent_epoch_id ? 'ps-6' : ''}`}>
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <p className="font-medium text-ink">{epoch.name}</p>
                                        <p className="text-sm text-ink-muted">
                                            Start {yearRange(epoch.start_year_hijri, epoch.start_year_hijri_latest)} · End{' '}
                                            {epoch.end_year_hijri === null ? 'continuing' : yearRange(epoch.end_year_hijri, epoch.end_year_hijri_latest)} ·{' '}
                                            {stateLabel(epoch.verification_status)}{epoch.publication_ready ? ', published' : ''}
                                        </p>
                                        {epoch.alternate_names.length > 0 && (
                                            <p className="text-xs text-ink-muted">
                                                Also called {epoch.alternate_names.map((alternate) => `${alternate.name} (${alternate.used_by})`).join('; ')}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex shrink-0 gap-2">
                                        <Button size="sm" variant="outline" className="border-rule text-ink"
                                            aria-label={`Edit ${epoch.name}`}
                                            onClick={() => { setEditingId(epoch.id); setForm(toForm(epoch)); setError(null); }}>
                                            Edit
                                        </Button>
                                        <ConfirmDelete itemName="era"
                                            consequence={`Retire "${epoch.name}"? It is hidden from every page. Nothing is erased and an audit record is kept.`}
                                            onConfirm={async () => { await unwrapAction(retireEpoch(epoch.id)); router.refresh(); }} />
                                    </div>
                                </div>
                                {editingId === epoch.id && form && (
                                    <form onSubmit={save} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2" aria-busy={saving}>
                                        {error && <p role="alert" className="text-sm text-danger md:col-span-2">{error}</p>}
                                        {epoch.verification_status === 'unverified_seed' && (
                                            <p className="text-xs text-ink-muted md:col-span-2">
                                                This is seed data. Saving takes it out of the seed, so later seed runs leave it alone.
                                            </p>
                                        )}
                                        {input('name', 'Name (neutral, descriptive)')}
                                        {input('name_arabic', 'Name (Arabic)')}
                                        {input('start_year_hijri', 'Start (earliest)', 'number')}
                                        {input('start_year_hijri_latest', 'Start (latest, if disputed)', 'number')}
                                        {input('end_year_hijri', 'End (earliest; blank if continuing)', 'number')}
                                        {input('end_year_hijri_latest', 'End (latest, if disputed)', 'number')}
                                        <div className="md:col-span-2">
                                            <Label htmlFor="epoch-boundary_note" className="text-ink">Boundary note</Label>
                                            <Textarea id="epoch-boundary_note" value={form.boundary_note} className={FIELD}
                                                onChange={(event) => setForm({ ...form, boundary_note: event.target.value })} />
                                        </div>
                                        <div className="md:col-span-2">
                                            <Label htmlFor="epoch-overview" className="text-ink">Overview</Label>
                                            <Textarea id="epoch-overview" value={form.overview} className={FIELD}
                                                onChange={(event) => setForm({ ...form, overview: event.target.value })} />
                                        </div>
                                        <div>
                                            <Label htmlFor="epoch-verification_status" className="text-ink">Review state</Label>
                                            <select id="epoch-verification_status" value={form.verification_status}
                                                onChange={(event) => setForm({ ...form, verification_status: event.target.value })}
                                                className="mt-1 w-full border border-rule bg-sunken px-3 py-2 text-ink">
                                                {VERIFICATION_STATES.map((state) => <option key={state.value} value={state.value}>{state.label}</option>)}
                                            </select>
                                        </div>
                                        {input('citation_id', 'Citation id')}
                                        <label className="flex items-center gap-2 text-sm text-ink">
                                            <input type="checkbox" checked={form.publication_ready}
                                                onChange={(event) => setForm({ ...form, publication_ready: event.target.checked })} />
                                            Ready to publish
                                        </label>
                                        <div className="flex gap-3 md:col-span-2">
                                            <Button type="submit" disabled={saving} className="bg-accent text-on-accent hover:bg-ink hover:text-paper">
                                                {saving ? 'Saving...' : 'Save'}
                                            </Button>
                                            <Button type="button" variant="outline" disabled={saving} className="border-rule text-ink"
                                                onClick={() => { setEditingId(null); setForm(null); }}>
                                                Cancel
                                            </Button>
                                        </div>
                                    </form>
                                )}
                            </li>
                        ))}
                    </ul>
                </section>
            ))}
        </div>
    );
}
