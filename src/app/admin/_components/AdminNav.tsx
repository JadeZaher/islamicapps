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
                        className={`flex shrink-0 items-center gap-3  px-3 py-2.5 text-sm font-medium  transition-colors   ${
                            isActive
                                ? 'bg-accent-wash text-accent'
                                : 'text-ink hover:bg-sunken hover:text-ink'
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
