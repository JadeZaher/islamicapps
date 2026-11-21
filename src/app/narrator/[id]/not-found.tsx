import Link from 'next/link';

export default function NarratorNotFound() {
    return (
        <main className="flex min-h-[60vh] items-center justify-center px-6">
            <div className="max-w-md text-center">
                <h1 className="text-2xl font-semibold text-white">Narrator not found</h1>
                <Link href="/" className="mt-6 inline-block text-sm text-white/70 underline underline-offset-4 hover:text-white">
                    Home
                </Link>
            </div>
        </main>
    );
}
