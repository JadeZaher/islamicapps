import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Book, GitBranch, Award, Database, Sparkles } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white pattern-islamic relative overflow-hidden">
      {/* Subtle Overlay Gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-950/50 to-slate-950 pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-6 py-20 animate-fade-in">
        {/* Hero Section */}
        <div className="text-center mb-20 animate-slide-up">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full mb-6">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span className="text-sm font-medium text-emerald-300">Scholar-Backed Grading System</span>
          </div>

          <h1 className="text-6xl md:text-7xl font-bold mb-6 tracking-tight">
            <span className="bg-gradient-to-r from-amber-400 via-emerald-400 to-amber-400 bg-clip-text text-transparent">
              Hadith Graph
            </span>
            <br />
            <span className="text-slate-100">Explorer</span>
          </h1>

          <p className="text-xl md:text-2xl text-slate-300 mb-10 max-w-3xl mx-auto leading-relaxed font-light">
            Visualize <strong className="font-semibold text-white">Isnad transmission chains</strong> with scholar-backed grading.
            Explore authentic Islamic scholarship through interactive graph visualization.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/admin">
              <Button
                size="lg"
                className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg hover:shadow-emerald-500/25 transition-all duration-300 hover:scale-105"
              >
                <Database className="w-5 h-5 mr-2" />
                Admin Dashboard
              </Button>
            </Link>
            <Button
              size="lg"
              variant="outline"
              className="border-slate-600 hover:border-amber-400/50 text-slate-300 hover:text-amber-400 transition-all duration-300"
            >
              <Book className="w-5 h-5 mr-2" />
              Documentation
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
          <Card className="group relative bg-slate-900/50 border-slate-700 hover:border-emerald-500/50 p-8 transition-all duration-300 hover:shadow-xl hover:shadow-emerald-500/10 hover:scale-105 cursor-pointer overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
                <GitBranch className="w-8 h-8 text-emerald-400" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-slate-100">Interactive Graphs</h3>
              <p className="text-slate-400 leading-relaxed">
                Visualize complex transmission chains with force-directed layouts. Click nodes to explore narrator biographies and connections.
              </p>
            </div>
          </Card>

          <Card className="group relative bg-slate-900/50 border-slate-700 hover:border-amber-400/50 p-8 transition-all duration-300 hover:shadow-xl hover:shadow-amber-400/10 hover:scale-105 cursor-pointer overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-400/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-amber-400/10 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
                <Award className="w-8 h-8 text-amber-400" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-slate-100">Scholar Verdicts</h3>
              <p className="text-slate-400 leading-relaxed">
                Manual scholar verdicts take priority over auto-calculated grades, preserving traditional Islamic scholarship methodology.
              </p>
            </div>
          </Card>

          <Card className="group relative bg-slate-900/50 border-slate-700 hover:border-blue-400/50 p-8 transition-all duration-300 hover:shadow-xl hover:shadow-blue-400/10 hover:scale-105 cursor-pointer overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-blue-400/10 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
                <Book className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-slate-100">Matn Variations</h3>
              <p className="text-slate-400 leading-relaxed">
                Compare different text variations from Sahih Bukhari, Muslim, and other authentic hadith collections.
              </p>
            </div>
          </Card>
        </div>

        {/* Quick Start Section */}
        <Card className="bg-slate-900/60 backdrop-blur-sm border-slate-700 p-10 border-islamic shadow-2xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-slate-100">Quick Start Guide</h2>
          </div>

          <ol className="space-y-6 text-slate-300">
            <li className="flex items-start gap-4 group">
              <span className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-full flex items-center justify-center font-bold text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                1
              </span>
              <div className="flex-1">
                <p className="font-semibold text-lg text-slate-100 mb-2">Initialize Database</p>
                <code className="text-sm bg-slate-800/80 border border-slate-700 px-4 py-2 rounded-lg inline-block font-mono">
                  npm run db:init
                </code>
                <p className="text-sm text-slate-400 mt-2">Sets up Neo4j schema and seeds sample data</p>
              </div>
            </li>

            <li className="flex items-start gap-4 group">
              <span className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-full flex items-center justify-center font-bold text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                2
              </span>
              <div className="flex-1">
                <p className="font-semibold text-lg text-slate-100 mb-2">Visit Admin Dashboard</p>
                <p className="text-slate-300">
                  Navigate to <code className="bg-slate-800/80 border border-slate-700 px-3 py-1 rounded font-mono text-emerald-400">/admin</code> to manage Hadiths, narrators, and scholars
                </p>
              </div>
            </li>

            <li className="flex items-start gap-4 group">
              <span className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-full flex items-center justify-center font-bold text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                3
              </span>
              <div className="flex-1">
                <p className="font-semibold text-lg text-slate-100 mb-2">Explore Sample Data</p>
                <p className="text-slate-300">
                  Database seeds with <strong className="text-amber-400">Hadith of Jibril</strong> and multiple transmission chains for demonstration
                </p>
              </div>
            </li>
          </ol>
        </Card>

        {/* Footer Note */}
        <div className="text-center mt-16 pb-8">
          <p className="text-slate-500 text-sm">
            Built with Next.js • Neo4j • React Force Graph
          </p>
        </div>
      </div>
    </div>
  );
}
