'use client';

/** Last-resort boundary for root layout failures; replaces <html>, so it carries its own minimal styles. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" className="dark">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#020617',
          color: '#f1f5f9',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <main role="alert" style={{ maxWidth: 420, padding: 24, textAlign: 'center' }}>
          <h1 style={{ fontSize: 24, fontWeight: 600, margin: 0 }}>Something went wrong</h1>
          <p style={{ color: '#94a3b8', fontSize: 14 }}>Try again in a moment.</p>
          <button
            type="button"
            onClick={reset}
            style={{
              background: '#059669',
              color: '#fff',
              border: 0,
              borderRadius: 6,
              padding: '8px 16px',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
          {error.digest && (
            <p style={{ color: '#475569', fontSize: 12 }}>Reference {error.digest}</p>
          )}
        </main>
      </body>
    </html>
  );
}
