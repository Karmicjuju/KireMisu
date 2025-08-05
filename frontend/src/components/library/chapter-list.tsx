/**
 * Chapter list component with progress indicators and mark-read functionality
 */

'use client';

import * as React from 'react';
import Link from 'next/link';
import { format } from 'date-fns';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { ProgressBar } from '@/components/ui/progress-bar';
import { MarkReadButton, MarkAllReadButton } from '@/components/ui/mark-read-button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { ChapterResponse, chaptersApi } from '@/lib/api';
import { mutate } from 'swr';
import { toast } from 'sonner';
import { BookOpen, Calendar, FileText, Play, ChevronRight, Clock, Check } from 'lucide-react';
// import { formatDistanceToNow, format } from 'date-fns'; // Temporarily disabled to prevent build errors

export interface ChapterListProps {
  chapters: ChapterResponse[];
  seriesId?: string;
  showProgress?: boolean;
  showMarkAll?: boolean;
  variant?: 'default' | 'compact' | 'detailed';
  className?: string;
  onChapterUpdate?: (chapter: ChapterResponse) => void;
}

export interface ChapterItemProps {
  chapter: ChapterResponse;
  variant?: 'default' | 'compact' | 'detailed';
  showProgress?: boolean;
  onUpdate?: (chapter: ChapterResponse) => void;
}

