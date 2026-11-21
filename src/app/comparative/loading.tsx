/** Mirrors the comparative page header and stats row so nothing shifts on load. */
export default function ComparativeLoading() {
    return (
        <main className="px-6 py-10" role="status" aria-busy="true">
            <span className="sr-only">Loading comparative studies</span>
            <div className="mx-auto max-w-6xl animate-pulse">
                <div className="mb-8 h-9 w-64 rounded bg-slate-800" />
                <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
                    {[0, 1, 2, 3].map((i) => (
                        <div key={i} className="h-20 rounded-lg bg-slate-900" />
                    ))}
                </div>
                <div className="space-y-4">
                    {[0, 1, 2].map((i) => (
                        <div key={i} className="h-40 rounded-lg bg-slate-900" />
                    ))}
                </div>
            </div>
        </main>
    );
}
