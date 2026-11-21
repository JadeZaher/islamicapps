export default function ComparativeLoading() {
    return (
        <div className="min-h-screen bg-slate-950 py-12 px-4" role="status" aria-busy="true" aria-label="Loading comparative studies">
            <div className="max-w-7xl mx-auto animate-pulse">
                <div className="h-9 w-80 rounded bg-white/10 mb-8" />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    {[0, 1, 2, 3].map((i) => (
                        <div key={i} className="h-20 rounded-lg bg-white/5" />
                    ))}
                </div>
                <div className="space-y-4">
                    {[0, 1, 2].map((i) => (
                        <div key={i} className="h-48 rounded-lg bg-white/5" />
                    ))}
                </div>
            </div>
        </div>
    );
}
