/** Mirrors the narrator page (header, then sections) with flat placeholders: no shimmer or pulse. DESIGN.md §Empty, loading and error states. */
export default function NarratorLoading() {
    return (
        <main className="wrap pb-12" role="status" aria-busy="true">
            <span className="sr-only">Loading narrator</span>
            <div className="page-header">
                <div className="placeholder-bar h-8 w-72" />
                <div data-script="ar" className="placeholder-bar mt-4 h-7 w-56" />
            </div>
            <div className="mt-8 max-w-[var(--measure-wide)] space-y-4">
                {[0, 1, 2, 3].map((row) => (
                    <div key={row} className="placeholder-bar" />
                ))}
            </div>
        </main>
    );
}
