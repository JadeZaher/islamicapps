import { ReactNode } from 'react';
import Link from 'next/link';
import { Book, Users, Award, GitBranch, Home } from 'lucide-react';

export default function AdminLayout({ children }: { children: ReactNode }) {
    const navItems = [
        { href: '/admin/hadith', label: 'Hadith Manager', icon: Book },
        { href: '/admin/narrator', label: 'Narrators', icon: Users },
        { href: '/admin/scholar', label: 'Scholars', icon: Award },
        { href: '/admin/chain', label: 'Chain Builder', icon: GitBranch },
    ];

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 pattern-islamic">
            <div className="flex">
                {/* Refined Sidebar */}
                <aside className="w-72 min-h-screen bg-slate-900/80 backdrop-blur-sm border-r border-slate-800/50 p-6 border-islamic">
                    {/* Header */}
                    <div className="mb-10">
                        <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-emerald-400 transition-colors mb-6 group">
                            <Home className="w-4 h-4 group-hover:scale-110 transition-transform" />
                            <span className="text-sm">← Back to Home</span>
                        </Link>
                        <div className="border-l-4 border-emerald-500 pl-4">
                            <h1 className="text-2xl font-bold text-white tracking-tight">Admin Panel</h1>
                            <p className="text-sm text-slate-400 mt-1 font-light">Database Management</p>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="space-y-2">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className="group flex items-center gap-3 px-4 py-3.5 text-slate-300 hover:text-white hover:bg-slate-800/60 rounded-lg transition-all duration-300 relative overflow-hidden"
                                >
                                    {/* Hover gradient overlay */}
                                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                                    {/* Icon with animation */}
                                    <div className="relative w-10 h-10 flex items-center justify-center rounded-lg bg-slate-800 group-hover:bg-emerald-500/20 transition-all duration-300 group-hover:scale-110">
                                        <Icon className="w-5 h-5 group-hover:text-emerald-400 transition-colors duration-300" />
                                    </div>

                                    {/* Label */}
                                    <span className="relative font-medium">{item.label}</span>

                                    {/* Active indicator */}
                                    <div className="absolute left-0 w-1 h-8 bg-emerald-500 rounded-r-full opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Footer Stats */}
                    <div className="mt-auto pt-8 border-t border-slate-800">
                        <div className="text-xs text-slate-500 space-y-1">
                            <p>Neo4j Connected ●</p>
                            <p className="text-emerald-400">System: Online</p>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 p-10 overflow-y-auto">
                    <div className="max-w-7xl mx-auto animate-fade-in">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
