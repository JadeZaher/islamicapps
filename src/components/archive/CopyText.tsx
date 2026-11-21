'use client';

import { useState } from 'react';
import { CheckIcon, CopyIcon } from '@/components/marks';

/** Plain copyable text with one Copy action; the text stays selectable without JavaScript. */
export function CopyText({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <pre
        aria-label={label}
        className="max-w-[var(--measure-reading)] whitespace-pre-wrap break-words border-s-2 border-rule ps-4 font-sans type-small text-ink"
      >
        {text}
      </pre>
      <button
        type="button"
        className="mt-3 inline-flex h-10 items-center gap-2 border border-ink px-4 text-sm font-semibold text-ink transition-colors duration-[var(--motion-fast)] hover:bg-ink hover:text-paper"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          } catch {
            setCopied(false);
          }
        }}
      >
        {copied ? <CheckIcon decorative /> : <CopyIcon decorative />}
        {copied ? 'Copied' : 'Copy citation'}
      </button>
      <span aria-live="polite" className="sr-only">
        {copied ? 'Citation copied' : ''}
      </span>
    </div>
  );
}
