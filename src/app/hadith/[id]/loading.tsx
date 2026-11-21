/** Mirrors the reading column of client-page.tsx so nothing shifts when the hadith arrives. */
export default function HadithLoading() {
    return (
        <main className="mx-auto max-w-3xl animate-pulse px-6 pt-10" role="status" aria-busy="true">
            <span className="sr-only">Loading hadith</span>
            <div className="border-b border-slate-800 pb-6">
                <div className="h-5 w-16 rounded bg-slate-800" />
                <div className="mt-4 h-8 w-56 rounded bg-slate-800" />
                <div className="mt-3 h-5 w-72 rounded bg-slate-900" />
            </div>
            <div className="space-y-3 border-b border-slate-800 py-8">
                {[0, 1, 2, 3].map((row) => (
                    <div key={row} className="h-7 rounded bg-slate-900" />
                ))}
            </div>
            <div className="space-y-3 py-8">
                {[0, 1, 2].map((row) => (
                    <div key={row} className="h-8 rounded bg-slate-900" />
                ))}
            </div>
        </main>
    );
}
