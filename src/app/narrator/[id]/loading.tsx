export default function NarratorLoading() {
    return (
        <main className="mx-auto max-w-6xl px-6 py-10" aria-busy="true" aria-live="polite">
            <span className="sr-only">Loading narrator</span>
            <div className="h-9 w-72 animate-pulse rounded bg-white/10" />
            <div className="mt-3 h-6 w-48 animate-pulse rounded bg-white/5" />
            <div className="mt-10 h-10 w-full animate-pulse rounded bg-white/5" />
            <div className="mt-8 grid gap-8 lg:grid-cols-3">
                <div className="h-96 animate-pulse rounded-xl bg-white/5 lg:col-span-2" />
                <div className="h-96 animate-pulse rounded-xl bg-white/5" />
            </div>
        </main>
    );
}
