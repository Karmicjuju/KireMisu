'use client';

import React from 'react';
import { Download, Play, Clock, CheckCircle, AlertCircle, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface DownloadHeaderProps {
  stats?: {
    total: number;
    active_downloads: number;
    pending_downloads: number;
    completed_downloads: number;
    failed_downloads: number;
  };
  onViewDownloads?: () => void;
  className?: string;
}

export function DownloadHeader({ 
  stats = {
    total: 0,
    active_downloads: 0,
    pending_downloads: 0,
    completed_downloads: 0,
    failed_downloads: 0
  },
  onViewDownloads,
  className 
}: DownloadHeaderProps) {
  const hasActiveDownloads = stats.active_downloads > 0;
  const hasFailedDownloads = stats.failed_downloads > 0;
  const totalActiveAndPending = stats.active_downloads + stats.pending_downloads;

  return (
    <TooltipProvider>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="ghost" 
            size="sm" 
            className={cn(
              'relative text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              hasActiveDownloads && 'text-orange-400',
              className
            )}
          >
            <Download className={cn(
              'h-4 w-4',
              hasActiveDownloads && 'animate-pulse'
            )} />
            
            {/* Active downloads indicator */}
            {totalActiveAndPending > 0 && (
              <Badge 
                variant={hasFailedDownloads ? "destructive" : "default"}
                className="absolute -top-1 -right-1 h-4 w-4 p-0 text-xs rounded-full border border-background"
              >
                {totalActiveAndPending > 99 ? '99+' : totalActiveAndPending}
              </Badge>
            )}
            
            <ChevronDown className="ml-1 h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        
        <DropdownMenuContent align="end" className="w-64">
          {/* Header */}
          <div className="p-3 border-b">
            <h3 className="font-semibold text-sm">Downloads</h3>
            <p className="text-xs text-muted-foreground">
              {stats.total === 0 ? 'No downloads' : `${stats.total} total downloads`}
            </p>
          </div>
          
          {/* Stats */}
          {stats.total > 0 && (
            <>
              <div className="p-2 space-y-1">
                {stats.active_downloads > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Play className="h-3 w-3 text-green-500" />
                      <span>Active</span>
                    </div>
                    <Badge variant="secondary" className="h-4 text-xs">
                      {stats.active_downloads}
                    </Badge>
                  </div>
                )}
                
                {stats.pending_downloads > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3 text-orange-500" />
                      <span>Pending</span>
                    </div>
                    <Badge variant="secondary" className="h-4 text-xs">
                      {stats.pending_downloads}
                    </Badge>
                  </div>
                )}
                
                {stats.completed_downloads > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-blue-500" />
                      <span>Completed</span>
                    </div>
                    <Badge variant="secondary" className="h-4 text-xs">
                      {stats.completed_downloads}
                    </Badge>
                  </div>
                )}
                
                {stats.failed_downloads > 0 && (
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-3 w-3 text-red-500" />
                      <span>Failed</span>
                    </div>
                    <Badge variant="destructive" className="h-4 text-xs">
                      {stats.failed_downloads}
                    </Badge>
                  </div>
                )}
              </div>
              
              <DropdownMenuSeparator />
            </>
          )}
          
          {/* Actions */}
          <div className="p-1">
            <DropdownMenuItem 
              onClick={onViewDownloads}
              className="cursor-pointer"
            >
              <Download className="mr-2 h-4 w-4" />
              View All Downloads
            </DropdownMenuItem>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>
    </TooltipProvider>
  );
}