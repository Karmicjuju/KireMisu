'use client';

import { useCallback, useState } from 'react';
import { mutate } from 'swr';
import { watchingApi } from '@/lib/api';
import { toast } from '@/hooks/use-toast';

export interface UseWatchingReturn {
  toggleWatch: (seriesId: string, currentState: boolean) => Promise<boolean>;
  isLoading: boolean;
}

export function useWatching(): UseWatchingReturn {
  const [isLoading, setIsLoading] = useState(false);

  // Toggle watch status for a series
  const toggleWatch = useCallback(async (seriesId: string, currentState: boolean): Promise<boolean> => {
    if (isLoading) return currentState;

    setIsLoading(true);
    try {
      const response = await watchingApi.toggleWatch(seriesId, !currentState);
      
      // Revalidate series data and any watching-related cache keys
      await Promise.all([
        mutate(`/api/series/${seriesId}`),
        mutate((key) => typeof key === 'string' && key.includes('/api/series')),
        mutate((key) => typeof key === 'string' && key.includes('/api/watching')),
      ]);

      return response.watching_enabled;
    } catch (error) {
      console.error('Failed to toggle watch status:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  return {
    toggleWatch,
    isLoading,
  };
}