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

interface UseDownloadsOptions {
  status?: string;
  download_type?: string;
  page?: number;
  per_page?: number;
  pollInterval?: number; // in milliseconds
  enabled?: boolean;
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
  error: string | null;
  refetch: () => Promise<void>;
  createDownload: (request: DownloadJobRequest) => Promise<DownloadJobResponse | null>;
  performAction: (jobId: string, action: DownloadJobActionRequest) => Promise<boolean>;
  deleteDownload: (jobId: string, force?: boolean) => Promise<boolean>;
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
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const {
    status,
    download_type,
    page = 1,
    per_page = 20,
    pollInterval = 3000, // 3 seconds default
    enabled = true,
  } = options;

  const pollIntervalRef = useRef<NodeJS.Timeout>();
  const mountedRef = useRef(true);

  const fetchDownloads = useCallback(async (isBackgroundRefresh = false) => {
    if (!enabled || !mountedRef.current) return;

    try {
      // Only show loading spinner on initial load or explicit user refresh
      if (!isBackgroundRefresh) {
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

      setDownloads(response.jobs);
      setStats({
        total: response.total,
        active_downloads: response.active_downloads,
        pending_downloads: response.pending_downloads,
        failed_downloads: response.failed_downloads,
        completed_downloads: response.completed_downloads,
      });
      setPagination(response.pagination);
      
      if (initialLoad) {
        setInitialLoad(false);
      }
    } catch (err) {
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch downloads';
      setError(errorMessage);
      console.error('Failed to fetch downloads:', err);
    } finally {
      if (mountedRef.current && !isBackgroundRefresh) {
        setLoading(false);
      }
    }
  }, [status, download_type, page, per_page, enabled]);

  // Setup polling for real-time updates with smart background refresh
  useEffect(() => {
    if (!enabled) return;

    // Initial fetch (with loading indicator)
    fetchDownloads(false);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [fetchDownloads, enabled]);

  // Separate effect for managing polling based on active downloads
  useEffect(() => {
    if (!enabled || pollInterval <= 0) return;

    // Always clear existing interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = undefined;
    }

    // Only set up polling if there are active or pending downloads
    const hasActiveWork = stats.active_downloads > 0 || stats.pending_downloads > 0;
    if (hasActiveWork) {
      pollIntervalRef.current = setInterval(() => {
        fetchDownloads(true); // Background refresh - no loading spinner
      }, pollInterval);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = undefined;
      }
    };
  }, [fetchDownloads, pollInterval, enabled, stats.active_downloads, stats.pending_downloads]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const createDownload = useCallback(async (request: DownloadJobRequest): Promise<DownloadJobResponse | null> => {
    try {
      const response = await downloadsApi.createDownloadJob(request);
      toast({
        title: 'Download Started',
        description: `Download job created successfully for ${request.download_type} download`,
      });
      
      // Refresh the downloads list (explicit user action)
      await fetchDownloads(false);
      
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
  }, [fetchDownloads, toast]);

  const performAction = useCallback(async (jobId: string, action: DownloadJobActionRequest): Promise<boolean> => {
    try {
      const response = await downloadsApi.performJobAction(jobId, action);
      
      if (response.success) {
        toast({
          title: 'Action Completed',
          description: response.message,
        });
        
        // Refresh the downloads list (explicit user action)
        await fetchDownloads(false);
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
  }, [fetchDownloads, toast]);

  const deleteDownload = useCallback(async (jobId: string, force = false): Promise<boolean> => {
    try {
      await downloadsApi.deleteDownloadJob(jobId, force);
      toast({
        title: 'Download Deleted',
        description: 'Download job has been deleted successfully',
      });
      
      // Refresh the downloads list (explicit user action)
      await fetchDownloads(false);
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
  }, [fetchDownloads, toast]);

  return {
    downloads,
    stats,
    pagination,
    loading,
    error,
    refetch: () => fetchDownloads(false), // Explicit refresh with loading indicator
    createDownload,
    performAction,
    deleteDownload,
  };
}