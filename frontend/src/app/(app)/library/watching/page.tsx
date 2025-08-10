'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WatchedSeriesList } from '@/components/library/watched-series-list';
import { 
  Bell, 
  BellRing, 
  BookOpen, 
  Loader2,
  AlertCircle 
} from 'lucide-react';
import { seriesApi, type SeriesResponse, type WatchingResponse } from '@/lib/api';

export default function WatchingPage() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Fetch all series and filter for watched ones
  const {
    data: seriesData,
    error,
    isLoading,
    mutate
  } = useSWR<SeriesResponse[]>(
    'all-series-for-watching',
    () => seriesApi.getSeriesList(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  );

  // Filter and transform to WatchingResponse format
  const watchedSeries: WatchingResponse[] | undefined = seriesData
    ?.filter(series => series.watching_enabled)
    ?.map(series => ({
      series_id: series.id,
      series_title: series.title_primary || 'Unknown Title',
      watching_enabled: series.watching_enabled,
      last_watched_check: series.last_watched_check,
      message: `Watching ${series.title_primary || 'series'}`
    }));

  const handleRefresh = () => {
    mutate();
  };

  const stats = watchedSeries ? {
    total: watchedSeries.length,
    recentlyChecked: watchedSeries.filter(s => 
      s.last_watched_check && 
      new Date(s.last_watched_check) > new Date(Date.now() - 24 * 60 * 60 * 1000)
    ).length,
  } : { total: 0, recentlyChecked: 0 };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <BellRing className="h-8 w-8 text-primary" />
              <h1 className="text-3xl font-bold">Watching</h1>
            </div>
            <p className="text-muted-foreground">
              Manage your watched series and get notified about new chapters
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button onClick={handleRefresh} variant="outline" size="sm">
              Refresh
            </Button>
          </div>
        </div>

        {/* Stats */}
        {watchedSeries && (
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              <span>{stats.total} series watched</span>
            </div>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{stats.recentlyChecked} checked today</span>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading your watched series...</p>
          </div>
        </div>
      ) : error ? (
        <GlassCard className="p-12 text-center">
          <AlertCircle className="mx-auto mb-6 h-16 w-16 text-destructive" />
          <h3 className="mb-4 text-xl font-semibold">Error loading watched series</h3>
          <p className="mx-auto mb-6 max-w-md text-muted-foreground">
            Failed to load your watched series. Please check your connection and try again.
          </p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </GlassCard>
      ) : !watchedSeries || watchedSeries.length === 0 ? (
        /* Empty State */
        <GlassCard className="p-12 text-center">
          <Bell className="mx-auto mb-6 h-16 w-16 text-muted-foreground" />
          <h3 className="mb-4 text-xl font-semibold">No series being watched</h3>
          <p className="mx-auto mb-6 max-w-md text-muted-foreground">
            Start watching series from your library to get notifications about new chapters. 
            Click the watch button on any series card to add it to your watch list.
          </p>
          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
              <a href="/library">
                <BookOpen className="mr-2 h-4 w-4" />
                Browse Library
              </a>
            </Button>
          </div>
        </GlassCard>
      ) : (
        /* Watched Series List */
        <WatchedSeriesList 
          watchedSeries={watchedSeries} 
          viewMode={viewMode}
          onSeriesRemoved={handleRefresh}
        />
      )}
    </div>
  );
}