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

// Chapter and reading interfaces
export interface ChapterResponse {
  id: string;
  series_id: string;
  series_title: string;
  chapter_number: number;
  volume_number?: number;
  title?: string;
  file_path: string;
  file_size: number;
  page_count: number;
  mangadx_id?: string;
  source_metadata: Record<string, any>;
  is_read: boolean;
  last_read_page: number;
  read_at?: string;
  created_at: string;
  updated_at: string;
  series?: SeriesResponse;
}

export interface SeriesResponse {
  id: string;
  title_primary: string;
  title_alternative?: string;
  description?: string;
  author?: string;
  artist?: string;
  genres: string[];
  tags: string[];
  publication_status?: string;
  content_rating?: string;
  language: string;
  file_path?: string;
  cover_image_path?: string;
  mangadx_id?: string;
  source_metadata: Record<string, any>;
  user_metadata: Record<string, any>;
  custom_tags: string[];
  total_chapters: number;
  read_chapters: number;
  created_at: string;
  updated_at: string;
}

export interface ChapterProgressUpdate {
  last_read_page: number;
  is_read?: boolean;
}

export interface ChapterPagesInfo {
  chapter_id: string;
  total_pages: number;
  pages: Array<{
    page_number: number;
    url: string;
  }>;
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

export const chaptersApi = {
  async getChapter(chapterId: string): Promise<ChapterResponse> {
    const response = await api.get<ChapterResponse>(`/api/reader/chapter/${chapterId}/info`);
    return response.data;
  },

  async getChapterPages(chapterId: string): Promise<ChapterPagesInfo> {
    // Get chapter info first to know page count
    const chapterResponse = await api.get<ChapterResponse>(`/api/reader/chapter/${chapterId}/info`);
    const chapter = chapterResponse.data;
    
    // Generate pages info based on chapter page count
    const pages = Array.from({ length: chapter.page_count }, (_, i) => ({
      page_number: i + 1,
      url: `${api.defaults.baseURL}/api/reader/chapter/${chapterId}/page/${i}`,
    }));
    
    return {
      chapter_id: chapterId,
      total_pages: chapter.page_count,
      pages,
    };
  },

  getChapterPageUrl(chapterId: string, pageNumber: number): string {
    return `${api.defaults.baseURL}/api/reader/chapter/${chapterId}/page/${pageNumber}`;
  },

  async getSeriesChapters(
    seriesId: string,
    options?: { skip?: number; limit?: number }
  ): Promise<ChapterResponse[]> {
    const params = new URLSearchParams();
    if (options?.skip) params.append('skip', options.skip.toString());
    if (options?.limit) params.append('limit', options.limit.toString());

    const response = await api.get<ChapterResponse[]>(
      `/api/chapters/series/${seriesId}/chapters${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async updateChapterProgress(
    chapterId: string,
    progress: ChapterProgressUpdate
  ): Promise<ChapterResponse> {
    const response = await api.put<ChapterResponse>(
      `/api/reader/chapter/${chapterId}/progress`,
      progress
    );
    return response.data;
  },
};

export const seriesApi = {
  async getSeriesList(options?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<SeriesResponse[]> {
    const params = new URLSearchParams();
    if (options?.skip) params.append('skip', options.skip.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.search) params.append('search', options.search);

    const response = await api.get<SeriesResponse[]>(
      `/api/series${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async getSeries(seriesId: string): Promise<SeriesResponse> {
    const response = await api.get<SeriesResponse>(`/api/series/${seriesId}`);
    return response.data;
  },

  async getSeriesChapters(
    seriesId: string,
    options?: { skip?: number; limit?: number }
  ): Promise<ChapterResponse[]> {
    const params = new URLSearchParams();
    if (options?.skip) params.append('skip', options.skip.toString());
    if (options?.limit) params.append('limit', options.limit.toString());

    const response = await api.get<ChapterResponse[]>(
      `/api/series/${seriesId}/chapters${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },
};

export default api;
