'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { 
  DownloadJobResponse, 
  DownloadJobListResponse, 
  DownloadJobRequest,
  DownloadJobActionRequest,
  DownloadStatsResponse,
  downloadsApi 
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { useAdaptivePolling } from '@/hooks/use-adaptive-polling';
import { usePollingSettings } from '@/components/settings/polling-settings';

interface UseDownloadsOptions {
  status?: string;
  download_type?: string;
  page?: number;
  per_page?: number;
  /** @deprecated Use pollingStrategy instead */
  pollInterval?: number;
  enabled?: boolean;
  /** Advanced polling configuration */
  pollingStrategy?: {
    initialInterval?: number;
    maxInterval?: number;
    activeInterval?: number;
    backoffMultiplier?: number;
    maxConsecutiveErrors?: number;
  };
}

interface UseDownloadsReturn {
  downloads: DownloadJobResponse[];
  stats: {
    total: number;
    active_downloads: number;
    pending_downloads: number;
    failed_downloads: number;
    completed_downloads: number;
  };
  pagination?: DownloadJobListResponse['pagination'];
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createDownload: (request: DownloadJobRequest) => Promise<DownloadJobResponse | null>;
  performAction: (jobId: string, action: DownloadJobActionRequest) => Promise<boolean>;
  deleteDownload: (jobId: string, force?: boolean) => Promise<boolean>;
  /** Polling status information */
  polling: {
    isPolling: boolean;
    currentInterval: number;
    consecutiveErrors: number;
    isPaused: boolean;
    hasRecentActivity: boolean;
  };
  /** Polling control functions */
  pollingControl: {
    startPolling: () => void;
    stopPolling: () => void;
    pollNow: () => Promise<void>;
    resetPolling: () => void;
  };
}

