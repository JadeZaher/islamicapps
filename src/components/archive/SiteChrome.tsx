import Link from 'next/link';
import { connection } from 'next/server';
import { getCurrentDatasetVersion, isIndexable } from '@/db/queries/dataset-version';
import { privatePreviewEnabled } from '@/lib/auth/switches';
import { SquareMark } from './Marks';

/** Persistent strip on every page while PRIVATE_PREVIEW is on. Resolved per request, never at build time. */
export async function PrivatePreviewBanner() {
  await connection();
  if (!privatePreviewEnabled()) return null;
  return (
    <div role="status" className="sticky top-0 z-50 bg-notice text-on-notice">
      <p className="archive-column flex items-center gap-2 py-2 type-small font-medium">
        <SquareMark className="shrink-0" />
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
    <footer className="archive mt-24">
      <div className="archive-column">
        <div className="archive-rule flex flex-wrap gap-x-6 gap-y-2 pb-12 pt-6 type-small text-ink-muted">
          <Link href="/sources" className="archive-link text-ink-muted">
            Sources and licences
          </Link>
          <Link href="/collections" className="archive-link text-ink-muted">
            Collections
          </Link>
          <Link href="/glossary" className="archive-link text-ink-muted">
            Glossary
          </Link>
        </div>
      </div>
    </footer>
  );
}
