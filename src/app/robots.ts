import type { MetadataRoute } from 'next';
import { connection } from 'next/server';
import { getCurrentDatasetVersion, isIndexable } from '@/db/queries/dataset-version';
import { privatePreviewEnabled } from '@/lib/auth/switches';
import { siteOrigin } from '@/lib/site-url';

/**
 * Private preview: disallow everything. Otherwise crawling is allowed (so crawlers can read each page's noindex),
 * curator and API paths excluded, and the sitemap is named only once a release version is current.
 */
export default async function robots(): Promise<MetadataRoute.Robots> {
  await connection();
  if (privatePreviewEnabled()) return { rules: { userAgent: '*', disallow: '/' } };
  const version = await getCurrentDatasetVersion().catch(() => null);
  const rules = { userAgent: '*', allow: '/', disallow: ['/admin', '/api/', '/sign-in'] };
  if (!isIndexable(version, false)) return { rules };
  return { rules, sitemap: `${await siteOrigin()}/sitemap.xml` };
}
