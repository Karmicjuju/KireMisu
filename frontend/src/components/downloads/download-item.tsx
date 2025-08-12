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
  User,
  Calendar,
  Timer,
  FileText,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  Zap,
  Archive,
  MoreVertical,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { JobStatusBadge } from '@/components/ui/job-status-badge';
import { ProgressBar } from '@/components/ui/progress-bar';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { DownloadJobResponse } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DownloadItemProps {
  download: DownloadJobResponse;
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onDelete: (jobId: string) => Promise<void>;
  selected?: boolean;
  onSelect?: () => void;
  viewMode?: 'list' | 'compact';
  className?: string;
}

export function DownloadItem({ 
  download, 
  onCancel, 
  onRetry, 
  onDelete,
  selected = false,
  onSelect,
  viewMode = 'list',
  className 
}: DownloadItemProps) {
  const [isActioning, setIsActioning] = React.useState(false);
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [isHovered, setIsHovered] = React.useState(false);

  const handleAction = async (action: () => Promise<void>) => {
    setIsActioning(true);
    try {
      await action();
    } finally {
      setIsActioning(false);
    }
  };

  // Copy ID to clipboard
  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(download.id);
      // Could add toast notification here
    } catch (err) {
      console.error('Failed to copy ID:', err);
    }
  };

  // Format duration helper
  const formatDuration = (start?: string, end?: string) => {
    if (!start) return null;
    if (!end && download.status === 'running') {
      const duration = Date.now() - new Date(start).getTime();
      const minutes = Math.floor(duration / 60000);
      const seconds = Math.floor((duration % 60000) / 1000);
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    if (end) {
      const duration = new Date(end).getTime() - new Date(start).getTime();
      const minutes = Math.floor(duration / 60000);
      const seconds = Math.floor((duration % 60000) / 1000);
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    return null;
  };

  // Enhanced progress calculation
  const getProgressPercentage = () => {
    if (!download.progress) return 0;
    
    const { total_chapters, downloaded_chapters, current_chapter_progress } = download.progress;
    
    if (total_chapters === 0) return 0;
    
    // Calculate overall progress including current chapter progress
    const completedProgress = downloaded_chapters / total_chapters;
    const currentProgress = current_chapter_progress / total_chapters;
    
    return Math.min((completedProgress + currentProgress) * 100, 100);
  };

  // Get priority level styling
  const getPriorityData = () => {
    if (download.priority >= 8) {
      return { label: 'Critical', color: 'red', icon: Zap };
    } else if (download.priority >= 6) {
      return { label: 'High', color: 'orange', icon: ChevronUp };
    } else if (download.priority >= 4) {
      return { label: 'Medium', color: 'blue', icon: ChevronDown };
    } else {
      return { label: 'Low', color: 'gray', icon: Clock };
    }
  };

  const priorityData = getPriorityData();

  // Enhanced color scheme and status styling
  const getStatusData = () => {
    switch (download.status) {
      case 'completed':
        return {
          colorScheme: 'success' as const,
          bgGradient: 'from-green-500/10 to-emerald-500/10',
          borderColor: 'border-green-500/20',
          textColor: 'text-green-400',
          icon: CheckCircle
        };
      case 'failed':
        return {
          colorScheme: 'warning' as const,
          bgGradient: 'from-red-500/10 to-pink-500/10',
          borderColor: 'border-red-500/20',
          textColor: 'text-red-400',
          icon: AlertCircle
        };
      case 'running':
        return {
          colorScheme: 'primary' as const,
          bgGradient: 'from-orange-500/10 to-red-500/10',
          borderColor: 'border-orange-500/20',
          textColor: 'text-orange-400',
          icon: Play
        };
      case 'pending':
        return {
          colorScheme: 'info' as const,
          bgGradient: 'from-blue-500/10 to-cyan-500/10',
          borderColor: 'border-blue-500/20',
          textColor: 'text-blue-400',
          icon: Clock
        };
      default:
        return {
          colorScheme: 'slate' as const,
          bgGradient: 'from-slate-500/10 to-gray-500/10',
          borderColor: 'border-slate-500/20',
          textColor: 'text-slate-400',
          icon: Download
        };
    }
  };

  const statusData = getStatusData();

  // Enhanced time formatting
  const formatTime = (dateString: string | undefined, showRelative = false) => {
    if (!dateString) return 'N/A';
    
    try {
      const date = new Date(dateString);
      
      if (showRelative) {
        const now = Date.now();
        const diff = now - date.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return 'Just now';
      }
      
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  };

  // Calculate estimated time remaining
  const getEstimatedTimeRemaining = () => {
    if (!download.progress || download.status !== 'running') return null;
    
    const { total_chapters, downloaded_chapters } = download.progress;
    const remaining = total_chapters - downloaded_chapters;
    
    if (remaining <= 0 || !download.started_at) return null;
    
    const elapsed = Date.now() - new Date(download.started_at).getTime();
    const avgTimePerChapter = elapsed / Math.max(downloaded_chapters, 1);
    const estimatedMs = avgTimePerChapter * remaining;
    
    const minutes = Math.floor(estimatedMs / 60000);
    const hours = Math.floor(estimatedMs / 3600000);
    
    if (hours > 0) return `~${hours}h ${minutes % 60}m`;
    return `~${minutes}m`;
  };

  // Enhanced download type display with icons
  const getDownloadTypeDisplay = () => {
    switch (download.download_type) {
      case 'all_chapters':
        return { label: 'All Chapters', icon: Layers, color: 'purple' };
      case 'volume':
        return { label: `Volume ${download.volume_number || '?'}`, icon: Book, color: 'blue' };
      case 'latest':
        return { label: 'Latest Chapters', icon: Zap, color: 'green' };
      case 'single_chapter':
        return { label: 'Single Chapter', icon: FileText, color: 'gray' };
      default:
        return { label: download.download_type, icon: Download, color: 'slate' };
    }
  };

  const downloadTypeData = getDownloadTypeDisplay();

  // Enhanced action availability
  const canCancel = download.status === 'pending' || download.status === 'running';
  const canRetry = download.status === 'failed';
  const canDelete = download.status === 'completed' || download.status === 'failed';
  const canArchive = download.status === 'completed';

  // Compact view for mobile/list mode
  if (viewMode === 'compact') {
    return (
      <GlassCard 
        className={cn(
          'transition-all duration-300 hover:shadow-lg cursor-pointer',
          'border-l-4',
          statusData.borderColor,
          selected && 'ring-2 ring-orange-500/50 bg-orange-500/5',
          isHovered && 'scale-[1.02]',
          className
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => onSelect?.()}
      >
        <div className="flex items-center gap-4 p-4">
          {onSelect && (
            <Checkbox
              checked={selected}
              onCheckedChange={onSelect}
              onClick={(e) => e.stopPropagation()}
              className="border-white/20"
            />
          )}
          
          {/* Compact Cover */}
          <div className="relative flex h-12 w-9 items-center justify-center bg-gradient-to-br from-muted to-muted/80 rounded-md flex-shrink-0 overflow-hidden">
            {download.manga_cover_url ? (
              <img
                src={download.manga_cover_url}
                alt={download.manga_title || 'Manga cover'}
                className="w-full h-full object-cover"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />
            ) : (
              <Book className="h-4 w-4 text-white/40" />
            )}
            
            {/* Status indicator */}
            <div className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full border border-black/20 bg-blue-500/80">
              <statusData.icon className="w-full h-full p-0.5 text-white" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="font-medium text-sm line-clamp-1 text-white/90">
                  {download.manga_title || 'Unknown Manga'}
                </h3>
                <div className="flex items-center gap-2 text-xs text-white/60 mt-1">
                  <Badge variant="outline" className="text-xs h-4 px-1">
                    {downloadTypeData.label}
                  </Badge>
                  {download.progress && (
                    <span>{Math.round(getProgressPercentage())}%</span>
                  )}
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="flex items-center gap-1 flex-shrink-0">
                {canCancel && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); handleAction(() => onCancel(download.id)); }}
                    disabled={isActioning}
                    className="h-6 w-6 p-0 hover:bg-red-500/20"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
                {canRetry && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); handleAction(() => onRetry(download.id)); }}
                    disabled={isActioning}
                    className="h-6 w-6 p-0 hover:bg-green-500/20"
                  >
                    <RotateCcw className="h-3 w-3" />
                  </Button>
                )}
                {canDelete && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); handleAction(() => onDelete(download.id)); }}
                    disabled={isActioning}
                    className="h-6 w-6 p-0 hover:bg-red-500/20"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </div>
            
            {/* Progress bar */}
            {download.progress && (
              <div className="mt-2">
                <ProgressBar
                  value={getProgressPercentage()}
                  size="sm"
                  colorScheme={statusData.colorScheme}
                  animated={download.status === 'running'}
                  showValue={false}
                />
              </div>
            )}
          </div>
        </div>
      </GlassCard>
    );
  }

  // Full detailed view
  return (
    <GlassCard 
      className={cn(
        'transition-all duration-300 group overflow-hidden',
        'hover:shadow-xl hover:scale-[1.01]',
        'border border-white/10 hover:border-white/20',
        selected && 'ring-2 ring-orange-500/50 bg-gradient-to-r from-orange-500/5 to-red-500/5',
        isHovered && 'shadow-2xl',
        className
      )}
      variant={selected ? 'strong' : 'default'}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="relative">
        {/* Selection overlay */}
        {selected && (
          <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 to-red-500/10 pointer-events-none" />
        )}
        
        <div className="relative p-6 space-y-6">
          {/* Enhanced Header Section */}
          <div className="flex items-start gap-4">
            {/* Selection checkbox */}
            {onSelect && (
              <div className="flex-shrink-0 pt-1">
                <Checkbox
                  checked={selected}
                  onCheckedChange={onSelect}
                  className="border-white/20 data-[state=checked]:bg-orange-500 data-[state=checked]:border-orange-500"
                />
              </div>
            )}
            
            {/* Cover Image with enhanced styling */}
            <div className="flex-shrink-0">
              <div className="relative group/cover">
                <div className="w-20 h-28 rounded-xl overflow-hidden border border-white/10 bg-gradient-to-br from-muted to-muted/80 shadow-lg">
                  {download.manga_cover_url ? (
                    <img
                      src={download.manga_cover_url}
                      alt={download.manga_title || 'Manga cover'}
                      className="w-full h-full object-cover transition-transform duration-300 group-hover/cover:scale-110"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Book className="h-8 w-8 text-white/40" />
                    </div>
                  )}
                </div>
                
                {/* Status indicator overlay */}
                <div className="absolute -top-2 -right-2 p-1.5 rounded-full border border-black/20 shadow-lg bg-gradient-to-r from-orange-500/20 to-red-500/20">
                  <statusData.icon className="h-4 w-4 text-white" />
                </div>
                
                {/* Priority indicator */}
                {download.priority > 5 && (
                  <div className="absolute -bottom-2 -right-2 p-1 rounded-full border border-black/20 shadow-lg bg-orange-500/90">
                    <priorityData.icon className="h-3 w-3 text-white" />
                  </div>
                )}
              </div>
            </div>

            {/* Enhanced Content Section */}
            <div className="flex-1 min-w-0 space-y-3">
              {/* Title and badges */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <h3 className="font-bold text-xl text-white/95 leading-tight line-clamp-2">
                    {download.manga_title || 'Unknown Manga'}
                  </h3>
                  
                  {/* Action menu */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={handleCopyId}>
                        <Copy className="mr-2 h-4 w-4" />
                        Copy ID
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setIsExpanded(!isExpanded)}>
                        {isExpanded ? <ChevronUp className="mr-2 h-4 w-4" /> : <ChevronDown className="mr-2 h-4 w-4" />}
                        {isExpanded ? 'Collapse' : 'Expand'} Details
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {canArchive && (
                        <DropdownMenuItem>
                          <Archive className="mr-2 h-4 w-4" />
                          Archive
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                
                {/* Enhanced badges */}
                <div className="flex flex-wrap items-center gap-2">
                  <Badge 
                    variant="outline" 
                    className="text-xs h-6 px-2 bg-gradient-to-r from-orange-500/20 to-red-500/20 border-0 text-orange-400"
                  >
                    <statusData.icon className="mr-1 h-3 w-3" />
                    {download.status.charAt(0).toUpperCase() + download.status.slice(1)}
                  </Badge>
                  
                  <Badge 
                    variant="outline" 
                    className="text-xs h-6 px-2 bg-blue-500/20 border-blue-500/30 text-blue-400"
                  >
                    <downloadTypeData.icon className="mr-1 h-3 w-3" />
                    {downloadTypeData.label}
                  </Badge>
                  
                  {download.priority > 5 && (
                    <Badge 
                      variant="outline" 
                      className="text-xs h-6 px-2 bg-orange-500/20 border-orange-500/30 text-orange-400"
                    >
                      <priorityData.icon className="mr-1 h-3 w-3" />
                      {priorityData.label} Priority
                    </Badge>
                  )}
                  
                  {download.retry_count > 0 && (
                    <Badge variant="outline" className="text-xs h-6 px-2 bg-yellow-500/20 border-yellow-500/30 text-yellow-400">
                      <RotateCcw className="mr-1 h-3 w-3" />
                      Retry {download.retry_count}/{download.max_retries}
                    </Badge>
                  )}
                </div>
                
                {/* Author and metadata */}
                <div className="flex items-center gap-4 text-sm text-white/70">
                  {download.manga_author && (
                    <div className="flex items-center gap-1">
                      <User className="h-4 w-4" />
                      <span className="truncate">{download.manga_author}</span>
                    </div>
                  )}
                  
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    <span>{formatTime(download.created_at, true)}</span>
                  </div>
                  
                  {download.status === 'running' && download.started_at && (
                    <div className="flex items-center gap-1">
                      <Timer className="h-4 w-4" />
                      <span>{formatDuration(download.started_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced Progress Section */}
          {download.progress && (
            <div className="space-y-4">
              <div className="space-y-3">
                {/* Current chapter info */}
                {download.status === 'running' && download.progress.current_chapter && (
                  <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-orange-500/10 to-red-500/10 border border-orange-500/20 rounded-lg">
                    <div className="p-2 bg-orange-500/20 rounded-lg">
                      <Download className="h-4 w-4 text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-white/90 truncate">
                        Downloading: {download.progress.current_chapter.title}
                      </div>
                      {getEstimatedTimeRemaining() && (
                        <div className="text-xs text-white/60">
                          {getEstimatedTimeRemaining()} remaining
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Enhanced progress bar */}
                <ProgressBar
                  value={getProgressPercentage()}
                  colorScheme={statusData.colorScheme}
                  size="lg"
                  showValue
                  animated={download.status === 'running'}
                  description={
                    download.progress.total_chapters > 0
                      ? `${download.progress.downloaded_chapters} / ${download.progress.total_chapters} chapters`
                      : undefined
                  }
                />
                
                {/* Progress stats */}
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="text-lg font-bold text-white/90">
                      {download.progress.downloaded_chapters}
                    </div>
                    <div className="text-xs text-white/60">Downloaded</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="text-lg font-bold text-white/90">
                      {download.progress.total_chapters - download.progress.downloaded_chapters}
                    </div>
                    <div className="text-xs text-white/60">Remaining</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="text-lg font-bold text-white/90">
                      {Math.round(getProgressPercentage())}%
                    </div>
                    <div className="text-xs text-white/60">Complete</div>
                  </div>
                </div>

                {/* Error Summary */}
                {download.progress.error_count > 0 && (
                  <div className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-400" />
                    <div>
                      <div className="text-sm font-medium text-red-300">
                        {download.progress.error_count} chapter(s) failed to download
                      </div>
                      <div className="text-xs text-red-200/80">
                        These will be retried automatically
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Enhanced Error Message */}
          {download.error_message && (
            <div className="p-4 bg-gradient-to-r from-red-500/15 to-pink-500/15 border border-red-500/30 rounded-xl">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-red-500/20 rounded-lg flex-shrink-0">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-red-300 mb-2">
                    Download Failed
                  </div>
                  <div className="text-sm text-red-200/90 leading-relaxed">
                    {download.error_message}
                  </div>
                  {download.retry_count < download.max_retries && (
                    <div className="text-xs text-red-200/70 mt-2">
                      Automatic retry {download.retry_count + 1} of {download.max_retries} will occur shortly
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Expandable Metadata Section */}
          <div className="space-y-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full justify-between text-white/70 hover:text-white hover:bg-white/5"
            >
              <span className="text-sm">Details & Timeline</span>
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
            
            {isExpanded && (
              <div className="space-y-4 p-4 bg-white/5 rounded-xl border border-white/10">
                {/* Timeline */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-white/90">Timeline</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-3 text-xs">
                      <div className="p-1.5 bg-blue-500/20 rounded-md">
                        <Calendar className="h-3 w-3 text-blue-400" />
                      </div>
                      <div>
                        <div className="text-white/80">Created</div>
                        <div className="text-white/60">{formatTime(download.created_at)}</div>
                      </div>
                    </div>
                    
                    {download.started_at && (
                      <div className="flex items-center gap-3 text-xs">
                        <div className="p-1.5 bg-green-500/20 rounded-md">
                          <Play className="h-3 w-3 text-green-400" />
                        </div>
                        <div>
                          <div className="text-white/80">Started</div>
                          <div className="text-white/60">{formatTime(download.started_at)}</div>
                        </div>
                      </div>
                    )}
                    
                    {download.completed_at && (
                      <div className="flex items-center gap-3 text-xs">
                        <div className="p-1.5 bg-emerald-500/20 rounded-md">
                          <CheckCircle className="h-3 w-3 text-emerald-400" />
                        </div>
                        <div>
                          <div className="text-white/80">Completed</div>
                          <div className="text-white/60">{formatTime(download.completed_at)}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Technical Details */}
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="space-y-1">
                    <div className="text-white/80 font-medium">Download ID</div>
                    <div className="text-white/60 font-mono text-xs bg-white/5 p-2 rounded border">
                      {download.id.slice(0, 12)}...
                    </div>
                  </div>
                  
                  <div className="space-y-1">
                    <div className="text-white/80 font-medium">Retry Count</div>
                    <div className="text-white/60">
                      {download.retry_count} of {download.max_retries} attempts
                    </div>
                  </div>
                  
                  {download.started_at && download.status === 'running' && (
                    <div className="space-y-1">
                      <div className="text-white/80 font-medium">Duration</div>
                      <div className="text-white/60">
                        {formatDuration(download.started_at)}
                      </div>
                    </div>
                  )}
                  
                  {getEstimatedTimeRemaining() && (
                    <div className="space-y-1">
                      <div className="text-white/80 font-medium">Est. Remaining</div>
                      <div className="text-white/60">
                        {getEstimatedTimeRemaining()}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Enhanced Actions Section */}
          <div className="flex items-center justify-between pt-4 border-t border-white/10">
            <div className="flex items-center gap-3 text-xs text-white/60">
              <div className="flex items-center gap-1">
                <span>ID:</span>
                <button
                  onClick={handleCopyId}
                  className="font-mono hover:text-white transition-colors cursor-pointer"
                  title="Click to copy full ID"
                >
                  {download.id.slice(0, 8)}...
                </button>
              </div>
              
              {download.priority > 5 && (
                <Badge variant="outline" className="h-4 text-xs px-1">
                  P{download.priority}
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <TooltipProvider>
                {/* Enhanced action buttons */}
                {canCancel && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAction(() => onCancel(download.id))}
                        disabled={isActioning}
                        className="h-9 px-3 hover:bg-red-500/20 hover:border-red-500/30 transition-all"
                      >
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Cancel this download</TooltipContent>
                  </Tooltip>
                )}

                {canRetry && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAction(() => onRetry(download.id))}
                        disabled={isActioning}
                        className="h-9 px-3 hover:bg-green-500/20 hover:border-green-500/30 transition-all"
                      >
                        <RotateCcw className="h-4 w-4 mr-1" />
                        Retry
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Retry failed download</TooltipContent>
                  </Tooltip>
                )}

                {canDelete && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAction(() => onDelete(download.id))}
                        disabled={isActioning}
                        className="h-9 px-3 hover:bg-red-500/20 hover:border-red-500/30 transition-all"
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Delete
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Remove from downloads</TooltipContent>
                  </Tooltip>
                )}
                
                {canArchive && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-9 px-3 hover:bg-blue-500/20 hover:border-blue-500/30 transition-all"
                      >
                        <Archive className="h-4 w-4 mr-1" />
                        Archive
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Archive completed download</TooltipContent>
                  </Tooltip>
                )}
              </TooltipProvider>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}