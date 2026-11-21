import { ArabicText } from '@/components/ArabicText';
import { cn } from '@/lib/utils';

const ARABIC_CHARACTER = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const TRAILING_SEPARATORS = /[\s\-–—:|(]+$/;

/** Splits a mixed "Latin … Arabic" string at its first Arabic letter. Display only; the text is not altered. */
export function splitLatinArabic(text: string | null | undefined): { latin: string; arabic: string } {
  const value = (text ?? '').trim();
  const index = value.search(ARABIC_CHARACTER);
  if (index === -1) return { latin: value, arabic: '' };
  return { latin: value.slice(0, index).replace(TRAILING_SEPARATORS, ''), arabic: value.slice(index).trim() };
}

/** Latin and Arabic parts of a narrator name; prefers the dedicated Arabic field over Arabic found in the English one. */
export function narratorNameParts(english?: string | null, arabic?: string | null) {
  const split = splitLatinArabic(english);
  return { latin: split.latin, arabic: arabic?.trim() || split.arabic };
}

interface NarratorNameProps {
  english?: string | null;
  arabic?: string | null;
  /** Chains read in Arabic first; lists lead with the transliteration. */
  arabicFirst?: boolean;
  className?: string;
  latinClassName?: string;
  arabicClassName?: string;
}

/** One way to show a narrator's name: transliteration and Arabic on separate lines, Arabic through ArabicText. */
export function NarratorName({
  english,
  arabic,
  arabicFirst = false,
  className,
  latinClassName,
  arabicClassName,
}: NarratorNameProps) {
  const parts = narratorNameParts(english, arabic);
  const latin = parts.latin && <span className={cn('block', latinClassName)}>{parts.latin}</span>;
  const arabicLine = parts.arabic && (
    <ArabicText variant="inline" className={cn('block text-start', arabicClassName)}>{parts.arabic}</ArabicText>
  );
  return (
    <span className={cn('flex min-w-0 flex-col', className)}>
      {arabicFirst ? arabicLine : latin}
      {arabicFirst ? latin : arabicLine}
    </span>
  );
}

/** Chapter and book titles stored as "English - Arabic": same text, Arabic run set in the Arabic face about 1.15x the Latin. */
export function BilingualTitle({ text, className }: { text: string; className?: string }) {
  const { latin, arabic } = splitLatinArabic(text);
  if (!latin || !arabic) {
    return arabic ? <ArabicText className={cn('text-[1.15em]', className)}>{arabic}</ArabicText> : <span className={className}>{latin}</span>;
  }
  return (
    <span className={cn('inline-flex flex-wrap items-baseline gap-x-3', className)}>
      <span>{latin}</span>
      <ArabicText className="text-[1.15em] font-normal">{arabic}</ArabicText>
    </span>
  );
}
