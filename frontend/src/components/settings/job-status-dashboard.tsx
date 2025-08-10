'use client';

import React from 'react';
import { Clock, CheckCircle, XCircle, Play, Pause, Activity } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { JobStatusBadge } from '@/components/ui/job-status-badge';
import { Button } from '@/components/ui/button';
import {
  jobsApi,
  type JobResponse,
  type JobStatsResponse,
  type WorkerStatusResponse,
} from '@/lib/api';
import { formatRelativeTime, formatDateTime } from '@/lib/utils';
import useSWR from 'swr';

interface JobStatusDashboardProps {
  className?: string;
}

export function JobStatusDashboard({ className }: JobStatusDashboardProps) {
  // Stagger polling intervals to reduce server load
  const { data: jobStats, error: statsError } = useSWR('job-stats', jobsApi.getJobStatus, {
    refreshInterval: 30000, // Poll every 30 seconds (reduced from 8)
  });

  const { data: recentJobs, error: jobsError } = useSWR(
    'recent-jobs-dashboard',
    () => jobsApi.getRecentJobs(undefined, 15),
    {
      refreshInterval: 45000, // Poll every 45 seconds (reduced from 12)
    }
  );

  const { data: workerStatus } = useSWR('worker-status', jobsApi.getWorkerStatus, {
    refreshInterval: 60000, // Poll every 60 seconds (reduced from 15)
  });

  const formatJobDuration = (job: JobResponse) => {
    if (!job.started_at) return 'Not started';

    const startTime = new Date(job.started_at);
    const endTime = job.completed_at ? new Date(job.completed_at) : new Date();
    const durationMs = endTime.getTime() - startTime.getTime();
    const durationSeconds = Math.floor(durationMs / 1000);

    if (durationSeconds < 60) return `${durationSeconds}s`;
    const durationMinutes = Math.floor(durationSeconds / 60);
    if (durationMinutes < 60) return `${durationMinutes}m ${durationSeconds % 60}s`;
    const durationHours = Math.floor(durationMinutes / 60);
    return `${durationHours}h ${durationMinutes % 60}m`;
  };

  const getJobTypeDisplay = (jobType: string) => {
    switch (jobType) {
      case 'library_scan':
        return 'Library Scan';
      case 'auto_schedule':
        return 'Auto Schedule';
      default:
        return jobType;
    }
  };

  if (statsError || jobsError) {
    return (
      <div className={`rounded-lg border border-destructive/20 bg-destructive/10 p-4 ${className}`}>
        <div className="text-destructive">Failed to load job status information.</div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold">Job Status</h3>
        {workerStatus && (
          <div className="flex items-center gap-2">
            {workerStatus.running ? (
              <div className="flex items-center gap-2 text-green-600">
                <Play className="h-4 w-4" />
                <span className="text-sm">Worker Running</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-600">
                <Pause className="h-4 w-4" />
                <span className="text-sm">Worker Stopped</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Queue Statistics */}
      {jobStats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg border p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-muted-foreground">Pending</div>
              <Clock className="h-4 w-4 text-blue-500" />
            </div>
            <div className="text-2xl font-bold">{jobStats.queue_stats.pending || 0}</div>
          </div>

          <div className="rounded-lg border p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-muted-foreground">Running</div>
              <Activity className="h-4 w-4 text-orange-500" />
            </div>
            <div className="text-2xl font-bold">{jobStats.queue_stats.running || 0}</div>
          </div>

          <div className="rounded-lg border p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-muted-foreground">Completed</div>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </div>
            <div className="text-2xl font-bold">{jobStats.queue_stats.completed || 0}</div>
          </div>

          <div className="rounded-lg border p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-muted-foreground">Failed</div>
              <XCircle className="h-4 w-4 text-red-500" />
            </div>
            <div className="text-2xl font-bold">{jobStats.queue_stats.failed || 0}</div>
          </div>
        </div>
      )}

      {/* Worker Status Details */}
      {workerStatus && (
        <div className="rounded-lg border p-4">
          <h4 className="mb-3 font-medium">Worker Details</h4>
          <div className="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
            <div>
              <span className="font-medium">Active Jobs:</span> {workerStatus.active_jobs} /{' '}
              {workerStatus.max_concurrent_jobs}
            </div>
            <div>
              <span className="font-medium">Poll Interval:</span>{' '}
              {workerStatus.poll_interval_seconds}s
            </div>
            <div>
              <span className="font-medium">Status:</span>{' '}
              {workerStatus.running ? 'Active' : 'Inactive'}
            </div>
          </div>
          {workerStatus.message && (
            <div className="mt-2 text-sm text-muted-foreground">{workerStatus.message}</div>
          )}
        </div>
      )}

      {/* Recent Jobs */}
      <div>
        <h4 className="mb-3 font-medium">Recent Jobs</h4>
        {!recentJobs || recentJobs.jobs.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">No recent jobs found.</div>
        ) : (
          <div className="space-y-2">
            {recentJobs.jobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <JobStatusBadge status={job.status} size="sm" />
                  <div>
                    <div className="font-medium">{getJobTypeDisplay(job.job_type)}</div>
                    <div className="text-sm text-muted-foreground">
                      {job.payload.library_path_id
                        ? `Path: ${job.payload.library_path_id.slice(0, 8)}...`
                        : 'All paths'}
                      {job.priority !== 5 && (
                        <Badge variant="outline" className="ml-2 text-xs">
                          Priority {job.priority}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-right text-sm">
                  <div className="text-muted-foreground">{formatRelativeTime(job.created_at)}</div>
                  <div className="text-xs text-muted-foreground">
                    Duration: {formatJobDuration(job)}
                  </div>
                  {job.error_message && (
                    <div
                      className="mt-1 max-w-48 truncate text-xs text-red-600"
                      title={job.error_message}
                    >
                      {job.error_message}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {recentJobs.total > recentJobs.jobs.length && (
              <div className="py-2 text-center">
                <span className="text-sm text-muted-foreground">
                  Showing {recentJobs.jobs.length} of {recentJobs.total} jobs
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
