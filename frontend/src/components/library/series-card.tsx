/**
 * Series card component for library display
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { SeriesResponse } from '@/lib/api';
import { Book, BookOpen, Play } from 'lucide-react';

export interface SeriesCardProps {
  series: SeriesResponse;
  className?: string;
}

export function SeriesCard({ series, className }: SeriesCardProps) {
  const progressPercentage =
    series.total_chapters > 0
      ? Math.round((series.read_chapters / series.total_chapters) * 100)
      : 0;

  return (
    <GlassCard className={cn('overflow-hidden transition-all hover:scale-105', className)}>
      <div className="relative flex aspect-[3/4] items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
        {/* Placeholder for cover image */}
        <div className="text-white/40">
          <Book className="h-16 w-16" />
        </div>

        {/* Reading progress overlay */}
        {progressPercentage > 0 && (
          <div className="absolute right-2 top-2">
            <Badge variant="secondary" className="text-xs">
              {progressPercentage}%
            </Badge>
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

        <div className="flex items-center gap-2 text-sm text-white/60">
          <BookOpen className="h-4 w-4" />
          <span>
            {series.read_chapters} / {series.total_chapters} chapters
          </span>
        </div>

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

        <div className="flex gap-2 pt-2">
          <Button asChild size="sm" className="flex-1">
            <Link href={`/library/series/${series.id}`}>View Details</Link>
          </Button>

          {series.total_chapters > 0 && (
            <Button asChild size="sm" variant="outline">
              <Link href={`/library/series/${series.id}/continue`}>
                <Play className="mr-1 h-4 w-4" />
                Continue
              </Link>
            </Button>
          )}
        </div>
      </div>
    </GlassCard>
  );
}
