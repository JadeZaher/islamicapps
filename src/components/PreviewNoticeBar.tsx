'use client';
// Temporary preview notice: see conductor/RUNBOOK.md, Remove after the first release.
import Link from 'next/link';
import { usePathname } from 'next/navigation';

/** The notice line itself (DESIGN.md §Preview notice, an inverted ink band); hidden under /admin, like the public header. */
export function PreviewNoticeBar() {
  const pathname = usePathname();
  if (pathname.startsWith('/admin')) return null;
  return (
    <div role="note" className="bg-notice text-on-notice">
      {/* One text run: http-gate.test.ts matches "Preview: this archive's data is under active review". */}
      <p className="wrap py-2 type-small">
        Preview: this archive&apos;s data is under active review. Identities, gradings and translations may be incomplete or
        unverified.{' '}
        <Link href="/glossary#preview" className="underline underline-offset-[0.2em] focus-visible:outline-on-notice">
          What is a preview?
        </Link>
      </p>
    </div>
  );
}
