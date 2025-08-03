import { GlassCard } from '@/components/ui/glass-card';
import { BookOpen, TrendingUp, Clock, Star } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="flex h-screen">
        {/* This will be replaced by the app layout, but for now we show the dashboard directly */}
        <div className="flex-1 p-6">
          <div className="mx-auto max-w-7xl space-y-6">
            {/* Welcome Header */}
            <div className="space-y-2">
              <h1 className="bg-gradient-to-r from-orange-500 to-red-500 bg-clip-text text-3xl font-bold text-transparent">
                Welcome to KireMisu!
              </h1>
              <p className="text-slate-400">
                Your self-hosted manga reader and library management system
              </p>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <GlassCard className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="rounded-full bg-orange-500/20 p-3">
                    <BookOpen className="h-6 w-6 text-orange-500" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Total Series</p>
                    <p className="text-2xl font-bold">0</p>
                  </div>
                </div>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="rounded-full bg-blue-500/20 p-3">
                    <TrendingUp className="h-6 w-6 text-blue-500" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Chapters Read</p>
                    <p className="text-2xl font-bold">0</p>
                  </div>
                </div>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="rounded-full bg-green-500/20 p-3">
                    <Clock className="h-6 w-6 text-green-500" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Reading Time</p>
                    <p className="text-2xl font-bold">0h</p>
                  </div>
                </div>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="rounded-full bg-purple-500/20 p-3">
                    <Star className="h-6 w-6 text-purple-500" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Favorites</p>
                    <p className="text-2xl font-bold">0</p>
                  </div>
                </div>
              </GlassCard>
            </div>

            {/* Setup Instructions */}
            <GlassCard className="p-8">
              <h2 className="mb-4 text-xl font-semibold">Getting Started</h2>
              <div className="space-y-4">
                <p className="text-slate-300">
                  Welcome to KireMisu! To get started with your manga library:
                </p>
                <ol className="list-inside list-decimal space-y-2 text-slate-400">
                  <li>Navigate to Settings to configure your library paths</li>
                  <li>Scan your existing manga collection</li>
                  <li>Discover new series from MangaDx</li>
                  <li>Start reading and organizing your collection</li>
                </ol>
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  );
}
