/**
 * Series progress display components
 */

'use client';

import React from 'react';
import { ProgressBar, ProgressBarWithStats } from '@/components/ui/progress-bar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { 
  BookOpen, 
  Clock, 
  Check, 
  Star,
  TrendingUp,
  Calendar,
  Play,
  Pause,
  RotateCcw,
  Loader2
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { SeriesResponse, SeriesProgress, ChapterResponse } from '@/lib/api';

export interface SeriesProgressBarProps {
  series: SeriesResponse;
  className?: string;
  size?: 'sm' | 'default' | 'lg' | 'xl';
  showValue?: boolean;
  showStats?: boolean;
}

export function SeriesProgressBar({ 
  series, 
  className, 
  size = 'default',
  showValue = true,
  showStats = true
}: SeriesProgressBarProps) {
  const progressPercentage = series.total_chapters > 0
    ? Math.round((series.read_chapters / series.total_chapters) * 100)
    : 0;

  const isCompleted = progressPercentage === 100;
  const hasProgress = progressPercentage > 0;

  if (!showStats) {
    return (
      <ProgressBar
        value={series.read_chapters}
        max={series.total_chapters}
        size={size}
        colorScheme={isCompleted ? 'success' : 'primary'}
        showValue={showValue}
        className={className}
        data-testid="progress-bar"
      />
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-sm text-white/60">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4" />
          <span data-testid="progress-text">
            {series.read_chapters} / {series.total_chapters} chapters
          </span>
          {isCompleted && <Check className="h-4 w-4 text-green-500" />}
          {hasProgress && !isCompleted && <Clock className="h-4 w-4 text-orange-500" />}
        </div>
        {showValue && (
          <span className="font-mono text-xs" data-testid="progress-percentage">
            {progressPercentage}%
          </span>
        )}
      </div>
      
      <ProgressBar
        value={series.read_chapters}
        max={series.total_chapters}
        size={size}
        colorScheme={isCompleted ? 'success' : 'primary'}
        showValue={false}
        data-testid="progress-bar"
      />
    </div>
  );
}

export interface SeriesProgressSummaryProps {
  series: SeriesResponse;
  progress?: SeriesProgress;
  loading?: boolean;
  className?: string;
  compact?: boolean;
}

export function SeriesProgressSummary({ 
  series, 
  progress, 
  loading, 
  className,
  compact = false
}: SeriesProgressSummaryProps) {
  const progressPercentage = series.total_chapters > 0
    ? Math.round((series.read_chapters / series.total_chapters) * 100)
    : 0;

  const getProgressStatus = () => {
    if (progressPercentage === 100) return 'completed';
    if (progressPercentage > 0) return 'in-progress';
    return 'unread';
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          icon: Check,
          color: 'text-green-500',
          bgColor: 'bg-green-500/20',
          label: 'Completed',
        };
      case 'in-progress':
        return {
          icon: Play,
          color: 'text-orange-500',
          bgColor: 'bg-orange-500/20',
          label: 'In Progress',
        };
      default:
        return {
          icon: Pause,
          color: 'text-slate-400',
          bgColor: 'bg-slate-400/20',
          label: 'Unread',
        };
    }
  };

  const status = getProgressStatus();
  const statusConfig = getStatusConfig(status);
  const StatusIcon = statusConfig.icon;

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className={cn('rounded-full p-1.5', statusConfig.bgColor)}>
          <StatusIcon className={cn('h-3 w-3', statusConfig.color)} />
        </div>
        <span className="text-sm text-white/80">{progressPercentage}%</span>
        <div className="flex-1 min-w-0">
          <ProgressBar
            value={series.read_chapters}
            max={series.total_chapters}
            size="sm"
            colorScheme={status === 'completed' ? 'success' : 'primary'}
            showValue={false}
            data-testid="progress-bar"
          />
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn('rounded-full p-2', statusConfig.bgColor)}>
            <StatusIcon className={cn('h-5 w-5', statusConfig.color)} />
          </div>
          <div>
            <h3 className="font-medium text-white">{statusConfig.label}</h3>
            <p className="text-sm text-white/60">
              {series.read_chapters} of {series.total_chapters} chapters read
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-white" data-testid="progress-percentage">
            {progressPercentage}%
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <ProgressBarWithStats
        current={series.read_chapters}
        total={series.total_chapters}
        unit="chapters"
        colorScheme={status === 'completed' ? 'success' : 'primary'}
        size="lg"
        animated={true}
        data-testid="progress-bar"
      />

      {/* Additional Progress Info */}
      {progress && (
        <div className="grid grid-cols-2 gap-4 pt-2">
          {progress.last_read_chapter && (
            <div className="space-y-1">
              <p className="text-xs text-white/40 uppercase tracking-wide">Last Read</p>
              <p className="text-sm text-white font-medium">
                Chapter {progress.last_read_chapter.chapter_number}
              </p>
              {progress.last_activity && (
                <p className="text-xs text-white/60">
                  {formatDistanceToNow(new Date(progress.last_activity), { addSuffix: true })}
                </p>
              )}
            </div>
          )}

          {progress.next_unread_chapter && (
            <div className="space-y-1">
              <p className="text-xs text-white/40 uppercase tracking-wide">Up Next</p>
              <p className="text-sm text-white font-medium">
                Chapter {progress.next_unread_chapter.chapter_number}
              </p>
              {progress.next_unread_chapter.title && (
                <p className="text-xs text-white/60 truncate">
                  {progress.next_unread_chapter.title}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-2">
          <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
          <span className="ml-2 text-sm text-slate-400">Loading progress...</span>
        </div>
      )}
    </div>
  );
}

export interface ProgressBadgeProps {
  readChapters: number;
  totalChapters: number;
  className?: string;
  variant?: 'default' | 'compact' | 'detailed';
}

export function ProgressBadge({ 
  readChapters, 
  totalChapters, 
  className,
  variant = 'default'
}: ProgressBadgeProps) {
  const progressPercentage = totalChapters > 0
    ? Math.round((readChapters / totalChapters) * 100)
    : 0;

  const isCompleted = progressPercentage === 100;
  const hasProgress = progressPercentage > 0;

  if (variant === 'compact') {
    return (
      <Badge 
        variant={isCompleted ? 'secondary' : hasProgress ? 'outline' : 'outline'} 
        className={cn(
          'text-xs',
          isCompleted && 'text-green-400 border-green-400/50',
          hasProgress && !isCompleted && 'text-orange-400 border-orange-400/50',
          className
        )}
        data-testid="progress-badge"
      >
        {progressPercentage}%
      </Badge>
    );
  }

  if (variant === 'detailed') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <Badge 
          variant={isCompleted ? 'secondary' : 'outline'} 
          className={cn(
            'text-xs',
            isCompleted && 'text-green-400 border-green-400/50',
            hasProgress && !isCompleted && 'text-orange-400 border-orange-400/50'
          )}
          data-testid="progress-badge"
        >
          {isCompleted && <Check className="mr-1 h-3 w-3" />}
          {hasProgress && !isCompleted && <Clock className="mr-1 h-3 w-3" />}
          {isCompleted ? 'Complete' : `${progressPercentage}%`}
        </Badge>
        <span className="text-xs text-white/60">
          {readChapters}/{totalChapters}
        </span>
      </div>
    );
  }

  return (
    <Badge 
      variant={isCompleted ? 'secondary' : hasProgress ? 'outline' : 'outline'} 
      className={cn(
        'text-xs',
        isCompleted && 'text-green-400 border-green-400/50',
        hasProgress && !isCompleted && 'text-orange-400 border-orange-400/50',
        className
      )}
      data-testid="progress-badge"
    >
      {isCompleted && <Check className="mr-1 h-3 w-3" />}
      {hasProgress && !isCompleted && <Clock className="mr-1 h-3 w-3" />}
      {isCompleted ? 'Complete' : `${progressPercentage}%`}
    </Badge>
  );
}