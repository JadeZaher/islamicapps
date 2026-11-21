/** The site's public origin for server components: `SITE_URL` in production, never request headers. See site-origin.ts. */
import 'server-only';
import { headers } from 'next/headers';
import { configuredSiteOrigin, siteOriginFor } from './site-origin';

export async function siteOrigin(): Promise<string> {
  const configured = configuredSiteOrigin();
  if (configured || process.env.NODE_ENV === 'production') return siteOriginFor(null, null);
  // Development and tests only: the request's host, accepted by siteOriginFor only when it is a loopback host.
  const store = await headers();
  return siteOriginFor(store.get('host'), store.get('x-forwarded-proto'));
}
