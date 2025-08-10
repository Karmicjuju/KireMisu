/**
 * Series card component for library display
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProgressBar } from '@/components/ui/progress-bar';
import { TagChipList } from '@/components/tags';
import { WatchToggle } from './watch-toggle';
import { cn } from '@/lib/utils';
import { SeriesResponse } from '@/lib/api';
import { Book, BookOpen, Play, Check, Clock, BellRing } from 'lucide-react';

export interface SeriesCardProps {
  series: SeriesResponse;
  className?: string;
  viewMode?: 'grid' | 'list';
}

export function SeriesCard({ series, className, viewMode = 'grid' }: SeriesCardProps) {
  const progressPercentage =
    series.total_chapters > 0
      ? Math.round((series.read_chapters / series.total_chapters) * 100)
      : 0;

  const isCompleted = progressPercentage === 100;
  const hasProgress = progressPercentage > 0;
  const readingStatus = isCompleted ? 'completed' : hasProgress ? 'in-progress' : 'unread';

  if (viewMode === 'list') {
    return (
      <GlassCard className={cn('overflow-hidden transition-all hover:bg-accent/5', className)} data-testid="series-card">
        <div className="flex items-center gap-4 p-4">
          {/* Compact Cover */}
          <div className="relative flex h-16 w-12 items-center justify-center bg-gradient-to-br from-muted to-muted/80 rounded-sm flex-shrink-0">
            <Book className="h-6 w-6 text-muted-foreground/60" />
            {/* Watching indicator */}
            {series.watching_enabled && (
              <div className="absolute -top-1 -right-1">
                <div className="bg-primary text-primary-foreground rounded-full p-1">
                  <BellRing className="h-2.5 w-2.5" />
                </div>
              </div>
            )}
            {/* Progress indicator */}
            {hasProgress && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted rounded-b-sm overflow-hidden">
                <div 
                  className={cn(
                    "h-full transition-all",
                    isCompleted ? "bg-green-500" : "bg-primary"
                  )} 
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="font-medium text-sm line-clamp-1">{series.title_primary}</h3>
                {series.author && (
                  <p className="text-xs text-muted-foreground line-clamp-1">by {series.author}</p>
                )}
              </div>
              
              {/* Status badge */}
              <div className="flex-shrink-0">
                {isCompleted && (
                  <Badge variant="secondary" className="text-xs h-5">
                    <Check className="mr-1 h-2.5 w-2.5" />
                    Complete
                  </Badge>
                )}
                {hasProgress && !isCompleted && (
                  <Badge variant="outline" className="text-xs h-5">
                    <Clock className="mr-1 h-2.5 w-2.5" />
                    {progressPercentage}%
                  </Badge>
                )}
              </div>
            </div>

            {/* Progress and chapters */}
            {series.total_chapters > 0 && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <BookOpen className="h-3 w-3" />
                <span>{series.read_chapters} / {series.total_chapters} chapters</span>
              </div>
            )}

            {/* Genres (limited) */}
            {series.genres.length > 0 && (
              <div className="flex gap-1">
                {series.genres.slice(0, 2).map((genre) => (
                  <Badge key={genre} variant="outline" className="text-xs h-4 px-1">
                    {genre}
                  </Badge>
                ))}
                {series.genres.length > 2 && (
                  <Badge variant="outline" className="text-xs h-4 px-1">
                    +{series.genres.length - 2}
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <WatchToggle 
              seriesId={series.id}
              isWatching={series.watching_enabled}
              variant="button"
              size="sm"
            />
            <Button asChild size="sm" variant="outline">
              <Link href={`/library/series/${series.id}`}>View</Link>
            </Button>
            {series.total_chapters > 0 && (
              <Button asChild size="sm">
                <Link href={`/library/series/${series.id}/continue`}>
                  <Play className="mr-1 h-3 w-3" />
                  {hasProgress ? 'Continue' : 'Start'}
                </Link>
              </Button>
            )}
          </div>
        </div>
      </GlassCard>
    );
  }

  // Grid view - more compact than before
  return (
    <GlassCard className={cn('overflow-hidden transition-all hover:scale-105', className)} data-testid="series-card">
      <div className="relative flex aspect-[2/3] items-center justify-center bg-gradient-to-br from-muted to-muted/80">
        {/* Placeholder for cover image */}
        <div className="text-muted-foreground/60">
          <Book className="h-12 w-12" />
        </div>

        {/* Status overlays */}
        <div className="absolute right-2 top-2 space-y-1">
          {/* Watching indicator */}
          {series.watching_enabled && (
            <div className="flex justify-end">
              <div className="bg-primary text-primary-foreground rounded-full p-1">
                <BellRing className="h-2.5 w-2.5" />
              </div>
            </div>
          )}
          {/* Reading status */}
          {isCompleted && (
            <Badge variant="secondary" className="text-xs" data-testid="completion-badge">
              <Check className="mr-1 h-2.5 w-2.5" />
              Complete
            </Badge>
          )}
          {hasProgress && !isCompleted && (
            <Badge variant="outline" className="text-xs" data-testid="progress-badge">
              <Clock className="mr-1 h-2.5 w-2.5" />
              <span data-testid="progress-percentage">{progressPercentage}%</span>
            </Badge>
          )}
        </div>

        {/* Progress bar overlay at bottom */}
        {hasProgress && (
          <div className="absolute bottom-0 left-0 right-0 p-2">
            <ProgressBar
              value={progressPercentage}
              size="sm"
              variant="strong"
              colorScheme={isCompleted ? 'success' : 'primary'}
              animated={false}
              data-testid="progress-bar"
            />
          </div>
        )}
      </div>

      <div className="space-y-2 p-3">
        <div>
          <h3 className="mb-1 line-clamp-2 text-sm font-semibold">{series.title_primary}</h3>
          {series.author && (
            <p className="line-clamp-1 text-xs text-muted-foreground">by {series.author}</p>
          )}
        </div>

        {/* Compact progress section */}
        {series.total_chapters > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <BookOpen className="h-3 w-3" />
            <span data-testid="chapter-count-text">
              {series.read_chapters} / {series.total_chapters}
            </span>
            {readingStatus === 'completed' && <Check className="h-3 w-3 text-green-500" />}
            {readingStatus === 'in-progress' && <Clock className="h-3 w-3 text-primary" />}
          </div>
        )}

        {/* Limited genres */}
        {series.genres.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {series.genres.slice(0, 2).map((genre) => (
              <Badge key={genre} variant="outline" className="text-xs h-4 px-1">
                {genre}
              </Badge>
            ))}
            {series.genres.length > 2 && (
              <Badge variant="outline" className="text-xs h-4 px-1">
                +{series.genres.length - 2}
              </Badge>
            )}
          </div>
        )}

        {/* Compact actions */}
        <div className="space-y-1.5 pt-1">
          <WatchToggle 
            seriesId={series.id}
            isWatching={series.watching_enabled}
            variant="button"
            size="sm"
            className="w-full text-xs h-7"
          />
          <div className="flex gap-1.5">
            <Button asChild size="sm" className="flex-1 text-xs h-7">
              <Link href={`/library/series/${series.id}`}>View</Link>
            </Button>
            {series.total_chapters > 0 && (
              <Button asChild size="sm" variant="outline" className="text-xs h-7">
                <Link href={`/library/series/${series.id}/continue`}>
                  <Play className="mr-1 h-2.5 w-2.5" />
                  {hasProgress ? 'Continue' : 'Start'}
                </Link>
              </Button>
            )}
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
