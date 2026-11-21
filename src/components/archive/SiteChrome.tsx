import Link from 'next/link';
import { connection } from 'next/server';
import { getCurrentDatasetVersion, isIndexable } from '@/db/queries/dataset-version';
import { privatePreviewEnabled } from '@/lib/auth/switches';
import { SquareMark } from './Marks';
import './archive.css';

/** Persistent strip on every page while PRIVATE_PREVIEW is on. Resolved per request, never at build time. */
export async function PrivatePreviewBanner() {
  await connection();
  if (!privatePreviewEnabled()) return null;
  return (
    <div
      role="status"
      className="archive sticky top-0 z-50 bg-[color:var(--archive-accent)] text-[color:var(--archive-ground)]"
    >
      <p className="archive-column flex items-center gap-[var(--archive-space-2)] py-[var(--archive-space-2)] text-sm font-medium">
        <SquareMark />
        Private curator preview. This site shows unpublished material and works not cleared for publication. Do not share.
      </p>
    </div>
  );
}

/**
 * Robots meta for the whole site, from the same dataset_versions state as the preview notice: noindex unless the
 * current version is a release and private preview is off. React hoists the tag into <head>.
 */
export async function CrawlPolicy() {
  await connection();
  const version = await getCurrentDatasetVersion().catch(() => null);
  if (isIndexable(version, privatePreviewEnabled())) return null;
  return <meta name="robots" content="noindex, nofollow" />;
}

/** Site footer: the sources reference page, linked from every page. */
export function SiteFooter() {
  return (
    <footer className="archive archive-rule mt-[var(--archive-space-5)]">
      <div className="archive-column flex flex-wrap gap-x-[var(--archive-space-4)] gap-y-[var(--archive-space-2)] py-[var(--archive-space-4)] text-sm text-[color:var(--archive-muted)]">
        <Link href="/sources" className="archive-link text-[color:var(--archive-muted)]">
          Sources and licences
        </Link>
        <Link href="/collections" className="archive-link text-[color:var(--archive-muted)]">
          Collections
        </Link>
        <Link href="/glossary" className="archive-link text-[color:var(--archive-muted)]">
          Glossary
        </Link>
      </div>
    </footer>
  );
}
