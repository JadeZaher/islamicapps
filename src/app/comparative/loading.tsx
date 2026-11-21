/** Mirrors the comparative page header and lists with flat placeholders: no shimmer or pulse. */
export default function ComparativeLoading() {
    return (
        <main className="wrap pb-12" role="status" aria-busy="true">
            <span className="sr-only">Loading comparative studies</span>
            <div className="page-header">
                <div className="placeholder-bar h-8 w-64" />
            </div>
            <div className="mt-8 space-y-4">
                {[0, 1, 2, 3, 4].map((i) => (
                    <div key={i} className="placeholder-bar" />
                ))}
            </div>
        </main>
    );
}
