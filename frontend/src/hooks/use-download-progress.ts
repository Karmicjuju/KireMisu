'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { DownloadJobResponse, downloadsApi } from '@/lib/api';

interface UseDownloadProgressOptions {
  jobId: string;
  pollInterval?: number; // in milliseconds
  enabled?: boolean;
  stopOnComplete?: boolean;
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
    pollInterval = 2000, // 2 seconds for active downloads
    enabled = true,
    stopOnComplete = true,
  } = options;

  const pollIntervalRef = useRef<NodeJS.Timeout>();
  const mountedRef = useRef(true);

  const fetchJob = useCallback(async () => {
    if (!enabled || !jobId || !mountedRef.current) return;

    try {
      setLoading(true);
      setError(null);

      const response = await downloadsApi.getDownloadJob(jobId);

      if (!mountedRef.current) return;

      setJob(response);
    } catch (err) {
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch download progress';
      setError(errorMessage);
      console.error('Failed to fetch download progress:', err);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [jobId, enabled]);

  // Setup polling based on job status
  useEffect(() => {
    if (!enabled || !jobId) return;

    // Initial fetch
    fetchJob();

    // Setup polling interval based on job status
    if (pollInterval > 0) {
      pollIntervalRef.current = setInterval(() => {
        if (!mountedRef.current) return;

        // Stop polling if job is complete and stopOnComplete is true
        if (stopOnComplete && job && (job.status === 'completed' || job.status === 'failed')) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          return;
        }

        fetchJob();
      }, pollInterval);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [fetchJob, pollInterval, enabled, jobId, job?.status, stopOnComplete]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Computed values
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
    job,
    loading,
    error,
    refetch: fetchJob,
    progressPercentage,
    estimatedTimeRemaining,
    isActive,
    isComplete,
    hasFailed,
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

  const pollIntervalRef = useRef<NodeJS.Timeout>();
  const mountedRef = useRef(true);

  const fetchStats = useCallback(async () => {
    if (!enabled || !mountedRef.current) return;

    try {
      setLoading(true);
      setError(null);

      const response = await downloadsApi.getDownloadStats();

      if (!mountedRef.current) return;

      setStats(response);
    } catch (err) {
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch download stats';
      setError(errorMessage);
      console.error('Failed to fetch download stats:', err);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchStats();

    // Setup polling interval
    if (pollInterval > 0) {
      pollIntervalRef.current = setInterval(fetchStats, pollInterval);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [fetchStats, pollInterval, enabled]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return {
    stats,
    loading,
    error,
    refetch: fetchStats,
  };
}