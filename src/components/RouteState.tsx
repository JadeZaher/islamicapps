'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';

const COLD_START_RETRY_MS = 2000;

interface RouteMessageProps {
  title: string;
  description?: string;
  /** Primary action first, then at most one secondary link. */
  children?: ReactNode;
  footnote?: ReactNode;
  role?: 'alert' | 'status';
}

/**
 * Shared layout for error and not-found screens (DESIGN.md §Empty, loading and error states): a label, a title, one
 * reason, the actions. Flush left in the page grid; an alert gets the 2px danger rule and a danger label.
 */
export function RouteMessage({ title, description, children, footnote, role }: RouteMessageProps) {
  const isError = role === 'alert';
  return (
    <main role={role} className="wrap min-h-[50vh] py-12">
      <div
        className={`max-w-[var(--measure-reading)] pt-3 ${
          isError ? 'border-t-2 border-danger' : 'border-t border-rule-strong'
        }`}
      >
        <p className={`type-label ${isError ? 'text-danger' : ''}`}>{isError ? 'Error' : 'Not found'}</p>
        <h1 className="type-h3 mt-3 text-ink">{title}</h1>
        {description && <p className="mt-2 type-small text-ink-muted">{description}</p>}
        {children && <div className="mt-5 flex flex-wrap items-center gap-4">{children}</div>}
        {footnote && <p className="mt-4 type-code text-ink-muted">{footnote}</p>}
      </div>
    </main>
  );
}

/** Kept for call sites that style a Link as the primary action; Button's default variant is already the primary. */
export const primaryActionClass = '';

interface RouteErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
  title?: string;
  backHref?: string;
  backLabel?: string;
}

/** Error boundary body: logs the digest (never error.message), retries once silently for a waking database. */
export function RouteError({
  error,
  reset,
  title = 'This page is temporarily unavailable',
  backHref = '/',
  backLabel = 'Home',
}: RouteErrorProps) {
  const retried = useRef(false);

  useEffect(() => {
    console.error('Route error', error.digest ?? '');
    if (retried.current) return;
    const timer = setTimeout(() => {
      retried.current = true;
      reset();
    }, COLD_START_RETRY_MS);
    return () => clearTimeout(timer);
  }, [error, reset]);

  return (
    <RouteMessage
      role="alert"
      title={title}
      description="The archive could not be reached. Try again in a moment."
      footnote={error.digest ? `Reference ${error.digest}` : undefined}
    >
      <Button onClick={reset}>Try again</Button>
      <Button asChild variant="link">
        <Link href={backHref}>{backLabel}</Link>
      </Button>
    </RouteMessage>
  );
}
