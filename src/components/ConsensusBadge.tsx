const VERDICT_STYLES: Record<string, { label: string }> = {
  thiqa_thabt: { label: 'thiqa thabt' },
  thiqa: { label: 'thiqa' },
  'ṣadūq': { label: 'ṣadūq' },
  'lā_baʾsa_bihi': { label: 'lā baʾsa bihi' },
  mukhtalaf_fīhi: { label: 'mukhtalaf fīhi' },
  majhūl: { label: 'majhūl' },
  'ḍaʿīf': { label: 'ḍaʿīf' },
  matrūk: { label: 'matrūk' },
  kadhāb: { label: 'kadhāb' },
  not_applicable: { label: 'ʿadālat al-ṣaḥāba' },
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

/** The one narrator-verdict label (reliability_consensus), muted uppercase with no verdict colour (DESIGN.md §Badges). Renders nothing when there is no verdict. */
export function ConsensusBadge({ verdict }: { verdict?: string | null }) {
  if (!verdict) return null;
  const style = VERDICT_STYLES[LEGACY_VERDICT_KEYS[verdict] ?? verdict] ?? { label: verdict };
  return (
    <span className="type-label inline-block whitespace-nowrap">
      {style.label}
    </span>
  );
}
