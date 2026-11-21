import * as React from 'react';

import { cn } from '@/lib/utils';

/** The three Arabic roles of DESIGN.md §Typography: names beside Latin, report text, a quoted report. */
const ARABIC_ROLE_CLASS = {
  inline: 'arabic-inline',
  reading: 'arabic-reading',
  display: 'arabic-display',
} as const;

type ArabicTextProps = Omit<React.HTMLAttributes<HTMLElement>, 'dir' | 'lang'> & {
  /** Element to render; defaults to span so it can sit inline. */
  as?: React.ElementType;
  /** Use "auto" for fields that may mix Arabic and Latin (bios, titles). */
  dir?: 'rtl' | 'auto';
  /** Size and line height by role; omit to inherit (the caller sets the size). */
  variant?: keyof typeof ARABIC_ROLE_CLASS;
};

/** Arabic run with lang/dir set, Amiri via the `font-arabic` token. Line height 2 comes from globals.css. */
export function ArabicText({
  as: Component = 'span',
  dir = 'rtl',
  variant,
  className,
  ...props
}: ArabicTextProps) {
  return (
    <Component
      lang="ar"
      dir={dir}
      className={cn('font-arabic', variant && ARABIC_ROLE_CLASS[variant], className)}
      {...props}
    />
  );
}
