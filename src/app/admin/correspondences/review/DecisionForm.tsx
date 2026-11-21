'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { decideReportCorrespondence } from '@/app/actions/curation/correspondence';
import { describeActionError, unwrapAction } from '@/app/admin/_components/actionError';

const DECISIONS = [
  { value: 'confirmed', label: 'Confirm', hint: 'The two texts carry the same report or passage' },
  { value: 'rejected', label: 'Reject', hint: 'Only a formula, a verse or a ruling is shared' },
  { value: 'uncertain', label: 'Uncertain', hint: 'Needs another reader' },
] as const;

const RELATIONS = [
  { value: '', label: 'No reading recorded' },
  { value: 'same_wording', label: 'Same wording' },
  { value: 'same_report_variant_wording', label: 'Variant wording' },
  { value: 'partial_overlap', label: 'Shares a passage' },
  { value: 'same_ruling_different_attribution', label: 'Same ruling, different attribution' },
  { value: 'shared_formula_only', label: 'Shared formula only' },
  { value: 'shared_quran_quotation', label: 'Shared Quran quotation' },
];

interface DecisionFormProps {
  hadithIdA: string;
  hadithIdB: string;
  /** The Arabic hashes of the texts on screen: the decision is bound to them. */
  shaA: string;
  shaB: string;
  current: string | null;
}

/** Records confirm / reject / uncertain through the curation action; refusals show inline. */
export function DecisionForm({ hadithIdA, hadithIdB, shaA, shaB, current }: DecisionFormProps) {
  const router = useRouter();
  const [decision, setDecision] = useState<string>(current ?? '');
  const [relation, setRelation] = useState('');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState<{ kind: 'error' | 'done'; text: string } | null>(null);
  const [pending, startTransition] = useTransition();

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setMessage(null);
    startTransition(async () => {
      try {
        await unwrapAction(
          decideReportCorrespondence({
            hadith_id_a: hadithIdA,
            hadith_id_b: hadithIdB,
            seen_arabic_sha256_a: shaA,
            seen_arabic_sha256_b: shaB,
            decision,
            reviewed_relation: relation,
            note,
          }),
        );
        setMessage({ kind: 'done', text: 'Decision recorded.' });
        router.refresh();
      } catch (error) {
        setMessage({ kind: 'error', text: describeActionError(error, 'The decision could not be recorded.') });
      }
    });
  };

  return (
    <form onSubmit={submit} className="mt-4 space-y-4 text-sm">
      <fieldset>
        <legend className="sr-only">Decision</legend>
        <div className="flex flex-wrap gap-2">
          {DECISIONS.map((option) => (
            <label key={option.value} className={`cursor-pointer border px-3 py-2 ${decision === option.value ? 'border-slate-100 bg-slate-100 text-slate-950' : 'border-slate-700'}`}>
              <input
                type="radio"
                name="decision"
                value={option.value}
                checked={decision === option.value}
                onChange={() => setDecision(option.value)}
                className="sr-only"
              />
              <span className="font-medium">{option.label}</span>
              <span className={`block text-xs ${decision === option.value ? 'text-slate-700' : 'text-slate-500'}`}>{option.hint}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <label className="flex flex-col gap-1 text-slate-400">
        Reviewer&apos;s reading
        <select value={relation} onChange={(event) => setRelation(event.target.value)} className="border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100">
          {RELATIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-slate-400">
        Note
        <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={3} className="border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100" />
      </label>
      <div className="flex items-center gap-4">
        <button type="submit" disabled={!decision || pending} className="border border-emerald-500 px-4 py-2 text-emerald-300 disabled:opacity-40">
          {pending ? 'Recording…' : 'Record decision'}
        </button>
        {message && (
          <p role={message.kind === 'error' ? 'alert' : 'status'} className={message.kind === 'error' ? 'text-red-300' : 'text-slate-300'}>
            {message.text}
          </p>
        )}
      </div>
    </form>
  );
}