export function useDownloads(options: UseDownloadsOptions = {}): UseDownloadsReturn {
  const [downloads, setDownloads] = useState<DownloadJobResponse[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    active_downloads: 0,
    pending_downloads: 0,
    failed_downloads: 0,
    completed_downloads: 0,
  });
  const [pagination, setPagination] = useState<DownloadJobListResponse['pagination']>();
  const [loading, setLoading] = useState(true); // Start with loading true for initial load
  const [refreshing, setRefreshing] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(true);
  const { toast } = useToast();

  // Get polling settings from localStorage
  const pollingSettings = usePollingSettings();

  const {
    status,
    download_type,
    page = 1,
    per_page = 20,
    pollInterval = pollingSettings.initialInterval * 1000, // Convert to milliseconds
    enabled = true,
    pollingStrategy = {},
  } = options;

  const mountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserActionRef = useRef<number>(0);

  // Track document visibility to pause polling when not needed
  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // Memoize the fetch function to prevent unnecessary re-renders
  const fetchDownloads = useCallback(async () => {
    if (!enabled || !mountedRef.current) return;

    // Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      // Show loading only on initial load - background polling is silent
      if (initialLoad) {
        setLoading(true);
      }
      setError(null);

      const response = await downloadsApi.getDownloadJobs({
        status,
        download_type,
        page,
        per_page,
      });

      if (!mountedRef.current) return;

      // Optimize state updates with batch update
      const newStats = {
        total: response.total,
        active_downloads: response.active_downloads,
        pending_downloads: response.pending_downloads,
        failed_downloads: response.failed_downloads,
        completed_downloads: response.completed_downloads,
      };

      setDownloads(response.jobs);
      setStats(newStats);
      setPagination(response.pagination);
      
      if (initialLoad) {
        setInitialLoad(false);
        setHasLoadedOnce(true);
        setLoading(false); // Only clear loading after initial load completes
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch downloads';
      setError(errorMessage);
      console.error('Failed to fetch downloads:', err);
      
      // Clear loading state on error during initial load
      if (initialLoad) {
        setLoading(false);
        setHasLoadedOnce(true);
      }
      throw err; // Re-throw for adaptive polling error handling
    }
  }, [status, download_type, page, per_page, enabled, initialLoad]);

  // Memoize hasActiveWork function for adaptive polling
  const hasActiveWork = useCallback(() => {
    return stats.active_downloads > 0 || stats.pending_downloads > 0;
  }, [stats.active_downloads, stats.pending_downloads]);

  // Use adaptive polling for optimized performance with user-configured settings
  const adaptivePolling = useAdaptivePolling({
    enabled: enabled && isVisible, // Only poll when page is visible
    hasActiveWork,
    fetchFunction: fetchDownloads,
    strategy: {
      initialInterval: pollingSettings.initialInterval * 1000, // Convert to milliseconds
      activeInterval: pollingSettings.activeInterval * 1000, // Convert to milliseconds
      maxInterval: pollingSettings.maxInterval * 1000, // Convert to milliseconds
      backoffMultiplier: pollingStrategy.backoffMultiplier || 1.5,
      ...pollingStrategy, // Allow override if explicitly provided
    },
    maxConsecutiveErrors: pollingStrategy.maxConsecutiveErrors || pollingSettings.maxConsecutiveErrors,
    stopOnUnmount: true,
  });

  // Cleanup on unmount with proper abort controller cleanup
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const createDownload = useCallback(async (request: DownloadJobRequest): Promise<DownloadJobResponse | null> => {
    try {
      lastUserActionRef.current = Date.now();
      const response = await downloadsApi.createDownloadJob(request);
      toast({
        title: 'Download Started',
        description: `Download job created successfully for ${request.download_type} download`,
      });
      
      // Reset polling to start fresh with new activity
      adaptivePolling.resetPolling();
      
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create download';
      toast({
        title: 'Download Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      console.error('Failed to create download:', err);
      return null;
    }
  }, [adaptivePolling, toast]);

  const performAction = useCallback(async (jobId: string, action: DownloadJobActionRequest): Promise<boolean> => {
    try {
      lastUserActionRef.current = Date.now();
      const response = await downloadsApi.performJobAction(jobId, action);
      
      if (response.success) {
        toast({
          title: 'Action Completed',
          description: response.message,
        });
        
        // Immediately poll for updated data
        await adaptivePolling.pollNow();
        return true;
      } else {
        toast({
          title: 'Action Failed',
          description: response.message,
          variant: 'destructive',
        });
        return false;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to ${action.action} download`;
      toast({
        title: 'Action Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      console.error(`Failed to ${action.action} download:`, err);
      return false;
    }
  }, [adaptivePolling, toast]);

  const deleteDownload = useCallback(async (jobId: string, force = false): Promise<boolean> => {
    try {
      lastUserActionRef.current = Date.now();
      await downloadsApi.deleteDownloadJob(jobId, force);
      toast({
        title: 'Download Deleted',
        description: 'Download job has been deleted successfully',
      });
      
      // Immediately poll for updated data
      await adaptivePolling.pollNow();
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete download';
      toast({
        title: 'Delete Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      console.error('Failed to delete download:', err);
      return false;
    }
  }, [adaptivePolling, toast]);

  // Memoize refetch function to prevent unnecessary re-renders
  const refetch = useCallback(async () => {
    setRefreshing(true);
    try {
      await adaptivePolling.pollNow();
    } finally {
      setRefreshing(false);
    }
  }, [adaptivePolling]);

  return useMemo(() => ({
    downloads,
    stats,
    pagination,
    loading,
    refreshing,
    error,
    refetch,
    createDownload,
    performAction,
    deleteDownload,
    polling: {
      isPolling: adaptivePolling.isPolling,
      currentInterval: adaptivePolling.currentInterval,
      consecutiveErrors: adaptivePolling.consecutiveErrors,
      isPaused: adaptivePolling.isPaused,
      hasRecentActivity: adaptivePolling.hasRecentActivity,
    },
    pollingControl: {
      startPolling: adaptivePolling.startPolling,
      stopPolling: adaptivePolling.stopPolling,
      pollNow: adaptivePolling.pollNow,
      resetPolling: adaptivePolling.resetPolling,
    },
  }), [
    downloads,
    stats,
    pagination,
    loading,
    refreshing,
    error,
    refetch,
    createDownload,
    performAction,
    deleteDownload,
    adaptivePolling.isPolling,
    adaptivePolling.currentInterval,
    adaptivePolling.consecutiveErrors,
    adaptivePolling.isPaused,
    adaptivePolling.hasRecentActivity,
    adaptivePolling.startPolling,
    adaptivePolling.stopPolling,
    adaptivePolling.pollNow,
    adaptivePolling.resetPolling,
  ]);
}