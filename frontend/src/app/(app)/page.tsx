import { GlassCard } from '@/components/ui/glass-card';
import { BookOpen, TrendingUp, Clock, Star } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="space-y-2">
        <h1 className="bg-gradient-to-r from-orange-500 to-red-500 bg-clip-text text-3xl font-bold text-transparent">
          Welcome back!
        </h1>
        <p className="text-slate-400">Continue your manga journey where you left off</p>
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

      {/* Continue Reading Section */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Continue Reading</h2>
        <GlassCard className="p-8 text-center">
          <BookOpen className="mx-auto mb-4 h-12 w-12 text-slate-500" />
          <h3 className="mb-2 text-lg font-medium text-slate-300">No manga in your library yet</h3>
          <p className="text-sm text-slate-500">
            Add some library paths in Settings to start building your collection
          </p>
        </GlassCard>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <GlassCard className="cursor-pointer p-6 transition-colors hover:bg-white/5">
            <div className="text-center">
              <BookOpen className="mx-auto mb-3 h-8 w-8 text-orange-500" />
              <h3 className="font-medium">Browse Library</h3>
              <p className="mt-1 text-sm text-slate-400">Explore your manga collection</p>
            </div>
          </GlassCard>

          <GlassCard className="cursor-pointer p-6 transition-colors hover:bg-white/5">
            <div className="text-center">
              <TrendingUp className="mx-auto mb-3 h-8 w-8 text-blue-500" />
              <h3 className="font-medium">Discover New</h3>
              <p className="mt-1 text-sm text-slate-400">Find trending manga on MangaDx</p>
            </div>
          </GlassCard>

          <GlassCard className="cursor-pointer p-6 transition-colors hover:bg-white/5">
            <div className="text-center">
              <Clock className="mx-auto mb-3 h-8 w-8 text-green-500" />
              <h3 className="font-medium">Reading Lists</h3>
              <p className="mt-1 text-sm text-slate-400">Organize your collection</p>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
