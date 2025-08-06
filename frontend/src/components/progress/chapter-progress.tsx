/**
 * Chapter progress display components
 */

'use client';

import React from 'react';
import { ProgressBar } from '@/components/ui/progress-bar';
import { MarkReadButton } from '@/components/ui/mark-read-button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { 
  BookOpen, 
  Clock, 
  Check, 
  Eye,
  EyeOff,
  Play,
  Bookmark,
  Calendar
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { ChapterResponse } from '@/lib/api';

export interface ChapterProgressIndicatorProps {
  chapter: ChapterResponse;
  onMarkRead?: (chapterId: string, isRead: boolean) => Promise<void>;
  className?: string;
  variant?: 'default' | 'compact' | 'detailed';
  showProgress?: boolean;
}

export function ChapterProgressIndicator({ 
  chapter, 
  onMarkRead,
  className,
  variant = 'default',
  showProgress = true
}: ChapterProgressIndicatorProps) {
  const progressPercentage = chapter.page_count > 0
    ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
    : 0;

  const isCompleted = chapter.is_read;
  const hasProgress = chapter.last_read_page > 0 || isCompleted;

  if (variant === 'compact') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className={cn(
          'rounded-full p-1.5',
          isCompleted ? 'bg-green-500/20' : hasProgress ? 'bg-orange-500/20' : 'bg-slate-500/20'
        )}>
          {isCompleted ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : hasProgress ? (
            <Clock className="h-3 w-3 text-orange-500" />
          ) : (
            <BookOpen className="h-3 w-3 text-slate-400" />
          )}
        </div>
        
        {showProgress && (
          <div className="flex-1 min-w-0">
            <ProgressBar
              value={isCompleted ? 100 : progressPercentage}
              size="sm"
              colorScheme={isCompleted ? 'success' : 'primary'}
              showValue={false}
              data-testid="chapter-progress-bar"
            />
          </div>
        )}

        {onMarkRead && (
          <MarkReadButton
            isRead={chapter.is_read}
            onToggle={(isRead) => onMarkRead(chapter.id, isRead)}
            variant="ghost"
            size="sm"
            appearance="icon"
            data-testid="mark-read-button"
          />
        )}
      </div>
    );
  }

  if (variant === 'detailed') {
    return (
      <div className={cn('space-y-3', className)}>
        {/* Status Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              'rounded-full p-2',
              isCompleted ? 'bg-green-500/20' : hasProgress ? 'bg-orange-500/20' : 'bg-slate-500/20'
            )}>
              {isCompleted ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : hasProgress ? (
                <Clock className="h-4 w-4 text-orange-500" />
              ) : (
                <BookOpen className="h-4 w-4 text-slate-400" />
              )}
            </div>
            <div>
              <p className="font-medium text-white">
                {isCompleted ? 'Completed' : hasProgress ? 'In Progress' : 'Unread'}
              </p>
              <p className="text-sm text-white/60">
                {isCompleted ? 'All pages read' : 
                 hasProgress ? `Page ${chapter.last_read_page + 1} of ${chapter.page_count}` :
                 `${chapter.page_count} pages`}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-white">
              {isCompleted ? '100' : progressPercentage}%
            </span>
            {onMarkRead && (
              <MarkReadButton
                isRead={chapter.is_read}
                onToggle={(isRead) => onMarkRead(chapter.id, isRead)}
                appearance="icon"
                data-testid="mark-read-button"
              />
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {showProgress && (
          <ProgressBar
            value={isCompleted ? 100 : progressPercentage}
            size="lg"
            colorScheme={isCompleted ? 'success' : 'primary'}
            showValue={false}
            animated={true}
            data-testid="chapter-progress-bar"
          />
        )}

        {/* Reading Info */}
        {(hasProgress || chapter.read_at) && (
          <div className="flex items-center justify-between text-sm text-white/60">
            {hasProgress && (
              <span>
                Page {chapter.last_read_page + 1} of {chapter.page_count}
              </span>
            )}
            {chapter.read_at && (
              <span>
                Read {formatDistanceToNow(new Date(chapter.read_at), { addSuffix: true })}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }

  // Default variant
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className={cn(
        'rounded-full p-2',
        isCompleted ? 'bg-green-500/20' : hasProgress ? 'bg-orange-500/20' : 'bg-slate-500/20'
      )}>
        {isCompleted ? (
          <Check className="h-4 w-4 text-green-500" />
        ) : hasProgress ? (
          <Clock className="h-4 w-4 text-orange-500" />
        ) : (
          <BookOpen className="h-4 w-4 text-slate-400" />
        )}
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/80">
            {isCompleted ? 'Complete' : hasProgress ? `${progressPercentage}%` : 'Unread'}
          </span>
          {hasProgress && !isCompleted && (
            <span className="text-xs text-white/60">
              Page {chapter.last_read_page + 1}/{chapter.page_count}
            </span>
          )}
        </div>

        {showProgress && (
          <ProgressBar
            value={isCompleted ? 100 : progressPercentage}
            size="sm"
            colorScheme={isCompleted ? 'success' : 'primary'}
            showValue={false}
            data-testid="chapter-progress-bar"
          />
        )}
      </div>

      {onMarkRead && (
        <MarkReadButton
          isRead={chapter.is_read}
          onToggle={(isRead) => onMarkRead(chapter.id, isRead)}
          variant="ghost"
          data-testid="mark-read-button"
        />
      )}
    </div>
  );
}

export interface ChapterProgressBarProps {
  chapter: ChapterResponse;
  className?: string;
  size?: 'sm' | 'default' | 'lg' | 'xl';
  showValue?: boolean;
  showPageInfo?: boolean;
}

export function ChapterProgressBar({ 
  chapter, 
  className,
  size = 'default',
  showValue = true,
  showPageInfo = true
}: ChapterProgressBarProps) {
  const progressPercentage = chapter.page_count > 0
    ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
    : 0;

  const isCompleted = chapter.is_read;
  const currentPage = chapter.last_read_page + 1;

  return (
    <div className={cn('space-y-2', className)}>
      {showPageInfo && (
        <div className="flex items-center justify-between text-sm text-white/60">
          <span>
            {isCompleted ? 'Completed' : 
             currentPage > 0 ? `Page ${currentPage} of ${chapter.page_count}` :
             `${chapter.page_count} pages`}
          </span>
          {showValue && (
            <span className="font-mono text-xs">
              {isCompleted ? '100' : progressPercentage}%
            </span>
          )}
        </div>
      )}
      
      <ProgressBar
        value={isCompleted ? 100 : progressPercentage}
        size={size}
        colorScheme={isCompleted ? 'success' : 'primary'}
        showValue={false}
        data-testid="chapter-progress-bar"
      />
    </div>
  );
}

export interface ReadingStatusBadgeProps {
  chapter: ChapterResponse;
  className?: string;
  variant?: 'default' | 'minimal' | 'detailed';
}

export function ReadingStatusBadge({ 
  chapter, 
  className,
  variant = 'default'
}: ReadingStatusBadgeProps) {
  const progressPercentage = chapter.page_count > 0
    ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
    : 0;

  const isCompleted = chapter.is_read;
  const hasProgress = chapter.last_read_page > 0 || isCompleted;

  if (variant === 'minimal') {
    return (
      <div className={cn(
        'rounded-full p-1.5',
        isCompleted ? 'bg-green-500/20' : hasProgress ? 'bg-orange-500/20' : 'bg-slate-500/20',
        className
      )}>
        {isCompleted ? (
          <Check className="h-3 w-3 text-green-500" />
        ) : hasProgress ? (
          <Clock className="h-3 w-3 text-orange-500" />
        ) : (
          <BookOpen className="h-3 w-3 text-slate-400" />
        )}
      </div>
    );
  }

  if (variant === 'detailed') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <Badge
          variant={isCompleted ? 'secondary' : hasProgress ? 'outline' : 'outline'}
          className={cn(
            'text-xs',
            isCompleted && 'text-green-400 border-green-400/50',
            hasProgress && !isCompleted && 'text-orange-400 border-orange-400/50'
          )}
        >
          {isCompleted ? (
            <>
              <Check className="mr-1 h-3 w-3" />
              Complete
            </>
          ) : hasProgress ? (
            <>
              <Clock className="mr-1 h-3 w-3" />
              {progressPercentage}%
            </>
          ) : (
            <>
              <BookOpen className="mr-1 h-3 w-3" />
              Unread
            </>
          )}
        </Badge>
        
        {hasProgress && (
          <span className="text-xs text-white/60">
            Page {chapter.last_read_page + 1}/{chapter.page_count}
          </span>
        )}

        {chapter.read_at && (
          <span className="text-xs text-white/40">
            {formatDistanceToNow(new Date(chapter.read_at), { addSuffix: true })}
          </span>
        )}
      </div>
    );
  }

  // Default variant
  return (
    <Badge
      variant={isCompleted ? 'secondary' : hasProgress ? 'outline' : 'outline'}
      className={cn(
        'text-xs',
        isCompleted && 'text-green-400 border-green-400/50',
        hasProgress && !isCompleted && 'text-orange-400 border-orange-400/50',
        className
      )}
      data-testid="reading-status-badge"
    >
      {isCompleted ? (
        <>
          <Check className="mr-1 h-3 w-3" />
          Complete
        </>
      ) : hasProgress ? (
        <>
          <Clock className="mr-1 h-3 w-3" />
          {progressPercentage}%
        </>
      ) : (
        <>
          <BookOpen className="mr-1 h-3 w-3" />
          Unread
        </>
      )}
    </Badge>
  );
}