/**
 * API client for KireMisu backend
 */

import axios from 'axios';

export interface LibraryPath {
  id: string;
  path: string;
  enabled: boolean;
  scan_interval_hours: number;
  last_scan: string | null;
  created_at: string;
  updated_at: string;
}

export interface LibraryPathCreate {
  path: string;
  enabled?: boolean;
  scan_interval_hours?: number;
}

export interface LibraryPathUpdate {
  path?: string;
  enabled?: boolean;
  scan_interval_hours?: number;
}

export interface LibraryPathList {
  paths: LibraryPath[];
  total: number;
}

export interface LibraryScanRequest {
  library_path_id?: string;
}

export interface LibraryScanStats {
  series_found: number;
  series_created: number;
  series_updated: number;
  chapters_found: number;
  chapters_created: number;
  chapters_updated: number;
  errors: number;
}

export interface LibraryScanResponse {
  status: string;
  message: string;
  stats: LibraryScanStats;
}

// Job-related interfaces
export interface JobResponse {
  id: string;
  job_type: string;
  payload: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  retry_count: number;
  max_retries: number;
  scheduled_at: string;
  created_at: string;
  updated_at: string;
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  job_type_filter?: string;
}

export interface JobScheduleRequest {
  job_type: 'library_scan' | 'auto_schedule';
  library_path_id?: string;
  priority?: number;
}

export interface JobScheduleResponse {
  status: string;
  message: string;
  job_id?: string;
  scheduled_count: number;
  skipped_count?: number;
  total_paths?: number;
}

export interface JobStatsResponse {
  queue_stats: Record<string, number>;
  worker_status?: Record<string, any>;
  timestamp: string;
}

export interface WorkerStatusResponse {
  running: boolean;
  active_jobs: number;
  max_concurrent_jobs: number;
  poll_interval_seconds: number;
  message?: string;
}

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 60000, // Increased timeout for library scanning operations
});

export const libraryApi = {
  async getPaths(): Promise<LibraryPathList> {
    const response = await api.get<LibraryPathList>('/api/library/paths');
    return response.data;
  },

  async getPath(id: string): Promise<LibraryPath> {
    const response = await api.get<LibraryPath>(`/api/library/paths/${id}`);
    return response.data;
  },

  async createPath(data: LibraryPathCreate): Promise<LibraryPath> {
    const response = await api.post<LibraryPath>('/api/library/paths', data);
    return response.data;
  },

  async updatePath(id: string, data: LibraryPathUpdate): Promise<LibraryPath> {
    const response = await api.put<LibraryPath>(`/api/library/paths/${id}`, data);
    return response.data;
  },

  async deletePath(id: string): Promise<void> {
    await api.delete(`/api/library/paths/${id}`);
  },

  async triggerScan(data?: LibraryScanRequest): Promise<LibraryScanResponse> {
    const response = await api.post<LibraryScanResponse>('/api/library/scan', data);
    return response.data;
  },
};

export const jobsApi = {
  async getJobStatus(): Promise<JobStatsResponse> {
    const response = await api.get<JobStatsResponse>('/api/jobs/status');
    return response.data;
  },

  async getRecentJobs(jobType?: string, limit?: number): Promise<JobListResponse> {
    const params = new URLSearchParams();
    if (jobType) params.append('job_type', jobType);
    if (limit) params.append('limit', limit.toString());
    
    const response = await api.get<JobListResponse>(
      `/api/jobs/recent${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async getJob(jobId: string): Promise<JobResponse> {
    const response = await api.get<JobResponse>(`/api/jobs/${jobId}`);
    return response.data;
  },

  async scheduleJob(data: JobScheduleRequest): Promise<JobScheduleResponse> {
    const response = await api.post<JobScheduleResponse>('/api/jobs/schedule', data);
    return response.data;
  },

  async getWorkerStatus(): Promise<WorkerStatusResponse> {
    const response = await api.get<WorkerStatusResponse>('/api/jobs/worker/status');
    return response.data;
  },

  async cleanupJobs(): Promise<{ deleted_count: number }> {
    const response = await api.post<{ deleted_count: number }>('/api/jobs/cleanup');
    return response.data;
  },
};

export default api;
