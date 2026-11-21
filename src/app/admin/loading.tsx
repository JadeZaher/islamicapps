export default function AdminLoading() {
    return (
        <div role="status" aria-busy="true" aria-label="Loading" className="space-y-4">
            <div className="h-9 w-56 bg-sunken" />
            <div className="h-11 w-full max-w-md bg-sunken" />
            {Array.from({ length: 6 }, (_, index) => (
                <div key={index} className="h-20 bg-sunken" />
            ))}
            <span className="sr-only">Loading</span>
        </div>
    );
}
