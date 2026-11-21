import type { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { ReportFooter } from '@/components/archive/ReportFooter';
import { ReportTrail } from '@/components/archive/ReportTrail';
import { loadHadith } from './data';

/**
 * Decides "not found" outside loading.tsx's Suspense boundary, before anything streams, so an unknown or
 * unpublished hadith answers HTTP 404 instead of 200. The read is cached and reused by the page.
 * Mounts the report's place in its work: trail above; previous/next, sources, citation and version below.
 */
export default async function HadithLayout({ children, params }: { children: ReactNode; params: Promise<{ id: string }> }) {
    const rawId = (await params).id;
    if (!(await loadHadith(rawId))) notFound();
    const id = decodeURIComponent(rawId);
    return (
        <>
            <ReportTrail id={id} />
            {children}
            <ReportFooter id={id} />
        </>
    );
}
