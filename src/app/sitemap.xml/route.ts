/** Sitemap, served only once a release dataset version is current (404 before that, and under private preview). */
import { getCurrentDatasetVersion, isIndexable } from '@/db/queries/dataset-version';
import { listWorksByTradition } from '@/db/queries/browse';
import { PUBLIC_VISIBILITY } from '@/db/queries/visibility';
import { privatePreviewEnabled } from '@/lib/auth/switches';
import { siteOrigin } from '@/lib/site-url';

export const dynamic = 'force-dynamic';

function escapeXml(value: string): string {
  return value.replace(/[<>&'"]/g, (character) => `&#${character.charCodeAt(0)};`);
}

export async function GET() {
  const version = await getCurrentDatasetVersion().catch(() => null);
  if (!isIndexable(version, privatePreviewEnabled())) return new Response('Not found.', { status: 404 });
  const origin = await siteOrigin();
  const traditions = await listWorksByTradition(PUBLIC_VISIBILITY);
  const paths = ['/', '/collections', '/sources', '/glossary', ...traditions.flatMap((group) => group.works.map((work) => `/collections/${encodeURIComponent(work.slug)}`))];
  const body =
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    paths.map((path) => `  <url><loc>${escapeXml(origin + path)}</loc></url>`).join('\n') +
    '\n</urlset>\n';
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
