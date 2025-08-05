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
import { cn } from '@/lib/utils';
import { SeriesResponse } from '@/lib/api';
import { Book, BookOpen, Play, Check, Clock } from 'lucide-react';

export interface SeriesCardProps {
  series: SeriesResponse;
  className?: string;
}

export function SeriesCard({ series, className }: SeriesCardProps) {
  const progressPercentage =
    series.total_chapters > 0
      ? Math.round((series.read_chapters / series.total_chapters) * 100)
      : 0;

  const isCompleted = progressPercentage === 100;
  const hasProgress = progressPercentage > 0;
  const readingStatus = isCompleted ? 'completed' : hasProgress ? 'in-progress' : 'unread';

  return (
    <GlassCard className={cn('overflow-hidden transition-all hover:scale-105', className)}>
      <div className="relative flex aspect-[3/4] items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
        {/* Placeholder for cover image */}
        <div className="text-white/40">
          <Book className="h-16 w-16" />
        </div>

        {/* Reading status overlay */}
        <div className="absolute right-2 top-2 flex gap-1">
          {isCompleted && (
            <Badge variant="secondary" className="text-xs">
              <Check className="mr-1 h-3 w-3" />
              Complete
            </Badge>
          )}
          {hasProgress && !isCompleted && (
            <Badge variant="outline" className="text-xs">
              <Clock className="mr-1 h-3 w-3" />
              {progressPercentage}%
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
            />
          </div>
        )}
      </div>

      <div className="space-y-3 p-4">
        <div>
          <h3 className="mb-1 line-clamp-2 font-semibold text-white">{series.title_primary}</h3>
          {series.author && (
            <p className="line-clamp-1 text-sm text-white/70">by {series.author}</p>
          )}
        </div>

        {/* Enhanced progress section */}
        {series.total_chapters > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-white/60">
              <BookOpen className="h-4 w-4" />
              <span>
                {series.read_chapters} / {series.total_chapters} chapters
              </span>
              {readingStatus === 'completed' && <Check className="h-4 w-4 text-green-500" />}
              {readingStatus === 'in-progress' && <Clock className="h-4 w-4 text-orange-500" />}
            </div>

            <ProgressBar
              value={series.read_chapters}
              max={series.total_chapters}
              size="sm"
              colorScheme={isCompleted ? 'success' : 'primary'}
              showValue={hasProgress}
            />
          </div>
        )}

        {series.genres.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {series.genres.slice(0, 3).map((genre) => (
              <Badge key={genre} variant="outline" className="text-xs">
                {genre}
              </Badge>
            ))}
            {series.genres.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{series.genres.length - 3}
              </Badge>
            )}
          </div>
        )}

        {series.user_tags && series.user_tags.length > 0 && (
          <TagChipList
            tags={series.user_tags}
            maxVisible={3}
            chipProps={{
              size: 'sm',
              variant: 'secondary',
            }}
          />
        )}

        <div className="flex gap-2 pt-2">
          <Button asChild size="sm" className="flex-1">
            <Link href={`/library/series/${series.id}`}>View Details</Link>
          </Button>

          {series.total_chapters > 0 && (
            <Button asChild size="sm" variant="outline">
              <Link href={`/library/series/${series.id}/continue`}>
                <Play className="mr-1 h-4 w-4" />
                {hasProgress ? 'Continue' : 'Start'}
              </Link>
            </Button>
          )}
        </div>
      </div>
    </GlassCard>
  );
}
