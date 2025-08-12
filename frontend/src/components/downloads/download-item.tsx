'use client';

import React from 'react';
import { 
  Play, 
  Pause, 
  X, 
  RotateCcw, 
  Trash2, 
  AlertCircle, 
  CheckCircle, 
  Clock,
  Download,
  Book,
  User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { JobStatusBadge } from '@/components/ui/job-status-badge';
import { ProgressBar } from '@/components/ui/progress-bar';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DownloadJobResponse } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DownloadItemProps {
  download: DownloadJobResponse;
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onDelete: (jobId: string) => Promise<void>;
  className?: string;
}

export function DownloadItem({ 
  download, 
  onCancel, 
  onRetry, 
  onDelete,
  className 
}: DownloadItemProps) {
  const [isActioning, setIsActioning] = React.useState(false);

  const handleAction = async (action: () => Promise<void>) => {
    setIsActioning(true);
    try {
      await action();
    } finally {
      setIsActioning(false);
    }
  };

  // Calculate progress percentage
  const getProgressPercentage = () => {
    if (!download.progress) return 0;
    
    const { total_chapters, downloaded_chapters, current_chapter_progress } = download.progress;
    
    if (total_chapters === 0) return 0;
    
    // Calculate overall progress including current chapter progress
    const completedProgress = downloaded_chapters / total_chapters;
    const currentProgress = current_chapter_progress / total_chapters;
    
    return Math.min((completedProgress + currentProgress) * 100, 100);
  };

  // Get color scheme based on status
  const getProgressColorScheme = () => {
    switch (download.status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'warning';
      case 'running':
        return 'primary';
      default:
        return 'slate';
    }
  };

  // Format time helper
  const formatTime = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    
    try {
      return new Date(dateString).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  };

  // Get download type display name
  const getDownloadTypeDisplay = () => {
    switch (download.download_type) {
      case 'all_chapters':
        return 'All Chapters';
      case 'volume':
        return `Volume ${download.volume_number || '?'}`;
      case 'latest':
        return 'Latest Chapters';
      case 'single_chapter':
        return 'Single Chapter';
      default:
        return download.download_type;
    }
  };

  // Determine if actions are available
  const canCancel = download.status === 'pending' || download.status === 'running';
  const canRetry = download.status === 'failed';
  const canDelete = download.status === 'completed' || download.status === 'failed';

  return (
    <GlassCard className={cn('p-6 transition-all duration-200 hover:shadow-lg', className)}>
      <div className="space-y-4">
        {/* Header Section */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <JobStatusBadge status={download.status} />
              <Badge variant="outline" className="text-xs">
                {getDownloadTypeDisplay()}
              </Badge>
              {download.priority > 5 && (
                <Badge variant="secondary" className="text-xs">
                  High Priority
                </Badge>
              )}
            </div>
            
            <div className="space-y-1">
              <h3 className="font-semibold text-lg text-white/90 truncate">
                {download.manga_title || 'Unknown Manga'}
              </h3>
              
              {download.manga_author && (
                <div className="flex items-center gap-1 text-sm text-white/60">
                  <User className="h-3 w-3" />
                  <span className="truncate">{download.manga_author}</span>
                </div>
              )}
            </div>
          </div>

          {/* Cover Image */}
          {download.manga_cover_url && (
            <div className="flex-shrink-0">
              <img
                src={download.manga_cover_url}
                alt={download.manga_title || 'Manga cover'}
                className="w-16 h-20 object-cover rounded-lg border border-white/10"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />
            </div>
          )}
        </div>

        {/* Progress Section */}
        {download.progress && (
          <div className="space-y-2">
            <ProgressBar
              value={getProgressPercentage()}
              colorScheme={getProgressColorScheme()}
              showValue
              animated={download.status === 'running'}
              label={
                download.status === 'running' && download.progress.current_chapter
                  ? `Downloading: ${download.progress.current_chapter.title}`
                  : undefined
              }
              description={
                download.progress.total_chapters > 0
                  ? `${download.progress.downloaded_chapters} / ${download.progress.total_chapters} chapters`
                  : undefined
              }
            />

            {/* Error Summary */}
            {download.progress.error_count > 0 && (
              <div className="flex items-center gap-2 text-sm text-orange-400">
                <AlertCircle className="h-4 w-4" />
                <span>{download.progress.error_count} chapter(s) failed</span>
              </div>
            )}
          </div>
        )}

        {/* Error Message */}
        {download.error_message && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-red-300">
                <p className="font-medium mb-1">Error:</p>
                <p className="text-red-200/80">{download.error_message}</p>
              </div>
            </div>
          </div>
        )}

        {/* Metadata Section */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs text-white/60">
          <div>
            <div className="font-medium text-white/80 mb-1">Created</div>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatTime(download.created_at)}
            </div>
          </div>
          
          {download.started_at && (
            <div>
              <div className="font-medium text-white/80 mb-1">Started</div>
              <div className="flex items-center gap-1">
                <Play className="h-3 w-3" />
                {formatTime(download.started_at)}
              </div>
            </div>
          )}
          
          {download.completed_at && (
            <div>
              <div className="font-medium text-white/80 mb-1">Completed</div>
              <div className="flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {formatTime(download.completed_at)}
              </div>
            </div>
          )}

          <div>
            <div className="font-medium text-white/80 mb-1">Retries</div>
            <div>{download.retry_count} / {download.max_retries}</div>
          </div>
        </div>

        {/* Actions Section */}
        <div className="flex items-center justify-between pt-2 border-t border-white/10">
          <div className="text-xs text-white/50">
            ID: {download.id.slice(0, 8)}...
          </div>
          
          <div className="flex items-center gap-2">
            <TooltipProvider>
              {/* Cancel Button */}
              {canCancel && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAction(() => onCancel(download.id))}
                      disabled={isActioning}
                      className="h-8 w-8 p-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Cancel download
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Retry Button */}
              {canRetry && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAction(() => onRetry(download.id))}
                      disabled={isActioning}
                      className="h-8 w-8 p-0"
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Retry download
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Delete Button */}
              {canDelete && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAction(() => onDelete(download.id))}
                      disabled={isActioning}
                      className="h-8 w-8 p-0 hover:bg-red-500/20 hover:border-red-500/30"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Delete download
                  </TooltipContent>
                </Tooltip>
              )}
            </TooltipProvider>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}