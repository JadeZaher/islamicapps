/** The site's public origin: SITE_URL when set (deployments), else the request's host. */
import 'server-only';
import { headers } from 'next/headers';

export async function siteOrigin(): Promise<string> {
  const configured = process.env.SITE_URL?.trim().replace(/\/+$/, '');
  if (configured) return configured;
  const store = await headers();
  const host = store.get('x-forwarded-host') ?? store.get('host') ?? 'localhost';
  const protocol = store.get('x-forwarded-proto') ?? (host.startsWith('localhost') || host.startsWith('127.') ? 'http' : 'https');
  return `${protocol}://${host}`;
}
