import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { authEnabled } from '@/lib/auth/switches';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = { title: 'Curator sign-in', robots: { index: false, follow: false } };

interface PageProps {
  searchParams: Promise<{ error?: string; next?: string }>;
}

const FIELD_CLASS = 'h-10 border-slate-700 bg-slate-900 text-slate-100';

/** Inline message per failure; `throttled` is the state after repeated failures (the route may answer 429 directly). */
function errorMessage(error: string | undefined): string | null {
  if (!error) return null;
  if (error === 'throttled') return 'Too many attempts. Wait fifteen minutes, then try again.';
  return 'That name and passphrase did not match.';
}

/** Named-curator sign-in. A plain form posting to the sign-in route, so it works without JavaScript. */
export default async function SignInPage({ searchParams }: PageProps) {
  if (!authEnabled()) notFound();
  const { error, next } = await searchParams;
  const message = errorMessage(error);
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6 py-16 text-slate-100">
      <h1 className="text-2xl font-semibold">Curator sign-in</h1>
      <form method="post" action="/api/auth/sign-in" className="mt-6 space-y-4">
        <input type="hidden" name="next" value={next ?? '/admin'} />
        <div className="space-y-1.5">
          <Label htmlFor="name" className="text-slate-300">
            Name
          </Label>
          <Input
            id="name"
            name="name"
            autoComplete="username"
            required
            aria-invalid={message ? true : undefined}
            aria-describedby={message ? 'sign-in-error' : undefined}
            className={FIELD_CLASS}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="passphrase" className="text-slate-300">
            Passphrase
          </Label>
          <Input
            id="passphrase"
            name="passphrase"
            type="password"
            autoComplete="current-password"
            required
            aria-invalid={message ? true : undefined}
            aria-describedby={message ? 'sign-in-error' : undefined}
            className={FIELD_CLASS}
          />
        </div>
        {message && (
          <p id="sign-in-error" role="alert" className="text-sm text-rose-300">
            {message}
          </p>
        )}
        <Button type="submit" className="h-10 w-full bg-emerald-600 text-white hover:bg-emerald-500">
          Sign in
        </Button>
      </form>
    </main>
  );
}
