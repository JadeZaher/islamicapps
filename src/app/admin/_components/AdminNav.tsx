'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Book, Users, Calendar, MessageSquare, MapPin, Globe } from 'lucide-react';

const NAV_ITEMS = [
    { href: '/admin/hadith', label: 'Hadiths', icon: Book },
    { href: '/admin/narrators', label: 'Narrators', icon: Users },
    { href: '/admin/events', label: 'Events', icon: Calendar },
    { href: '/admin/commentaries', label: 'Commentaries', icon: MessageSquare },
    { href: '/admin/locations', label: 'Locations', icon: MapPin },
    { href: '/admin/comparative', label: 'Comparative', icon: Globe },
];

/** Admin section links; vertical sidebar from md up, horizontal scroller below. */
export function AdminNav() {
    const pathname = usePathname();

    return (
        <nav aria-label="Admin" className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href || pathname.startsWith(`${href}/`);
                return (
                    <Link
                        key={href}
                        href={href}
                        aria-current={isActive ? 'page' : undefined}
                        className={`flex shrink-0 items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                            isActive
                                ? 'bg-emerald-500/15 text-emerald-300'
                                : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                        }`}
                    >
                        <Icon className="h-4 w-4" aria-hidden="true" />
                        {label}
                    </Link>
                );
            })}
        </nav>
    );
}
