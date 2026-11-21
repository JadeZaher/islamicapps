import * as React from 'react';

import { cn } from '@/lib/utils';

type ArabicTextProps = Omit<React.HTMLAttributes<HTMLElement>, 'dir' | 'lang'> & {
  /** Element to render; defaults to span so it can sit inline. */
  as?: React.ElementType;
  /** Use "auto" for fields that may mix Arabic and Latin (bios, titles). */
  dir?: 'rtl' | 'auto';
};

/** Arabic run with lang/dir set, Amiri via the `font-arabic` theme token. Line height comes from globals.css. */
export function ArabicText({
  as: Component = 'span',
  dir = 'rtl',
  className,
  ...props
}: ArabicTextProps) {
  return <Component lang="ar" dir={dir} className={cn('font-arabic', className)} {...props} />;
}