const ChapterItem = React.forwardRef<HTMLDivElement, ChapterItemProps>(
  ({ chapter, variant = 'default', showProgress = true, onUpdate }, ref) => {
    const progressPercentage =
      chapter.page_count > 0 ? Math.round((chapter.last_read_page / chapter.page_count) * 100) : 0;

    const handleMarkRead = async (isRead: boolean) => {
      try {
        const updatedChapter = await chaptersApi.markChapterRead(chapter.id, { is_read: isRead });

        // Update local state
        onUpdate?.(updatedChapter);

        // Invalidate related SWR caches
        mutate(`/api/chapters/${chapter.id}`);
        mutate(`/api/series/${chapter.series_id}/chapters`);
        mutate(`/api/series/${chapter.series_id}/progress`);
        mutate('/api/dashboard/stats');

        toast.success(isRead ? 'Chapter marked as read' : 'Chapter marked as unread');
      } catch (error) {
        console.error('Failed to update chapter read status:', error);
        toast.error('Failed to update chapter status');
      }
    };

    const formatChapterTitle = () => {
      let title = `Chapter ${chapter.chapter_number}`;
      if (chapter.volume_number) {
        title = `Vol. ${chapter.volume_number}, ${title}`;
      }
      if (chapter.title) {
        title += `: ${chapter.title}`;
      }
      return title;
    };

    const getReadingStatus = () => {
      if (chapter.is_read) return 'completed';
      if (progressPercentage > 0) return 'in-progress';
      return 'unread';
    };

    const readingStatus = getReadingStatus();

    if (variant === 'compact') {
      return (
        <div
          ref={ref}
          className={cn(
            'flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-3 transition-all hover:bg-white/10',
            chapter.is_read && 'opacity-75'
          )}
        >
          <div className="flex-shrink-0">
            <MarkReadButton
              isRead={chapter.is_read}
              onToggle={handleMarkRead}
              variant="ghost"
              size="sm"
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h4 className="truncate text-sm font-medium text-white">{formatChapterTitle()}</h4>
              {readingStatus === 'completed' && <Check className="h-4 w-4 text-green-500" />}
              {readingStatus === 'in-progress' && <Clock className="h-4 w-4 text-orange-500" />}
            </div>

            {showProgress && progressPercentage > 0 && (
              <div className="mt-1">
                <ProgressBar
                  value={progressPercentage}
                  size="sm"
                  variant="subtle"
                  colorScheme="primary"
                />
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button asChild size="sm" variant="ghost">
              <Link href={`/reader/${chapter.id}`}>
                <Play className="h-4 w-4" />
              </Link>
            </Button>
            <ChevronRight className="h-4 w-4 text-white/40" />
          </div>
        </div>
      );
    }

    return (
      <GlassCard
        ref={ref}
        className={cn('transition-all hover:scale-[1.02]', chapter.is_read && 'opacity-75')}
      >
        <div className="p-4">
          <div className="mb-3 flex items-start justify-between">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2">
                <h3 className="truncate font-semibold text-white">{formatChapterTitle()}</h3>
                {readingStatus === 'completed' && (
                  <Badge variant="secondary" className="text-xs">
                    <Check className="mr-1 h-3 w-3" />
                    Read
                  </Badge>
                )}
                {readingStatus === 'in-progress' && (
                  <Badge variant="outline" className="text-xs">
                    <Clock className="mr-1 h-3 w-3" />
                    {progressPercentage}%
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-4 text-sm text-white/60">
                <div className="flex items-center gap-1">
                  <FileText className="h-4 w-4" />
                  <span>{chapter.page_count} pages</span>
                </div>

                <div className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  <span>
                    {new Date(chapter.created_at).toLocaleDateString()}
                  </span>
                </div>

                {chapter.file_size && (
                  <div className="flex items-center gap-1">
                    <BookOpen className="h-4 w-4" />
                    <span>{(chapter.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                  </div>
                )}
              </div>
            </div>

            <MarkReadButton isRead={chapter.is_read} onToggle={handleMarkRead} variant="subtle" />
          </div>

          {showProgress && (
            <div className="mb-3">
              <ProgressBar
                value={progressPercentage}
                label="Reading Progress"
                showValue={progressPercentage > 0}
                colorScheme={chapter.is_read ? 'success' : 'primary'}
              />
            </div>
          )}

          {variant === 'detailed' && chapter.read_at && (
            <div className="mb-3 rounded-lg bg-white/5 p-2">
              <p className="text-xs text-white/60">
                Last read: {format(new Date(chapter.read_at), 'PPp')}
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <Button asChild className="flex-1">
              <Link href={`/reader/${chapter.id}`}>
                <Play className="mr-2 h-4 w-4" />
                {progressPercentage > 0 ? 'Continue Reading' : 'Start Reading'}
              </Link>
            </Button>
          </div>
        </div>
      </GlassCard>
    );
  }
);

ChapterItem.displayName = 'ChapterItem';

const ChapterList = React.forwardRef<HTMLDivElement, ChapterListProps>(
  (
    {
      chapters,
      seriesId,
      showProgress = true,
      showMarkAll = false,
      variant = 'default',
      className,
      onChapterUpdate,
    },
    ref
  ) => {
    const [localChapters, setLocalChapters] = React.useState(chapters);

    // Update local chapters when props change
    React.useEffect(() => {
      setLocalChapters(chapters);
    }, [chapters]);

    const readCount = localChapters.filter((ch) => ch.is_read).length;

    const handleChapterUpdate = (updatedChapter: ChapterResponse) => {
      setLocalChapters((prev) =>
        prev.map((ch) => (ch.id === updatedChapter.id ? updatedChapter : ch))
      );
      onChapterUpdate?.(updatedChapter);
    };

    const handleMarkAll = async (markAsRead: boolean) => {
      const chaptersToUpdate = markAsRead
        ? localChapters.filter((ch) => !ch.is_read)
        : localChapters.filter((ch) => ch.is_read);

      try {
        // Update all chapters in parallel
        const updatePromises = chaptersToUpdate.map((chapter) =>
          chaptersApi.markChapterRead(chapter.id, { is_read: markAsRead })
        );

        const updatedChapters = await Promise.all(updatePromises);

        // Update local state
        setLocalChapters((prev) => {
          const updatedMap = new Map(updatedChapters.map((ch) => [ch.id, ch]));
          return prev.map((ch) => updatedMap.get(ch.id) || ch);
        });

        // Invalidate caches
        if (seriesId) {
          mutate(`/api/series/${seriesId}/chapters`);
          mutate(`/api/series/${seriesId}/progress`);
        }
        mutate('/api/dashboard/stats');

        toast.success(
          `${updatedChapters.length} chapters marked as ${markAsRead ? 'read' : 'unread'}`
        );
      } catch (error) {
        console.error('Failed to bulk update chapters:', error);
        toast.error('Failed to update chapters');
      }
    };

    if (localChapters.length === 0) {
      return (
        <GlassCard className="p-8 text-center">
          <BookOpen className="mx-auto mb-4 h-12 w-12 text-white/40" />
          <h3 className="mb-2 text-lg font-medium text-white/80">No chapters found</h3>
          <p className="text-sm text-white/60">This series doesn&apos;t have any chapters yet.</p>
        </GlassCard>
      );
    }

    return (
      <div ref={ref} className={cn('space-y-4', className)}>
        {showMarkAll && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-white/60">
              {readCount} of {localChapters.length} chapters read
            </div>
            <MarkAllReadButton
              itemCount={localChapters.length}
              readCount={readCount}
              onMarkAll={handleMarkAll}
            />
          </div>
        )}

        <div className={cn('space-y-3', variant === 'compact' && 'space-y-2')}>
          {localChapters.map((chapter) => (
            <ChapterItem
              key={chapter.id}
              chapter={chapter}
              variant={variant}
              showProgress={showProgress}
              onUpdate={handleChapterUpdate}
            />
          ))}
        </div>
      </div>
    );
  }
);

ChapterList.displayName = 'ChapterList';

export { ChapterList, ChapterItem };
