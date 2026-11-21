export default function AdminComparativeLoading() {
    return (
        <div role="status" aria-busy="true" aria-label="Loading comparative studies" className="">
            <div className="h-9 w-72 bg-sunken mb-8" />
            <div className="h-10 w-full max-w-xl bg-sunken mb-6" />
            <div className="space-y-3">
                {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="h-24 bg-sunken" />
                ))}
            </div>
        </div>
    );
}
