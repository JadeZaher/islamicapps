export default function AdminLoading() {
    return (
        <div role="status" aria-busy="true" aria-label="Loading" className="animate-pulse space-y-4">
            <div className="h-9 w-56 rounded-md bg-slate-800" />
            <div className="h-11 w-full max-w-md rounded-md bg-slate-800/70" />
            {Array.from({ length: 6 }, (_, index) => (
                <div key={index} className="h-20 rounded-lg border border-slate-800 bg-slate-900" />
            ))}
            <span className="sr-only">Loading</span>
        </div>
    );
}
