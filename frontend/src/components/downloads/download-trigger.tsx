'use client';

import { useState } from 'react';
import { Download, Loader2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useDownloads } from '@/hooks/use-downloads';
import { useToast } from '@/hooks/use-toast';
import { DownloadJobRequest } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DownloadTriggerProps {
  mangaId: string;
  mangaTitle?: string;
  downloadType?: 'single' | 'batch' | 'series';
  chapterIds?: string[];
  seriesId?: string;
  volumeNumber?: string;
  priority?: number;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
  showLabel?: boolean;
  disabled?: boolean;
  className?: string;
}

export function DownloadTrigger({
  mangaId,
  mangaTitle,
  downloadType = 'series',
  chapterIds,
  seriesId,
  volumeNumber,
  priority = 5,
  variant = 'default',
  size = 'default',
  showLabel = true,
  disabled = false,
  className,
}: DownloadTriggerProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadStarted, setDownloadStarted] = useState(false);
  const { createDownload } = useDownloads({ enabled: false }); // Don't poll in trigger component
  const { toast } = useToast();

  const handleDownload = async () => {
    if (isDownloading || downloadStarted) return;

    setIsDownloading(true);
    
    try {
      const request: DownloadJobRequest = {
        download_type: downloadType,
        manga_id: mangaId,
        chapter_ids: chapterIds,
        series_id: seriesId,
        volume_number: volumeNumber,
        priority,
        notify_on_completion: true,
      };

      const result = await createDownload(request);
      
      if (result) {
        setDownloadStarted(true);
        toast({
          title: 'Download Started',
          description: `${downloadType} download for ${mangaTitle || mangaId} has been queued`,
        });
        
        // Reset state after a delay to allow re-downloading if needed
        setTimeout(() => {
          setDownloadStarted(false);
        }, 3000);
      }
    } catch (error) {
      console.error('Failed to start download:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  const getButtonContent = () => {
    if (isDownloading) {
      return (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          {showLabel && size !== 'sm' && <span className="ml-2">Starting...</span>}
        </>
      );
    }
    
    if (downloadStarted) {
      return (
        <>
          <Check className="h-4 w-4 text-green-500" />
          {showLabel && size !== 'sm' && <span className="ml-2">Queued</span>}
        </>
      );
    }
    
    return (
      <>
        <Download className="h-4 w-4" />
        {showLabel && size !== 'sm' && (
          <span className="ml-2">
            Download {downloadType === 'series' ? 'Series' : downloadType === 'batch' ? 'Chapters' : 'Chapter'}
          </span>
        )}
      </>
    );
  };

  const getDownloadLabel = () => {
    switch (downloadType) {
      case 'single':
        return 'Download Chapter';
      case 'batch':
        return `Download ${chapterIds?.length || 'Multiple'} Chapters`;
      case 'series':
        return 'Download Series';
      default:
        return 'Download';
    }
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Button
        variant={variant}
        size={size}
        onClick={handleDownload}
        disabled={disabled || isDownloading}
        className={cn(
          downloadStarted && "border-green-500/50 bg-green-500/10 hover:bg-green-500/20"
        )}
        title={getDownloadLabel()}
      >
        {getButtonContent()}
      </Button>
      
      {/* Additional info badges */}
      {volumeNumber && (
        <Badge variant="outline" className="text-xs">
          Vol. {volumeNumber}
        </Badge>
      )}
      {priority && priority >= 8 && (
        <Badge variant="default" className="text-xs bg-orange-500">
          High Priority
        </Badge>
      )}
    </div>
  );
}

// Quick download buttons for common scenarios
interface QuickDownloadProps {
  mangaId: string;
  mangaTitle?: string;
  seriesId?: string;
  className?: string;
}

export function QuickDownloadSeries({ mangaId, mangaTitle, seriesId, className }: QuickDownloadProps) {
  return (
    <DownloadTrigger
      mangaId={mangaId}
      mangaTitle={mangaTitle}
      downloadType="series"
      seriesId={seriesId}
      priority={5}
      variant="default"
      className={className}
    />
  );
}

export function QuickDownloadButton({ mangaId, mangaTitle, seriesId, className }: QuickDownloadProps) {
  return (
    <DownloadTrigger
      mangaId={mangaId}
      mangaTitle={mangaTitle}
      downloadType="series"
      seriesId={seriesId}
      priority={5}
      variant="outline"
      size="sm"
      showLabel={false}
      className={className}
    />
  );
}

// Batch download component for selecting multiple chapters
interface BatchDownloadTriggerProps {
  mangaId: string;
  mangaTitle?: string;
  seriesId?: string;
  availableChapters: Array<{
    id: string;
    title: string;
    number: string;
  }>;
  className?: string;
}

export function BatchDownloadTrigger({ 
  mangaId, 
  mangaTitle, 
  seriesId, 
  availableChapters, 
  className 
}: BatchDownloadTriggerProps) {
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);

  const handleChapterToggle = (chapterId: string) => {
    setSelectedChapters(prev => 
      prev.includes(chapterId) 
        ? prev.filter(id => id !== chapterId)
        : [...prev, chapterId]
    );
  };

  const selectAll = () => {
    setSelectedChapters(availableChapters.map(ch => ch.id));
  };

  const clearAll = () => {
    setSelectedChapters([]);
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Chapter Selection */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium">Select Chapters to Download</h4>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={selectAll}>
              Select All
            </Button>
            <Button variant="ghost" size="sm" onClick={clearAll}>
              Clear All
            </Button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
          {availableChapters.map((chapter) => (
            <label
              key={chapter.id}
              className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-accent"
            >
              <input
                type="checkbox"
                checked={selectedChapters.includes(chapter.id)}
                onChange={() => handleChapterToggle(chapter.id)}
                className="rounded"
              />
              <span className="text-sm">
                Ch. {chapter.number}: {chapter.title}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Download Trigger */}
      {selectedChapters.length > 0 && (
        <DownloadTrigger
          mangaId={mangaId}
          mangaTitle={mangaTitle}
          downloadType="batch"
          chapterIds={selectedChapters}
          seriesId={seriesId}
          priority={5}
          variant="default"
        />
      )}
    </div>
  );
}