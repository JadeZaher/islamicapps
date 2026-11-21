export default function Loading() {
  return (
    <div role="status" aria-label="Loading" className="mx-auto max-w-4xl animate-pulse space-y-4 px-6 py-10">
      <div className="h-8 w-48 rounded-md bg-slate-800" />
      <div className="h-10 w-full rounded-md bg-slate-900" />
      <div className="space-y-3 pt-4">
        {[0, 1, 2, 3].map((row) => (
          <div key={row} className="h-16 rounded-md bg-slate-900" />
        ))}
      </div>
    </div>
  );
}
