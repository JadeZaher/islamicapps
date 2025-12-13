'use client';

import { Component, ReactNode } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryProps {
    children: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

export class HadithErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: any) {
        console.error('Hadith page error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">
                    <Card className="bg-slate-900/50 border-slate-800 p-8 max-w-md">
                        <h2 className="text-2xl font-bold text-red-400 mb-4">Something went wrong</h2>
                        <p className="text-slate-300 mb-6">
                            We encountered an error while loading this hadith. This may be due to missing data or a connection issue.
                        </p>
                        {this.state.error && (
                            <div className="bg-slate-800 rounded p-4 mb-6">
                                <p className="text-sm text-slate-400 font-mono">
                                    {this.state.error.message}
                                </p>
                            </div>
                        )}
                        <div className="flex gap-4">
                            <Button
                                onClick={() => window.location.reload()}
                                className="bg-emerald-600 hover:bg-emerald-700"
                            >
                                Retry
                            </Button>
                            <Button
                                onClick={() => window.location.href = '/admin/hadith'}
                                variant="outline"
                                className="border-slate-600"
                            >
                                Back to Hadiths
                            </Button>
                        </div>
                    </Card>
                </div>
            );
        }

        return this.props.children;
    }
}
