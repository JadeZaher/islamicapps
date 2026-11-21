/** Database health probe for /api/health: `select 1` under a short timeout (section 2.6). */
import 'server-only';
import { sql } from 'drizzle-orm';
import { db } from '@/db/client';

export interface HealthResult {
  ok: boolean;
  latencyMs: number;
}

/** Resolves ok=false (never throws) when the database is unreachable, misconfigured or slower than `timeoutMs`. */
export async function checkDatabase(timeoutMs = 2000): Promise<HealthResult> {
  const started = performance.now();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<false>((resolve) => {
    timer = setTimeout(() => resolve(false), timeoutMs);
  });
  const probe = (async () => {
    await db.execute(sql`select 1`);
    return true;
  })().catch(() => false);
  try {
    const ok = await Promise.race([probe, timeout]);
    return { ok, latencyMs: Math.round(performance.now() - started) };
  } finally {
    clearTimeout(timer);
  }
}
