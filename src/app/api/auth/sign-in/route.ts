/** Curator sign-in: verifies a named passphrase and sets the signed session cookie (section 10.1). */
import { NextResponse, type NextRequest } from 'next/server';
import { z } from 'zod';
import { checkCuratorPassphrase } from '@/lib/auth/passphrases';
import { createSessionToken, sessionSecret, SESSION_COOKIE_NAME, SESSION_TTL_SECONDS } from '@/lib/auth/session';
import { throttledSignInResponse } from '@/lib/auth/throttled-response';
import { clientIp, confirmSignIn, reserveSignInAttempt, reserveSignInName } from '@/lib/auth/throttle';

export const dynamic = 'force-dynamic';

const signInForm = z.object({
  name: z.string().trim().min(1).max(100),
  passphrase: z.string().min(1).max(1000),
  next: z.string().optional(),
});

/** Only same-site admin paths are valid return targets (no open redirect). */
function safeNext(next: string | undefined): string {
  return next && /^\/admin(\/[^\s]*)?$/.test(next) && !next.startsWith('//') ? next : '/admin';
}

function redirectTo(request: NextRequest, path: string): NextResponse {
  return NextResponse.redirect(new URL(path, request.url), 303);
}

export async function POST(request: NextRequest) {
  // Count the attempt before any await: concurrent requests cannot all pass a stale check (AGENTS.md §Throttling).
  const attempt = reserveSignInAttempt(clientIp(request.headers));
  if (!attempt) return throttledSignInResponse(request);

  const form = await request.formData().catch(() => null);
  const parsed = signInForm.safeParse(form ? Object.fromEntries(form.entries()) : {});
  const next = safeNext(parsed.success ? parsed.data.next : undefined);
  const failed = () => redirectTo(request, `/sign-in?error=1&next=${encodeURIComponent(next)}`);
  if (parsed.success && !reserveSignInName(attempt, parsed.data.name)) return throttledSignInResponse(request);
  const secret = sessionSecret();
  if (!parsed.success || !secret) return failed();

  const valid = await checkCuratorPassphrase(parsed.data.name, parsed.data.passphrase);
  if (!valid) return failed();

  confirmSignIn(attempt);
  const response = redirectTo(request, next);
  response.cookies.set(SESSION_COOKIE_NAME, await createSessionToken(parsed.data.name, secret), {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    path: '/',
    maxAge: SESSION_TTL_SECONDS,
  });
  return response;
}
