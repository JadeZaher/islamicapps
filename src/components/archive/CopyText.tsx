'use client';

import { useState } from 'react';
import './archive.css';

/** Plain copyable text with one Copy action; the text stays selectable without JavaScript. */
export function CopyText({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <pre
        aria-label={label}
        className="whitespace-pre-wrap break-words border-l border-[color:var(--archive-rule)] pl-[var(--archive-space-3)] font-sans text-sm leading-relaxed text-[color:var(--archive-ink)]"
      >
        {text}
      </pre>
      <button
        type="button"
        className="archive-focus mt-[var(--archive-space-2)] border border-[color:var(--archive-rule)] px-3 py-1 text-sm text-[color:var(--archive-ink)] hover:border-[color:var(--archive-accent)]"
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
        {copied ? 'Copied' : 'Copy citation'}
      </button>
      <span aria-live="polite" className="sr-only">
        {copied ? 'Citation copied' : ''}
      </span>
    </div>
  );
}
