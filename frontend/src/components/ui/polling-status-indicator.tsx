'use client';

import { useState, useEffect } from 'react';
import { Activity, Pause, AlertTriangle, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface PollingStatusIndicatorProps {
  /** Whether polling is currently active */
  isPolling: boolean;
  /** Current polling interval in milliseconds */
  currentInterval: number;
  /** Number of consecutive errors */
  consecutiveErrors: number;
  /** Whether polling is paused due to errors */
  isPaused: boolean;
  /** Whether there has been recent activity */
  hasRecentActivity: boolean;
  /** Control functions for polling */
  onStart?: () => void;
  onStop?: () => void;
  onReset?: () => void;
  /** Whether to show the full status (default: false for compact mode) */
  showFullStatus?: boolean;
  /** Custom className */
  className?: string;
}

/**
 * Component that provides visual feedback about polling status and controls
 */
export function PollingStatusIndicator({
  isPolling,
  currentInterval,
  consecutiveErrors,
  isPaused,
  hasRecentActivity,
  onStart,
  onStop,
  onReset,
  showFullStatus = false,
  className,
}: PollingStatusIndicatorProps) {
  const [pulseAnimation, setPulseAnimation] = useState(false);

  // Trigger pulse animation when polling state changes
  useEffect(() => {
    if (isPolling) {
      setPulseAnimation(true);
      const timer = setTimeout(() => setPulseAnimation(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [isPolling]);

  // Determine status and appearance
  const status = (() => {
    if (isPaused) return 'paused';
    if (consecutiveErrors > 0) return 'warning';
    if (isPolling && hasRecentActivity) return 'active';
    if (isPolling) return 'idle';
    return 'stopped';
  })();

  const statusConfig = {
    active: {
      icon: Activity,
      color: 'text-green-500',
      bgColor: 'bg-green-500/20',
      label: 'Active polling',
      description: `Polling every ${Math.round(currentInterval / 1000)}s due to recent activity`,
    },
    idle: {
      icon: Wifi,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/20',
      label: 'Idle polling',
      description: `Polling every ${Math.round(currentInterval / 1000)}s with reduced frequency`,
    },
    warning: {
      icon: AlertTriangle,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/20',
      label: 'Polling with errors',
      description: `${consecutiveErrors} consecutive errors, polling every ${Math.round(currentInterval / 1000)}s`,
    },
    paused: {
      icon: Pause,
      color: 'text-red-500',
      bgColor: 'bg-red-500/20',
      label: 'Polling paused',
      description: 'Too many errors, polling temporarily stopped',
    },
    stopped: {
      icon: WifiOff,
      color: 'text-gray-500',
      bgColor: 'bg-gray-500/20',
      label: 'Polling stopped',
      description: 'No active polling',
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  if (!showFullStatus) {
    // Compact mode - just the icon with tooltip
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'flex items-center justify-center w-6 h-6 rounded-full transition-all duration-200',
                config.bgColor,
                pulseAnimation && 'animate-pulse',
                className
              )}
            >
              <Icon
                className={cn(
                  'w-3 h-3 transition-colors duration-200',
                  config.color
                )}
              />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="text-xs">
              <p className="font-medium">{config.label}</p>
              <p className="text-muted-foreground">{config.description}</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Full status mode - with controls and detailed info
  return (
    <div className={cn('flex items-center gap-2 p-2 rounded-lg border bg-card', className)}>
      <div
        className={cn(
          'flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200',
          config.bgColor,
          pulseAnimation && 'animate-pulse'
        )}
      >
        <Icon
          className={cn(
            'w-4 h-4 transition-colors duration-200',
            config.color
          )}
        />
      </div>
      
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{config.label}</p>
        <p className="text-xs text-muted-foreground truncate">
          {config.description}
        </p>
      </div>

      <div className="flex items-center gap-1">
        {status === 'paused' && onReset && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onReset}
                  className="h-7 px-2"
                >
                  Reset
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Reset error count and resume polling</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        {isPolling && onStop && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onStop}
                  className="h-7 px-2"
                >
                  <Pause className="w-3 h-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Stop polling</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        {!isPolling && onStart && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onStart}
                  className="h-7 px-2"
                >
                  <Activity className="w-3 h-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Start polling</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}

/**
 * Hook for managing polling status indicator state
 */
export function usePollingStatusIndicator(pollingData?: {
  isPolling: boolean;
  currentInterval: number;
  consecutiveErrors: number;
  isPaused: boolean;
  hasRecentActivity: boolean;
}) {
  const [showFullStatus, setShowFullStatus] = useState(false);

  // Auto-expand to full status when there are errors or when paused
  useEffect(() => {
    if (!pollingData) return;
    
    if (pollingData.consecutiveErrors > 0 || pollingData.isPaused) {
      setShowFullStatus(true);
      
      // Auto-collapse after 10 seconds if issues are resolved
      if (pollingData.consecutiveErrors === 0 && !pollingData.isPaused) {
        const timer = setTimeout(() => setShowFullStatus(false), 10000);
        return () => clearTimeout(timer);
      }
    }
  }, [pollingData?.consecutiveErrors, pollingData?.isPaused]);

  return {
    showFullStatus,
    setShowFullStatus,
  };
}