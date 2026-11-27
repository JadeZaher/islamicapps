'use client';

import { useEffect, useId, useRef, useState } from 'react';
import Link from 'next/link';
import type { ChainReviewIndicatorMeta } from './chain-structure';

interface ChainReviewIndicatorProps {
  meta: ChainReviewIndicatorMeta | null;
  className?: string;
  dataChainFix?: string | null;
  dataChainDisposition?: string | null;
}

/**
 * Accessible review indicator with hover/focus/click tooltip explaining how the chain is
 * currently reviewed, with a link to `/method#chain-tiers`.
 */
export function ChainReviewIndicator({ meta, className, dataChainFix, dataChainDisposition }: ChainReviewIndicatorProps) {
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pinned, setPinned] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipId = useId();
  const summaryId = useId();

  const open = pinned || hovered || focused;

  useEffect(() => {
    if (!pinned) return;
    const handlePointerDown = (event: PointerEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setPinned(false);
        setHovered(false);
        setFocused(false);
      }
    };
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [pinned]);

  if (!meta) return null;

  const accessibleSummary = [meta.tierLabel, meta.summary].filter(Boolean).join('. ');

  return (
    <div
      ref={containerRef}
      className={`relative inline-block max-w-full ${className ?? ''}`}
      data-chain-fix={dataChainFix ?? undefined}
      data-chain-disposition={dataChainDisposition ?? undefined}
      data-review-tier={meta.tier}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!containerRef.current?.contains(event.relatedTarget as Node | null)) {
          setFocused(false);
        }
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          event.stopPropagation();
          setPinned(false);
          setHovered(false);
          setFocused(false);
          triggerRef.current?.focus();
        }
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-controls={tooltipId}
        aria-describedby={summaryId}
        onClick={() => setPinned((prev) => !prev)}
        className="group inline-flex cursor-pointer items-baseline gap-1.5 text-start type-small text-ink-muted transition-colors duration-[var(--motion-fast)] hover:text-ink"
      >
        <span className="underline decoration-dotted decoration-ink-muted underline-offset-4 group-hover:decoration-accent">
          {meta.text}
        </span>
        <span
          aria-hidden="true"
          className="inline-flex h-3.5 w-3.5 shrink-0 translate-y-[1px] items-center justify-center border border-control text-[10px] leading-none font-semibold text-ink-muted group-hover:border-accent group-hover:text-accent"
        >
          i
        </span>
      </button>

      <span id={summaryId} hidden>
        {accessibleSummary}
      </span>

      <div
        id={tooltipId}
        role="region"
        aria-label="Chain review details"
        hidden={!open}
        className="absolute start-0 top-full z-30 w-[min(22rem,calc(100vw-2rem))] pt-1"
      >
        <div className="border border-control bg-[var(--color-surface)] p-3 type-small text-ink">
          <div className="flex items-baseline justify-between gap-2">
            <span className="archive-label text-ink">{meta.tierLabel}</span>
            {meta.reviewedAt && <span className="archive-code text-ink-muted">{meta.reviewedAt}</span>}
          </div>

          <p className="mt-1.5 text-xs leading-4 text-ink-muted">
            {meta.summary}
          </p>

          {meta.witness && (
            <p className="mt-2 border-t border-rule pt-2 text-xs leading-4 text-ink-muted">
              <span className="text-ink">Witness:</span> {meta.witness.witness} ({meta.witness.locator})
            </p>
          )}

          <div className="mt-2 border-t border-rule pt-2">
            <Link href={meta.methodHref} className="link-prose text-xs leading-4 font-medium">
              {meta.methodLinkLabel} →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
