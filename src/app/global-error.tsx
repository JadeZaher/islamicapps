'use client';

/**
 * Last-resort boundary for root layout failures; replaces <html>, so it carries its own minimal styles. Values are the
 * design tokens' (src/app/design-tokens.css), inlined because globals.css may be what failed. DESIGN.md §Error.
 */
const INK = 'light-dark(#17150f, #f1eee6)';
const MUTED = 'light-dark(#57524a, #aca79c)';
const DANGER = 'light-dark(#a32a1d, #ff8b7b)';
const ACCENT = 'light-dark(#0b6a4e, #5dc09a)';
const ON_ACCENT = 'light-dark(#fbfaf7, #0f0f0d)';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" style={{ colorScheme: 'light dark' }}>
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          background: 'light-dark(#f4f1ea, #0f0f0d)',
          color: INK,
          fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
        }}
      >
        <main role="alert" style={{ maxWidth: '42rem', padding: '48px clamp(16px, 4vw, 32px)' }}>
          <div style={{ borderTop: `2px solid ${DANGER}`, paddingTop: 12 }}>
            <p style={{ margin: 0, color: DANGER, fontSize: 12, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Error
            </p>
            <h1 style={{ fontSize: 20, lineHeight: '28px', fontWeight: 600, margin: '12px 0 0' }}>Something went wrong</h1>
            <p style={{ color: MUTED, fontSize: 14, lineHeight: '20px', margin: '8px 0 0' }}>Try again in a moment.</p>
            <button
              type="button"
              onClick={reset}
              style={{
                marginTop: 24,
                background: ACCENT,
                color: ON_ACCENT,
                border: `1px solid ${ACCENT}`,
                borderRadius: 0,
                minHeight: 40,
                padding: '0 16px',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Try again
            </button>
            {error.digest && (
              <p style={{ color: MUTED, fontSize: 12, fontFamily: 'ui-monospace, Consolas, monospace', margin: '16px 0 0' }}>
                Reference {error.digest}
              </p>
            )}
          </div>
        </main>
      </body>
    </html>
  );
}
