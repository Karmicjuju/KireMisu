'use client';

import { useState } from 'react';
import { 
  Download, 
  Play, 
  Pause, 
  X, 
  RotateCcw, 
  Trash2, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  MoreHorizontal
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GlassCard } from '@/components/ui/glass-card';
import { ProgressBarWithStats } from '@/components/ui/progress-bar';
import { DownloadJobResponse } from '@/lib/api';
import { cn } from '@/lib/utils';
// Using button group instead of dropdown for actions

interface DownloadCardProps {
  download: DownloadJobResponse;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
  onDelete?: (jobId: string, force?: boolean) => void;
  showActions?: boolean;
  compact?: boolean;
}

export function DownloadCard({ 
  download, 
  onCancel, 
  onRetry, 
  onDelete, 
  showActions = true,
  compact = false 
}: DownloadCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusIcon = () => {
    switch (download.status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-orange-500" />;
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <Download className="h-4 w-4 text-slate-500" />;
    }
  };

  const getStatusBadge = () => {
    const variants = {
      running: 'default',
      completed: 'secondary',
      failed: 'destructive',
      pending: 'outline',
    } as const;

    return (
      <Badge variant={variants[download.status] || 'outline'} className="capitalize">
        {download.status}
      </Badge>
    );
  };

  const getProgressInfo = () => {
    if (!download.progress) return null;

    const { total_chapters, downloaded_chapters, current_chapter_progress } = download.progress;
    const overallProgress = (downloaded_chapters / total_chapters) * 100 + 
      (current_chapter_progress / total_chapters) * 100;

    return {
      current: downloaded_chapters,
      total: total_chapters,
      percentage: Math.min(100, overallProgress),
    };
  };

  const getEstimatedTime = () => {
    if (!download.started_at || download.status !== 'running' || !download.progress) {
      return null;
    }

    const startTime = new Date(download.started_at).getTime();
    const now = Date.now();
    const elapsed = (now - startTime) / 1000; // seconds

    const progress = getProgressInfo();
    if (!progress || progress.percentage <= 0) return null;

    const totalEstimated = elapsed / (progress.percentage / 100);
    const remaining = Math.max(0, totalEstimated - elapsed);

    if (remaining < 60) {
      return `${Math.round(remaining)}s remaining`;
    } else if (remaining < 3600) {
      return `${Math.round(remaining / 60)}m remaining`;
    } else {
      const hours = Math.floor(remaining / 3600);
      const minutes = Math.round((remaining % 3600) / 60);
      return `${hours}h ${minutes}m remaining`;
    }
  };

  const handleDelete = async (force = false) => {
    if (!onDelete) return;
    
    setIsDeleting(true);
    try {
      await onDelete(download.id, force);
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getDisplayTitle = () => {
    if (download.manga_title) {
      return download.manga_title;
    }
    // Fallback to manga ID if no title is available
    return `Manga ID: ${download.manga_id}`;
  };

  const getDisplaySubtitle = () => {
    const parts = [];
    
    if (download.manga_author) {
      parts.push(`by ${download.manga_author}`);
    }
    
    parts.push(`${download.download_type} download`);
    
    if (download.volume_number) {
      parts.push(`Volume ${download.volume_number}`);
    }
    
    return parts.join(' • ');
  };

  const progressInfo = getProgressInfo();
  const estimatedTime = getEstimatedTime();

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border border-border/50 bg-card/50">
        {getStatusIcon()}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-foreground truncate">
            {getDisplayTitle()}
          </div>
          {progressInfo ? (
            <div className="text-xs text-muted-foreground">
              {progressInfo.current} / {progressInfo.total} chapters
            </div>
          ) : (
            <div className="text-xs text-muted-foreground truncate">
              {getDisplaySubtitle()}
            </div>
          )}
        </div>
        {progressInfo && (
          <div className="w-20">
            <div className="h-1 bg-secondary rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${progressInfo.percentage}%` }}
              />
            </div>
          </div>
        )}
        {showActions && (
          <div className="flex items-center gap-1">
            {download.status === 'running' && onCancel && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => onCancel(download.id)}
                title="Cancel download"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
            {download.status === 'failed' && onRetry && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => onRetry(download.id)}
                title="Retry download"
              >
                <RotateCcw className="h-3 w-3" />
              </Button>
            )}
            {onDelete && (
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => handleDelete(download.status === 'running')}
                disabled={isDeleting}
                title={download.status === 'running' ? "Force delete" : "Delete download"}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <GlassCard className="p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <h3 className="font-semibold text-foreground">
              {getDisplayTitle()}
            </h3>
            <p className="text-sm text-muted-foreground">
              {getDisplaySubtitle()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge()}
          {showActions && (
            <div className="flex items-center gap-2">
              {download.status === 'running' && onCancel && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => onCancel(download.id)}
                >
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              )}
              {download.status === 'failed' && onRetry && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => onRetry(download.id)}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              )}
              {onDelete && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleDelete(download.status === 'running')}
                  disabled={isDeleting}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  {download.status === 'running' ? 'Force Delete' : 'Delete'}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Progress Section */}
      {progressInfo && (
        <div className="mb-4">
          <ProgressBarWithStats
            current={progressInfo.current}
            total={progressInfo.total}
            unit="chapters"
            colorScheme={
              download.status === 'completed' ? 'success' :
              download.status === 'failed' ? 'warning' :
              'primary'
            }
            showValue={true}
            animated={download.status === 'running'}
          />
          
          {/* Current Chapter Info */}
          {download.progress?.current_chapter && (
            <div className="mt-2 text-sm text-muted-foreground">
              Currently downloading: {download.progress.current_chapter.title || download.progress.current_chapter.id}
              ({Math.round(download.progress.current_chapter_progress * 100)}%)
            </div>
          )}

          {/* Estimated Time */}
          {estimatedTime && (
            <div className="mt-1 text-xs text-muted-foreground">
              {estimatedTime}
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {download.error_message && (
        <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
          <p className="text-sm text-destructive">{download.error_message}</p>
          {download.retry_count > 0 && (
            <p className="text-xs text-muted-foreground mt-1">
              Retry attempt {download.retry_count} of {download.max_retries}
            </p>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Priority: {download.priority}</span>
          {download.series_id && (
            <span>Linked to series</span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span>Created: {formatDate(download.created_at)}</span>
          {download.completed_at && (
            <span>Completed: {formatDate(download.completed_at)}</span>
          )}
        </div>
      </div>
    </GlassCard>
  );
}