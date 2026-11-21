'use client';
// Temporary preview notice: see conductor/RUNBOOK.md, Remove after the first release.
import Link from 'next/link';
import { usePathname } from 'next/navigation';

/** The notice line itself; hidden under /admin, like the public header. */
export function PreviewNoticeBar() {
  const pathname = usePathname();
  if (pathname.startsWith('/admin')) return null;
  return (
    <div role="note" className="border-b border-amber-900/50 bg-amber-950/40 px-6 py-2 text-center text-sm text-amber-100">
      Preview: this archive&apos;s data is under active review. Identities, gradings and translations may be incomplete or
      unverified.{' '}
      <Link href="/glossary#preview" className="underline underline-offset-2 hover:text-white">
        What is a preview?
      </Link>
    </div>
  );
}
