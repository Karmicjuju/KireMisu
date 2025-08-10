'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Bell, BellRing } from 'lucide-react';
import { useWatching } from '@/hooks/use-watching';
import { useToast } from '@/hooks/use-toast';

export interface WatchToggleProps {
  seriesId: string;
  isWatching?: boolean;
  variant?: 'button' | 'badge' | 'icon';
  size?: 'sm' | 'default' | 'lg';
  className?: string;
}

export function WatchToggle({
  seriesId,
  isWatching = false,
  variant = 'button',
  size = 'sm',
  className
}: WatchToggleProps) {
  const { toggleWatch, isLoading } = useWatching();
  const { toast } = useToast();
  
  // Use local state to track the watching status
  const [localWatchingState, setLocalWatchingState] = useState(isWatching);

  // Update local state when prop changes (from SWR cache updates)
  useEffect(() => {
    setLocalWatchingState(isWatching);
  }, [isWatching]);

  const handleToggle = async () => {
    try {
      const newWatchingState = await toggleWatch(seriesId, localWatchingState);
      
      // Update local state immediately for responsive UI
      setLocalWatchingState(newWatchingState);
      
      toast({
        title: newWatchingState ? 'Now watching' : 'No longer watching',
        description: newWatchingState 
          ? 'You\'ll be notified about new chapters'
          : 'You won\'t receive notifications for this series',
        variant: 'default'
      });
    } catch (error) {
      console.error('Failed to toggle watch status:', error);
      toast({
        title: 'Error',
        description: 'Failed to update watch status. Please try again.',
        variant: 'destructive'
      });
    }
  };

  if (variant === 'badge') {
    return (
      <Badge
        variant={localWatchingState ? 'default' : 'outline'}
        className={cn(
          "cursor-pointer transition-colors hover:bg-accent",
          isLoading && "opacity-50 cursor-not-allowed",
          className
        )}
        onClick={!isLoading ? handleToggle : undefined}
        aria-label={localWatchingState ? 'Stop watching' : 'Start watching'}
      >
        {localWatchingState ? (
          <BellRing className="h-2.5 w-2.5 mr-1" />
        ) : (
          <Bell className="h-2.5 w-2.5 mr-1" />
        )}
        {localWatchingState ? 'Watching' : 'Watch'}
      </Badge>
    );
  }

  if (variant === 'icon') {
    return (
      <Button
        variant="ghost"
        size={size}
        onClick={handleToggle}
        disabled={isLoading}
        className={cn(
          "text-muted-foreground hover:text-foreground",
          localWatchingState && "text-primary hover:text-primary/80",
          className
        )}
        aria-label={localWatchingState ? 'Stop watching' : 'Start watching'}
      >
        {localWatchingState ? (
          <BellRing className="h-3 w-3" />
        ) : (
          <Bell className="h-3 w-3" />
        )}
      </Button>
    );
  }

  // Default button variant
  return (
    <Button
      variant={localWatchingState ? 'default' : 'outline'}
      size={size}
      onClick={handleToggle}
      disabled={isLoading}
      className={cn(
        "transition-all",
        isLoading && "opacity-50",
        className
      )}
      aria-label={localWatchingState ? 'Stop watching' : 'Start watching'}
    >
      {localWatchingState ? (
        <BellRing className="h-3 w-3 mr-1" />
      ) : (
        <Bell className="h-3 w-3 mr-1" />
      )}
      {localWatchingState ? 'Watching' : 'Watch'}
    </Button>
  );
}