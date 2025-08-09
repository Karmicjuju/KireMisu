'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { DownloadJobResponse, downloadsApi } from '@/lib/api';
import { useAdaptivePolling } from '@/hooks/use-adaptive-polling';

interface UseDownloadProgressOptions {
  jobId: string;
  /** @deprecated Use pollingStrategy instead */
  pollInterval?: number;
  enabled?: boolean;
  stopOnComplete?: boolean;
  /** Advanced polling configuration */
  pollingStrategy?: {
    initialInterval?: number;
    maxInterval?: number;
    activeInterval?: number;
    backoffMultiplier?: number;
  };
}

interface UseDownloadProgressReturn {
  job: DownloadJobResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  progressPercentage: number;
  estimatedTimeRemaining: string | null;
  isActive: boolean;
  isComplete: boolean;
  hasFailed: boolean;
}

export function useDownloadProgress(options: UseDownloadProgressOptions): UseDownloadProgressReturn {
  const [job, setJob] = useState<DownloadJobResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    jobId,
    pollInterval = 2000,
    enabled = true,
    stopOnComplete = true,
    pollingStrategy = {},
  } = options;

  const mountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastFetchTimeRef = useRef(0);

  const fetchJob = useCallback(async () => {
    if (!enabled || !jobId || !mountedRef.current) return;

    // Prevent rapid successive calls
    const now = Date.now();
    if (now - lastFetchTimeRef.current < 1000) {
      return;
    }
    lastFetchTimeRef.current = now;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      setError(null);

      const response = await downloadsApi.getDownloadJob(jobId);

      if (!mountedRef.current) return;

      setJob(response);
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch download progress';
      setError(errorMessage);
      console.error('Failed to fetch download progress:', err);
      throw err; // Re-throw for adaptive polling
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [jobId, enabled]);

  // Determine if job has active work that needs polling
  const hasActiveWork = useCallback(() => {
    if (!job) return true; // Poll until we get initial data
    
    const isActive = job.status === 'running' || job.status === 'pending';
    
    // If stopOnComplete is true, stop polling when complete/failed
    if (stopOnComplete && (job.status === 'completed' || job.status === 'failed')) {
      return false;
    }
    
    return isActive;
  }, [job?.status, stopOnComplete]);

  // Use adaptive polling for this specific job
  useAdaptivePolling({
    enabled: enabled && !!jobId,
    hasActiveWork,
    fetchFunction: fetchJob,
    strategy: {
      initialInterval: pollInterval,
      activeInterval: Math.min(pollInterval, 1500), // Faster for active jobs
      maxInterval: Math.max(pollInterval * 6, 15000), // Max 15s or 6x initial
      backoffMultiplier: 1.3, // Gentler backoff for individual jobs
      ...pollingStrategy,
    },
    maxConsecutiveErrors: 5, // More tolerant for individual jobs
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Memoize computed values to prevent unnecessary recalculations
  const computedValues = useMemo(() => {
    const progressPercentage = job?.progress
      ? Math.min(100, (job.progress.downloaded_chapters / job.progress.total_chapters) * 100 +
          (job.progress.current_chapter_progress / job.progress.total_chapters) * 100)
      : 0;

    const isActive = job?.status === 'running';
    const isComplete = job?.status === 'completed';
    const hasFailed = job?.status === 'failed';

    const estimatedTimeRemaining = (() => {
      if (!job?.started_at || !job?.progress || job.progress.total_chapters === 0 || isComplete) {
        return null;
      }

      const startTime = new Date(job.started_at).getTime();
      const now = Date.now();
      const elapsed = (now - startTime) / 1000; // seconds

      const currentProgress = progressPercentage / 100;
      if (currentProgress <= 0) return null;

      const totalEstimated = elapsed / currentProgress;
      const remaining = Math.max(0, totalEstimated - elapsed);

      if (remaining < 60) {
        return `${Math.round(remaining)}s`;
      } else if (remaining < 3600) {
        return `${Math.round(remaining / 60)}m`;
      } else {
        const hours = Math.floor(remaining / 3600);
        const minutes = Math.round((remaining % 3600) / 60);
        return `${hours}h ${minutes}m`;
      }
    })();

    return {
      progressPercentage,
      isActive,
      isComplete,
      hasFailed,
      estimatedTimeRemaining,
    };
  }, [job]);

  return {
    job,
    loading,
    error,
    refetch: fetchJob,
    ...computedValues,
  };
}

// Hook for monitoring download statistics
interface UseDownloadStatsOptions {
  pollInterval?: number;
  enabled?: boolean;
}

interface UseDownloadStatsReturn {
  stats: {
    total_jobs: number;
    active_jobs: number;
    pending_jobs: number;
    failed_jobs: number;
    completed_jobs: number;
    jobs_created_today: number;
    jobs_completed_today: number;
    chapters_downloaded_today: number;
    average_job_duration_minutes?: number;
    success_rate_percentage: number;
  } | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useDownloadStats(options: UseDownloadStatsOptions = {}): UseDownloadStatsReturn {
  const [stats, setStats] = useState<UseDownloadStatsReturn['stats']>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    pollInterval = 10000, // 10 seconds for stats
    enabled = true,
  } = options;

  const mountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastFetchTimeRef = useRef(0);

  const fetchStats = useCallback(async () => {
    if (!enabled || !mountedRef.current) return;

    // Prevent rapid successive calls
    const now = Date.now();
    if (now - lastFetchTimeRef.current < 5000) { // Minimum 5s between stats calls
      return;
    }
    lastFetchTimeRef.current = now;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      setError(null);

      const response = await downloadsApi.getDownloadStats();

      if (!mountedRef.current) return;

      setStats(response);
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch download stats';
      setError(errorMessage);
      console.error('Failed to fetch download stats:', err);
      throw err; // Re-throw for potential adaptive polling
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled]);

  // Stats don't change as frequently, so we don't need hasActiveWork logic
  // Just use simpler polling with longer intervals
  useEffect(() => {
    if (!enabled) return;

    fetchStats(); // Initial fetch

    // Use simple interval for stats (they change less frequently)
    const intervalId = setInterval(fetchStats, pollInterval);

    return () => {
      clearInterval(intervalId);
    };
  }, [fetchStats, pollInterval, enabled]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return useMemo(() => ({
    stats,
    loading,
    error,
    refetch: fetchStats,
  }), [stats, loading, error, fetchStats]);
}