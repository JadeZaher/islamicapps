const VERDICT_STYLES: Record<string, { label: string; className: string }> = {
  thiqa_thabt: { label: 'thiqa thabt', className: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40' },
  thiqa: { label: 'thiqa', className: 'bg-emerald-500/15 text-emerald-200 border-emerald-500/30' },
  'ṣadūq': { label: 'ṣadūq', className: 'bg-lime-500/15 text-lime-200 border-lime-500/30' },
  'lā_baʾsa_bihi': { label: 'lā baʾsa bihi', className: 'bg-lime-500/10 text-lime-200 border-lime-500/20' },
  mukhtalaf_fīhi: { label: 'mukhtalaf fīhi', className: 'bg-amber-500/15 text-amber-200 border-amber-500/30' },
  majhūl: { label: 'majhūl', className: 'bg-slate-500/20 text-slate-200 border-slate-500/30' },
  'ḍaʿīf': { label: 'ḍaʿīf', className: 'bg-orange-500/20 text-orange-200 border-orange-500/40' },
  matrūk: { label: 'matrūk', className: 'bg-rose-500/20 text-rose-200 border-rose-500/40' },
  kadhāb: { label: 'kadhāb', className: 'bg-red-600/25 text-red-200 border-red-600/50' },
  not_applicable: { label: 'ʿadālat al-ṣaḥāba', className: 'bg-cyan-500/15 text-cyan-200 border-cyan-500/30' },
};

/** Legacy v1 codes and the Postgres `narrator_verdict` enum values mapped onto the display vocabulary. */
const LEGACY_VERDICT_KEYS: Record<string, string> = {
  saduq: 'ṣadūq',
  la_basa_bihi: 'lā_baʾsa_bihi',
  mukhtalaf_fihi: 'mukhtalaf_fīhi',
  daif: 'ḍaʿīf',
  matruk: 'matrūk',
  kadhab: 'kadhāb',
  majhul: 'majhūl',
  THIQA: 'thiqa',
  SADUQ: 'ṣadūq',
  DAIF: 'ḍaʿīf',
  MAJHUL: 'majhūl',
  KADHAB: 'kadhāb',
};

/** The one narrator-verdict badge (reliability_consensus). Renders nothing when there is no verdict. */
export function ConsensusBadge({ verdict }: { verdict?: string | null }) {
  if (!verdict) return null;
  const style = VERDICT_STYLES[LEGACY_VERDICT_KEYS[verdict] ?? verdict] ?? {
    label: verdict,
    className: 'bg-white/10 text-white/80 border-white/20',
  };
  return (
    <span className={`inline-block whitespace-nowrap rounded border px-2.5 py-1 text-xs font-semibold ${style.className}`}>
      {style.label}
    </span>
  );
}
