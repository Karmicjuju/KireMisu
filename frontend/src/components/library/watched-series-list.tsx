'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WatchToggle } from './watch-toggle';
import { cn } from '@/lib/utils';
import { WatchingResponse } from '@/lib/api';
import { 
  Book, 
  BookOpen, 
  Play, 
  Clock, 
  Calendar,
  Grid3X3,
  List,
  Filter,
  Check
} from 'lucide-react';

export interface WatchedSeriesListProps {
  watchedSeries: WatchingResponse[];
  viewMode: 'grid' | 'list';
  onSeriesRemoved: () => void;
  className?: string;
}

interface WatchedSeriesCardProps {
  series: WatchingResponse;
  viewMode: 'grid' | 'list';
  onSeriesRemoved: () => void;
}

function WatchedSeriesCard({ series, viewMode, onSeriesRemoved }: WatchedSeriesCardProps) {
  const lastChecked = series.last_watched_check 
    ? new Date(series.last_watched_check).toLocaleDateString()
    : 'Never';

  if (viewMode === 'list') {
    return (
      <GlassCard className="overflow-hidden transition-all hover:bg-accent/5" data-testid="watched-series-card">
        <div className="flex items-center gap-4 p-4">
          {/* Compact Cover */}
          <div className="relative flex h-16 w-12 items-center justify-center bg-gradient-to-br from-muted to-muted/80 rounded-sm flex-shrink-0">
            <Book className="h-6 w-6 text-muted-foreground/60" />
            {/* Watching indicator */}
            <div className="absolute -top-1 -right-1">
              <Badge variant="default" className="text-xs h-4 w-4 p-0 rounded-full bg-primary">
                <span className="sr-only">Watching</span>
              </Badge>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="font-medium text-sm line-clamp-1">{series.series_title}</h3>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>Last checked: {lastChecked}</span>
                </div>
              </div>
              
              {/* Status badge */}
              <div className="flex-shrink-0">
                <Badge variant="secondary" className="text-xs h-5">
                  <Check className="mr-1 h-2.5 w-2.5" />
                  Watching
                </Badge>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <WatchToggle 
              seriesId={series.series_id}
              isWatching={series.watching_enabled}
              variant="button"
              size="sm"
              className="text-xs"
            />
            <Button asChild size="sm" variant="outline">
              <Link href={`/library/series/${series.series_id}`}>View Series</Link>
            </Button>
          </div>
        </div>
      </GlassCard>
    );
  }

  // Grid view
  return (
    <GlassCard className="overflow-hidden transition-all hover:scale-105" data-testid="watched-series-card">
      <div className="relative flex aspect-[2/3] items-center justify-center bg-gradient-to-br from-muted to-muted/80">
        {/* Placeholder for cover image */}
        <div className="text-muted-foreground/60">
          <Book className="h-12 w-12" />
        </div>

        {/* Watching indicator overlay */}
        <div className="absolute right-2 top-2">
          <Badge variant="default" className="text-xs">
            <Check className="mr-1 h-2.5 w-2.5" />
            Watching
          </Badge>
        </div>
      </div>

      <div className="space-y-2 p-3">
        <div>
          <h3 className="mb-1 line-clamp-2 text-sm font-semibold">{series.series_title}</h3>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>Last checked: {lastChecked}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-1.5 pt-1">
          <WatchToggle 
            seriesId={series.series_id}
            isWatching={series.watching_enabled}
            variant="button"
            size="sm"
            className="w-full text-xs h-7"
          />
          <Button asChild size="sm" className="w-full text-xs h-7">
            <Link href={`/library/series/${series.series_id}`}>View Series</Link>
          </Button>
        </div>
      </div>
    </GlassCard>
  );
}

export function WatchedSeriesList({ 
  watchedSeries, 
  viewMode, 
  onSeriesRemoved,
  className 
}: WatchedSeriesListProps) {
  const [sortBy, setSortBy] = useState<'title' | 'last_checked'>('title');
  const [filterRecent, setFilterRecent] = useState(false);

  const filteredAndSortedSeries = useMemo(() => {
    let filtered = [...watchedSeries];

    // Filter for recent activity if enabled
    if (filterRecent) {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      filtered = filtered.filter(series => 
        series.last_watched_check && 
        new Date(series.last_watched_check) > oneDayAgo
      );
    }

    // Sort
    filtered.sort((a, b) => {
      if (sortBy === 'title') {
        return a.series_title.localeCompare(b.series_title);
      } else {
        // Sort by last_watched_check, with null values last
        const aDate = a.last_watched_check ? new Date(a.last_watched_check) : new Date(0);
        const bDate = b.last_watched_check ? new Date(b.last_watched_check) : new Date(0);
        return bDate.getTime() - aDate.getTime();
      }
    });

    return filtered;
  }, [watchedSeries, sortBy, filterRecent]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <BookOpen className="h-4 w-4" />
          <span>
            {filteredAndSortedSeries.length === watchedSeries.length 
              ? `${watchedSeries.length} watched series` 
              : `${filteredAndSortedSeries.length} of ${watchedSeries.length} series`
            }
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={sortBy === 'title' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSortBy('title')}
          >
            A-Z
          </Button>
          <Button
            variant={sortBy === 'last_checked' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSortBy('last_checked')}
          >
            <Calendar className="mr-2 h-4 w-4" />
            Recent
          </Button>
          <Button
            variant={filterRecent ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterRecent(!filterRecent)}
          >
            <Filter className="mr-2 h-4 w-4" />
            Today Only
          </Button>
        </div>
      </div>

      {/* Series List */}
      <div
        className={
          viewMode === 'grid'
            ? 'grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6'
            : 'space-y-2'
        }
        data-testid="watched-series-list"
      >
        {filteredAndSortedSeries.map((series) => (
          <WatchedSeriesCard 
            key={series.series_id} 
            series={series}
            viewMode={viewMode}
            onSeriesRemoved={onSeriesRemoved}
          />
        ))}
      </div>

      {filteredAndSortedSeries.length === 0 && watchedSeries.length > 0 && (
        <GlassCard className="p-8 text-center">
          <Filter className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="mb-2 text-lg font-semibold">No series match your filters</h3>
          <p className="text-muted-foreground mb-4">
            Try adjusting your filters to see more series.
          </p>
          <Button 
            onClick={() => {
              setSortBy('title');
              setFilterRecent(false);
            }}
            variant="outline"
          >
            Clear Filters
          </Button>
        </GlassCard>
      )}
    </div>
  );
}