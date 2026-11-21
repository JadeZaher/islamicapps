import Link from 'next/link';

export default function HadithNotFound() {
    return (
        <main className="min-h-screen bg-slate-950 flex items-center justify-center p-8 text-white">
            <div className="max-w-md w-full text-center space-y-5">
                <h1 className="text-2xl font-bold">Hadith not found</h1>
                <Link href="/" className="inline-block text-sm text-cyan-300 hover:text-cyan-200 underline-offset-4 hover:underline">
                    Back to home
                </Link>
            </div>
        </main>
    );
}
