/** Canonical corpus traditions and their reader-facing labels. */
export type HadithTradition = 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';

const TRADITION_DETAILS: Record<HadithTradition, { label: string; aliases: readonly string[] }> = {
  Sunni: { label: 'Sunni', aliases: ['Sunni'] },
  Imami: { label: 'Twelver Shia · Imami', aliases: ['Imami', 'Shia Imami', 'Shia'] },
  Zaydi: { label: 'Zaydi Shia · Zaydi', aliases: ['Zaydi', 'Shia Zaydi'] },
  Ibadi: { label: 'Ibadi', aliases: ['Ibadi'] },
};

export const HADITH_TRADITION_OPTIONS = [
  { label: 'All traditions', value: '' },
  ...Object.entries(TRADITION_DETAILS).map(([value, detail]) => ({
    label: detail.label,
    value,
    aliases: detail.aliases.filter((alias) => alias !== value),
  })),
];

export function getTraditionFilterValues(tradition: string): readonly string[] {
  const normalized = tradition.trim();
  const entry = Object.entries(TRADITION_DETAILS).find(([canonical, detail]) =>
    canonical.toLowerCase() === normalized.toLowerCase() ||
    detail.aliases.some((alias) => alias.toLowerCase() === normalized.toLowerCase()),
  );
  return entry?.[1].aliases ?? [normalized];
}

export function displayHadithTradition(tradition: string | null | undefined): string {
  if (!tradition) return 'Unspecified tradition';
  const normalized = tradition.trim();
  const entry = Object.entries(TRADITION_DETAILS).find(([, detail]) =>
    detail.aliases.some((alias) => alias.toLowerCase() === normalized.toLowerCase()),
  );
  return entry ? entry[1].label : normalized;
}
