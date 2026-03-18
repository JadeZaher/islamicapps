'use client';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { BookOpen, Users, Calendar, MessageSquare, MapPin, Upload } from 'lucide-react';

export default function AdminPage() {
    const router = useRouter();

    const sections = [
        {
            title: 'Hadith Management',
            description: 'Manage Hadith entries, grading, and transmission chains',
            icon: BookOpen,
            href: '/admin/hadith',
            color: 'bg-blue-500/10 border-blue-500/30 hover:border-blue-500/50',
        },
        {
            title: 'Chain Builder',
            description: 'Create and validate transmission chains for hadiths',
            icon: Users,
            href: '/admin/chain-builder',
            color: 'bg-purple-500/10 border-purple-500/30 hover:border-purple-500/50',
        },
        {
            title: 'Historical Events',
            description: 'Manage and organize Islamic historical events',
            icon: Calendar,
            href: '/admin/events',
            color: 'bg-green-500/10 border-green-500/30 hover:border-green-500/50',
        },
        {
            title: 'Scholarly Commentaries',
            description: 'Add and manage scholarly commentaries on hadiths and narrators',
            icon: MessageSquare,
            href: '/admin/commentaries',
            color: 'bg-orange-500/10 border-orange-500/30 hover:border-orange-500/50',
        },
        {
            title: 'Locations',
            description: 'Manage historical locations and geographic data',
            icon: MapPin,
            href: '/admin/locations',
            color: 'bg-red-500/10 border-red-500/30 hover:border-red-500/50',
        },
    ];

    return (
        <div>
            <div className="mb-12">
                <h1 className="text-4xl font-bold text-white mb-3">Admin Dashboard</h1>
                <p className="text-slate-400">Manage all aspects of the Islamic knowledge base</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {sections.map((section) => {
                    const Icon = section.icon;
                    return (
                        <Card
                            key={section.href}
                            className={`${section.color} border transition-all cursor-pointer p-6`}
                            onClick={() => router.push(section.href)}
                        >
                            <div className="flex items-start gap-4">
                                <div className="p-3 bg-white/5 rounded-lg">
                                    <Icon className="w-6 h-6 text-white" />
                                </div>
                                <div className="flex-1">
                                    <h3 className="text-lg font-semibold text-white mb-1">{section.title}</h3>
                                    <p className="text-sm text-slate-400 mb-4">{section.description}</p>
                                    <Button
                                        variant="outline"
                                        className="border-slate-600 text-slate-300 hover:bg-white/5"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            router.push(section.href);
                                        }}
                                    >
                                        Go to Section →
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    );
                })}
            </div>

            {/* Additional Info Section */}
            <Card className="bg-slate-900/50 border-slate-700 p-8">
                <div className="flex items-start gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-lg">
                        <Upload className="w-6 h-6 text-blue-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-2">Data Import & Management</h3>
                        <p className="text-slate-400 mb-4">
                            For bulk data imports and advanced management, please refer to the data import scripts in
                            the project documentation.
                        </p>
                        <Button
                            variant="outline"
                            className="border-blue-600/30 text-blue-400 hover:bg-blue-500/10"
                        >
                            View Import Guides →
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
}
