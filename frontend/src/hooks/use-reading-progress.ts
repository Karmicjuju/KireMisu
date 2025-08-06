/**
 * Reading progress hook for centralized progress management
 */

'use client';

import { useCallback, useMemo } from 'react';
import useSWR, { mutate } from 'swr';
import { 
  chaptersApi, 
  seriesApi, 
  dashboardApi,
  type ChapterResponse, 
  type SeriesResponse, 
  type SeriesProgress,
  type DashboardStats,
  type MarkReadRequest
} from '@/lib/api';
import { toast } from '@/hooks/use-toast';

export interface ReadingProgressHook {
  // Dashboard stats
  dashboardStats: DashboardStats | undefined;
  dashboardLoading: boolean;
  dashboardError: any;
  
  // Series progress
  getSeriesProgress: (seriesId: string) => {
    progress: SeriesProgress | undefined;
    loading: boolean;
    error: any;
  };
  
  // Chapter actions
  markChapterRead: (chapterId: string, isRead: boolean) => Promise<void>;
  updateChapterProgress: (chapterId: string, page: number, isRead?: boolean) => Promise<void>;
  
  // Utilities
  refreshDashboard: () => Promise<void>;
  refreshSeriesProgress: (seriesId: string) => Promise<void>;
  getProgressPercentage: (readChapters: number, totalChapters: number) => number;
  getProgressStatus: (readChapters: number, totalChapters: number) => 'unread' | 'in-progress' | 'completed';
  formatReadingTime: (hours: number) => string;
}

export function useReadingProgress(): ReadingProgressHook {
  // Dashboard stats query
  const {
    data: dashboardStats,
    error: dashboardError,
    isLoading: dashboardLoading,
  } = useSWR<DashboardStats>(
    '/api/dashboard/stats',
    dashboardApi.getStats,
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      errorRetryCount: 3,
      revalidateOnFocus: false,
    }
  );

  // Get series progress with caching
  const getSeriesProgress = useCallback((seriesId: string) => {
    const {
      data: progress,
      error,
      isLoading: loading,
    } = useSWR<SeriesProgress>(
      `/api/series/${seriesId}/progress`,
      () => seriesApi.getSeriesProgress(seriesId),
      {
        refreshInterval: 60000, // Refresh every minute
        errorRetryCount: 2,
        revalidateOnFocus: false,
      }
    );

    return { progress, loading, error };
  }, []);

  // Mark chapter as read/unread
  const markChapterRead = useCallback(
    async (chapterId: string, isRead: boolean) => {
      try {
        const markReadRequest: MarkReadRequest = { is_read: isRead };
        await chaptersApi.markChapterRead(chapterId, markReadRequest);

        // Revalidate related data
        await Promise.all([
          mutate('/api/dashboard/stats'),
          mutate((key) => typeof key === 'string' && key.includes('/progress')),
          mutate((key) => typeof key === 'string' && key.includes('/chapters')),
          mutate(`chapter-${chapterId}`),
        ]);

        toast({
          title: 'Success',
          description: `Chapter marked as ${isRead ? 'read' : 'unread'}`,
        });
      } catch (error) {
        console.error('Failed to mark chapter as read:', error);
        toast({
          title: 'Error',
          description: 'Failed to update reading status',
          variant: 'destructive',
        });
        throw error;
      }
    },
    []
  );

  // Update chapter reading progress
  const updateChapterProgress = useCallback(
    async (chapterId: string, page: number, isRead?: boolean) => {
      try {
        await chaptersApi.updateChapterProgress(chapterId, {
          last_read_page: page - 1, // Convert to 0-based
          is_read: isRead,
        });

        // Revalidate related data
        await Promise.all([
          mutate('/api/dashboard/stats'),
          mutate((key) => typeof key === 'string' && key.includes('/progress')),
          mutate(`chapter-${chapterId}`),
        ]);
      } catch (error) {
        console.error('Failed to update reading progress:', error);
        toast({
          title: 'Error',
          description: 'Failed to save reading progress',
          variant: 'destructive',
        });
        throw error;
      }
    },
    []
  );

  // Refresh dashboard data
  const refreshDashboard = useCallback(async () => {
    await mutate('/api/dashboard/stats');
  }, []);

  // Refresh series progress
  const refreshSeriesProgress = useCallback(async (seriesId: string) => {
    await mutate(`/api/series/${seriesId}/progress`);
  }, []);

  // Utility functions
  const getProgressPercentage = useCallback((readChapters: number, totalChapters: number): number => {
    if (totalChapters === 0) return 0;
    return Math.round((readChapters / totalChapters) * 100);
  }, []);

  const getProgressStatus = useCallback((readChapters: number, totalChapters: number): 'unread' | 'in-progress' | 'completed' => {
    if (readChapters === 0) return 'unread';
    if (readChapters === totalChapters) return 'completed';
    return 'in-progress';
  }, []);

  const formatReadingTime = useCallback((hours: number): string => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  }, []);

  return {
    dashboardStats,
    dashboardLoading,
    dashboardError,
    getSeriesProgress,
    markChapterRead,
    updateChapterProgress,
    refreshDashboard,
    refreshSeriesProgress,
    getProgressPercentage,
    getProgressStatus,
    formatReadingTime,
  };
}

// Specialized hook for series progress
export function useSeriesProgress(seriesId: string) {
  const {
    data: progress,
    error,
    isLoading: loading,
  } = useSWR<SeriesProgress>(
    `/api/series/${seriesId}/progress`,
    () => seriesApi.getSeriesProgress(seriesId),
    {
      refreshInterval: 60000,
      errorRetryCount: 2,
      revalidateOnFocus: false,
    }
  );

  return { progress, loading, error };
}

// Specialized hook for dashboard stats
export function useDashboardStats() {
  const {
    data: stats,
    error,
    isLoading: loading,
  } = useSWR<DashboardStats>(
    '/api/dashboard/stats',
    dashboardApi.getStats,
    {
      refreshInterval: 30000,
      errorRetryCount: 3,
      revalidateOnFocus: false,
    }
  );

  return { stats, loading, error };
}