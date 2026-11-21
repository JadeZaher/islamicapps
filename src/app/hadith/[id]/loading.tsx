export default function HadithLoading() {
    return (
        <div className="min-h-screen bg-slate-950" role="status" aria-busy="true" aria-label="Loading hadith">
            <div className="border-b border-slate-800/60 px-6 py-4">
                <div className="max-w-7xl mx-auto h-8 w-64 rounded bg-slate-800/60 animate-pulse" />
            </div>
            <div className="max-w-2xl mx-auto px-4 py-8 space-y-3">
                <div className="h-20 rounded-lg bg-slate-900/60 animate-pulse" />
                <div className="h-16 rounded-md bg-slate-900/40 animate-pulse" />
                <div className="h-16 rounded-md bg-slate-900/40 animate-pulse" />
                <div className="h-16 rounded-md bg-slate-900/40 animate-pulse" />
            </div>
            <span className="sr-only">Loading hadith</span>
        </div>
    );
}
