/** Mirrors client-page.tsx (page header, text column, facts margin) with flat placeholders: no shimmer or pulse. DESIGN.md §Empty, loading and error states. */
export default function HadithLoading() {
    return (
        <main className="wrap pb-12" role="status" aria-busy="true">
            <span className="sr-only">Loading report</span>
            <div className="page-header !pt-4">
                <div className="placeholder-bar h-8 w-64" />
                <div className="placeholder-bar mt-4 w-80" />
            </div>
            <div className="grid grid-cols-1 gap-x-6 lg:grid-cols-12">
                <div className="mt-8 max-w-[var(--measure-reading)] space-y-4 lg:col-span-8">
                    <div className="placeholder-bar w-24" />
                    {[0, 1, 2].map((row) => (
                        <div key={row} data-script="ar" className="placeholder-bar" />
                    ))}
                    <div className="placeholder-bar mt-6" />
                    <div className="placeholder-bar w-3/4" />
                </div>
                <div className="mt-8 space-y-3 lg:col-span-4 lg:col-start-9">
                    {[0, 1, 2].map((row) => (
                        <div key={row} className="placeholder-bar w-2/3" />
                    ))}
                </div>
            </div>
        </main>
    );
}
