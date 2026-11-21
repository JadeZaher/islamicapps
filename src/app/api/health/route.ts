/** Deploy and uptime health check: 200 when the database answers `select 1` within two seconds, else 503. */
import { NextResponse } from 'next/server';
import { checkDatabase } from '@/db/queries/health';

export const dynamic = 'force-dynamic';

export async function GET() {
  const { ok, latencyMs } = await checkDatabase(2000);
  return NextResponse.json(
    { status: ok ? 'ok' : 'unavailable', database: ok ? 'reachable' : 'unreachable', latencyMs },
    { status: ok ? 200 : 503, headers: { 'Cache-Control': 'no-store' } },
  );
}
