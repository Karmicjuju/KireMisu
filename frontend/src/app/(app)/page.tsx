'use client';

import { GlassCard } from '@/components/ui/glass-card';
import { ProgressBar } from '@/components/ui/progress-bar';
import { Button } from '@/components/ui/button';
import { ChapterList } from '@/components/library/chapter-list';
import { BookOpen, TrendingUp, Clock, Star, Loader2, AlertTriangle } from 'lucide-react';
import {
  dashboardApi,
  seriesApi,
  DashboardStats,
  SeriesResponse,
  ChapterResponse,
} from '@/lib/api';
import useSWR from 'swr';
import Link from 'next/link';
// import { formatDistanceToNow } from 'date-fns'; // Temporarily disabled to prevent build errors

export default function Dashboard() {
  const {
    data: stats,
    error: statsError,
    isLoading: statsLoading,
  } = useSWR<DashboardStats>('/api/dashboard/stats', dashboardApi.getStats, {
    refreshInterval: 30000, // Refresh every 30 seconds
    errorRetryCount: 3,
  });

  const {
    data: recentSeries,
    error: seriesError,
    isLoading: seriesLoading,
  } = useSWR<SeriesResponse[]>('/api/series?limit=6', () => seriesApi.getSeriesList({ limit: 6 }));

  const formatReadingTime = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  };
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
              <div className="flex items-center gap-2">
                {statsLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : statsError ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <p className="text-2xl font-bold">{stats?.total_series ?? 0}</p>
                )}
              </div>
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
              <div className="flex items-center gap-2">
                {statsLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : statsError ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <>
                    <p className="text-2xl font-bold">{stats?.chapters_read ?? 0}</p>
                    {stats && stats.total_chapters > 0 && (
                      <span className="text-sm text-slate-400">/ {stats.total_chapters}</span>
                    )}
                  </>
                )}
              </div>
              {stats && stats.total_chapters > 0 && (
                <div className="mt-2">
                  <ProgressBar
                    value={stats.chapters_read}
                    max={stats.total_chapters}
                    size="sm"
                    variant="subtle"
                    colorScheme="info"
                  />
                </div>
              )}
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
              <div className="flex items-center gap-2">
                {statsLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : statsError ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <p className="text-2xl font-bold">
                    {formatReadingTime(stats?.reading_time_hours ?? 0)}
                  </p>
                )}
              </div>
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
              <div className="flex items-center gap-2">
                {statsLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                ) : statsError ? (
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                ) : (
                  <p className="text-2xl font-bold">{stats?.favorites_count ?? 0}</p>
                )}
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Continue Reading Section */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Continue Reading</h2>
          {recentSeries && recentSeries.length > 0 && (
            <Button asChild variant="outline" size="sm">
              <Link href="/library">View All Series</Link>
            </Button>
          )}
        </div>

        {seriesLoading ? (
          <GlassCard className="p-8 text-center">
            <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-slate-400" />
            <p className="text-sm text-slate-400">Loading your library...</p>
          </GlassCard>
        ) : seriesError ? (
          <GlassCard className="p-8 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-red-500" />
            <h3 className="mb-2 text-lg font-medium text-slate-300">Failed to load library</h3>
            <p className="text-sm text-slate-500">
              Unable to fetch your manga collection. Please try again later.
            </p>
          </GlassCard>
        ) : !recentSeries || recentSeries.length === 0 ? (
          <GlassCard className="p-8 text-center">
            <BookOpen className="mx-auto mb-4 h-12 w-12 text-slate-500" />
            <h3 className="mb-2 text-lg font-medium text-slate-300">
              No manga in your library yet
            </h3>
            <p className="mb-4 text-sm text-slate-500">
              Add some library paths in Settings to start building your collection
            </p>
            <Button asChild>
              <Link href="/settings">Go to Settings</Link>
            </Button>
          </GlassCard>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {recentSeries.map((series) => (
              <GlassCard key={series.id} className="overflow-hidden transition-all hover:scale-105">
                <div className="relative flex aspect-[3/4] items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
                  <div className="text-white/40">
                    <BookOpen className="h-12 w-12" />
                  </div>

                  {series.total_chapters > 0 && (
                    <div className="absolute right-2 top-2">
                      <div className="rounded-full bg-black/50 px-2 py-1 text-xs text-white">
                        {Math.round((series.read_chapters / series.total_chapters) * 100)}%
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-3 p-4">
                  <div>
                    <h3 className="line-clamp-2 font-semibold text-white">
                      {series.title_primary}
                    </h3>
                    {series.author && (
                      <p className="line-clamp-1 text-sm text-white/70">by {series.author}</p>
                    )}
                  </div>

                  {series.total_chapters > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm text-white/60">
                        <span>
                          {series.read_chapters} / {series.total_chapters} chapters
                        </span>
                      </div>
                      <ProgressBar
                        value={series.read_chapters}
                        max={series.total_chapters}
                        size="sm"
                        colorScheme="primary"
                      />
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <Button asChild size="sm" className="flex-1">
                      <Link href={`/library/series/${series.id}`}>View Details</Link>
                    </Button>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      {stats && stats.recent_activity && stats.recent_activity.length > 0 && (
        <div>
          <h2 className="mb-4 text-xl font-semibold">Recent Activity</h2>
          <GlassCard className="p-4">
            <div className="space-y-3">
              {stats.recent_activity.slice(0, 5).map((activity) => (
                <div key={activity.id} className="flex items-center gap-3 text-sm">
                  <div className="rounded-full bg-orange-500/20 p-2">
                    {activity.type === 'chapter_read' && (
                      <BookOpen className="h-4 w-4 text-orange-500" />
                    )}
                    {activity.type === 'series_added' && (
                      <Star className="h-4 w-4 text-purple-500" />
                    )}
                    {activity.type === 'progress_updated' && (
                      <TrendingUp className="h-4 w-4 text-blue-500" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-white">{activity.title}</p>
                    {activity.subtitle && (
                      <p className="truncate text-xs text-white/60">{activity.subtitle}</p>
                    )}
                  </div>

                  <div className="text-xs text-white/40">
                    {new Date(activity.timestamp).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Button asChild variant="ghost" className="h-auto p-6">
            <Link href="/library">
              <div className="text-center">
                <BookOpen className="mx-auto mb-3 h-8 w-8 text-orange-500" />
                <h3 className="font-medium">Browse Library</h3>
                <p className="mt-1 text-sm text-slate-400">
                  {stats
                    ? `${stats.total_series} series available`
                    : 'Explore your manga collection'}
                </p>
              </div>
            </Link>
          </Button>

          <Button asChild variant="ghost" className="h-auto p-6">
            <Link href="/downloads">
              <div className="text-center">
                <TrendingUp className="mx-auto mb-3 h-8 w-8 text-blue-500" />
                <h3 className="font-medium">Discover New</h3>
                <p className="mt-1 text-sm text-slate-400">Find trending manga on MangaDx</p>
              </div>
            </Link>
          </Button>

          <Button asChild variant="ghost" className="h-auto p-6">
            <Link href="/settings">
              <div className="text-center">
                <Clock className="mx-auto mb-3 h-8 w-8 text-green-500" />
                <h3 className="font-medium">Manage Library</h3>
                <p className="mt-1 text-sm text-slate-400">Configure paths and scanning</p>
              </div>
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
