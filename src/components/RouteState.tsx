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

/** Shared layout for error and not-found screens: one heading, one line, one primary action. */
export function RouteMessage({ title, description, children, footnote, role }: RouteMessageProps) {
  return (
    <main
      role={role}
      className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-3 px-6 py-16 text-center"
    >
      <h1 className="text-2xl font-semibold text-slate-100">{title}</h1>
      {description && <p className="text-sm text-slate-400">{description}</p>}
      {children && <div className="mt-3 flex items-center gap-2">{children}</div>}
      {footnote && <p className="mt-2 text-xs text-slate-500">{footnote}</p>}
    </main>
  );
}

/** Primary emerald action used by every route-state screen. */
export const primaryActionClass = 'bg-emerald-600 text-white hover:bg-emerald-500 focus-visible:ring-emerald-400';

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
      <Button onClick={reset} className={primaryActionClass}>
        Try again
      </Button>
      <Button asChild variant="ghost" className="text-slate-300 hover:text-white">
        <Link href={backHref}>{backLabel}</Link>
      </Button>
    </RouteMessage>
  );
}
