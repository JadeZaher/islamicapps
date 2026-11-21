/** Mirrors the narrator page column so nothing shifts when the record arrives. */
export default function NarratorLoading() {
    return (
        <main className="mx-auto max-w-4xl animate-pulse px-6 pt-10" role="status" aria-busy="true">
            <span className="sr-only">Loading narrator</span>
            <div className="h-9 w-72 rounded bg-slate-800" />
            <div className="mt-3 h-9 w-56 rounded bg-slate-900" />
            <div className="mt-8 h-9 w-full border-b border-slate-800" />
            <div className="mt-8 space-y-3">
                {[0, 1, 2, 3].map((row) => (
                    <div key={row} className="h-5 rounded bg-slate-900" />
                ))}
            </div>
        </main>
    );
}
