import type { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { loadHadith } from './data';

/**
 * Decides "not found" outside loading.tsx's Suspense boundary, before anything streams, so an unknown or
 * unpublished hadith answers HTTP 404 instead of 200. The read is cached and reused by the page.
 */
export default async function HadithLayout({ children, params }: { children: ReactNode; params: Promise<{ id: string }> }) {
    if (!(await loadHadith((await params).id))) notFound();
    return children;
}
