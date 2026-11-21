import { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { connection } from 'next/server';
import { authEnabled } from '@/lib/auth/switches';
import Link from 'next/link';
import { Home } from 'lucide-react';
import { AdminNav } from './_components/AdminNav';

export default async function AdminLayout({ children }: { children: ReactNode }) {
    // Resolved at request time (not build time): the admin area does not exist while AUTH_ENABLED is off.
    await connection();
    if (!authEnabled()) notFound();
    return (
        <div className="min-h-screen bg-paper md:flex">
            <aside className="border-b border-rule bg-sunken p-4 md:min-h-screen md:w-64 md:shrink-0 md:border-b-0 md:border-r md:p-6">
                <div className="mb-4 flex items-center justify-between md:mb-8 md:block">
                    <h1 className="border-l-4 border-accent pl-3 text-xl font-bold tracking-tight text-ink">
                        Admin
                    </h1>
                    <Link
                        href="/"
                        className="flex items-center gap-2 text-sm text-ink-muted transition-colors hover:text-accent md:mt-4"
                    >
                        <Home className="h-4 w-4" aria-hidden="true" />
                        Home
                    </Link>
                </div>
                <AdminNav />
            </aside>

            <main className="min-w-0 flex-1 p-4 md:p-10">
                <div className="mx-auto max-w-7xl">{children}</div>
            </main>
        </div>
    );
}
