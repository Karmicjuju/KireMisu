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

export interface TagResponse {
  id: string;
  name: string;
  description?: string;
  color?: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface TagCreate {
  name: string;
  description?: string;
  color?: string;
}

export interface TagUpdate {
  name?: string;
  description?: string;
  color?: string;
}

export interface TagListResponse {
  tags: TagResponse[];
  total: number;
}

export interface SeriesTagAssignment {
  tag_ids: string[];
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
  user_tags: TagResponse[];
  total_chapters: number;
  read_chapters: number;
  watching_enabled: boolean;
  watching_config?: Record<string, any>;
  last_watched_check?: string;
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

// Dashboard statistics interfaces
export interface DashboardStats {
  total_series: number;
  total_chapters: number;
  chapters_read: number;
  reading_time_hours: number;
  favorites_count: number;
  recent_activity: RecentActivity[];
}

export interface RecentActivity {
  id: string;
  type: 'chapter_read' | 'series_added' | 'progress_updated';
  title: string;
  subtitle?: string;
  timestamp: string;
  series_id?: string;
  chapter_id?: string;
}

// Series progress interfaces
export interface SeriesProgress {
  series_id: string;
  total_chapters: number;
  read_chapters: number;
  unread_chapters: number;
  progress_percentage: number;
  last_read_chapter?: ChapterResponse;
  next_unread_chapter?: ChapterResponse;
  last_activity: string;
}

// Mark read request interface
export interface MarkReadRequest {
  is_read: boolean;
}

// Annotation interfaces
export interface AnnotationBase {
  content: string;
  page_number?: number;
  annotation_type: 'note' | 'bookmark' | 'highlight';
  position_x?: number;
  position_y?: number;
  color?: string;
}

export interface AnnotationCreate extends AnnotationBase {
  chapter_id: string;
}

export interface AnnotationUpdate {
  content?: string;
  page_number?: number;
  annotation_type?: 'note' | 'bookmark' | 'highlight';
  position_x?: number;
  position_y?: number;
  color?: string;
}

export interface AnnotationResponse extends AnnotationBase {
  id: string;
  chapter_id: string;
  created_at: string;
  updated_at: string;
  chapter?: ChapterResponse;
}

export interface AnnotationListResponse {
  annotations: AnnotationResponse[];
  total: number;
  chapter_id?: string;
  annotation_type?: string;
}

export interface ChapterAnnotationsResponse {
  chapter_id: string;
  chapter_title: string;
  total_pages: number;
  annotations: AnnotationResponse[];
  annotations_by_page: Record<number, AnnotationResponse[]>;
}

// Helper function to get the correct API URL based on context
const getApiUrl = (): string => {
  // Server-side (SSR, API routes): use internal Docker network URL
  if (typeof window === 'undefined') {
    return process.env.BACKEND_URL || 'http://backend:8000';
  }
  
  // Client-side (browser): use public URL
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

const api = axios.create({
  baseURL: getApiUrl(),
  timeout: 60000, // Increased timeout for library scanning operations
  withCredentials: true, // Include cookies in requests
});

// Auth header getter function - will be set by auth context
let getAuthHeaders: () => Record<string, string> = () => ({});

// Request interceptor to add auth headers
api.interceptors.request.use(
  (config) => {
    const authHeaders = getAuthHeaders();
    // Add auth headers (including CSRF token if available)
    Object.assign(config.headers, authHeaders);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth data and redirect to login
      if (typeof window !== 'undefined') {
        localStorage.removeItem('kiremisu_auth');
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

// Function to configure auth for the API client
export const configureApiAuth = (headerGetter: () => Record<string, string>) => {
  getAuthHeaders = headerGetter;
};

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
    return `${api.defaults.baseURL}/api/reader/chapter/${chapterId}/page/${pageNumber - 1}`;
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

  async markChapterRead(chapterId: string, markRead: MarkReadRequest): Promise<ChapterResponse> {
    const response = await api.put<ChapterResponse>(
      `/api/chapters/${chapterId}/mark-read`,
      markRead
    );
    return response.data;
  },
};

export const seriesApi = {
  async getSeriesList(options?: {
    skip?: number;
    limit?: number;
    search?: string;
    tag_ids?: string[];
    tag_names?: string[];
  }): Promise<SeriesResponse[]> {
    const params = new URLSearchParams();
    if (options?.skip) params.append('skip', options.skip.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.search) params.append('search', options.search);
    if (options?.tag_ids) {
      options.tag_ids.forEach(id => params.append('tag_ids', id));
    }
    if (options?.tag_names) {
      options.tag_names.forEach(name => params.append('tag_names', name));
    }

    const response = await api.get<SeriesResponse[]>(
      `/api/series/${params.toString() ? `?${params.toString()}` : ''}`
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

  async getSeriesProgress(seriesId: string): Promise<SeriesProgress> {
    const response = await api.get<SeriesProgress>(`/api/series/${seriesId}/progress`);
    return response.data;
  },
};

export const dashboardApi = {
  async getStats(): Promise<DashboardStats> {
    const response = await api.get<DashboardStats>('/api/dashboard/stats');
    return response.data;
  },
};

export const annotationsApi = {
  async createAnnotation(data: AnnotationCreate): Promise<AnnotationResponse> {
    const response = await api.post<AnnotationResponse>('/api/annotations/', data);
    return response.data;
  },

  async getAnnotation(annotationId: string, includeChapter?: boolean): Promise<AnnotationResponse> {
    const params = new URLSearchParams();
    if (includeChapter) params.append('include_chapter', 'true');

    const response = await api.get<AnnotationResponse>(
      `/api/annotations/${annotationId}${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async updateAnnotation(annotationId: string, data: AnnotationUpdate): Promise<AnnotationResponse> {
    const response = await api.put<AnnotationResponse>(`/api/annotations/${annotationId}`, data);
    return response.data;
  },

  async deleteAnnotation(annotationId: string): Promise<void> {
    await api.delete(`/api/annotations/${annotationId}`);
  },

  async listAnnotations(options?: {
    chapter_id?: string;
    annotation_type?: string;
    page_number?: number;
    limit?: number;
    offset?: number;
  }): Promise<AnnotationListResponse> {
    const params = new URLSearchParams();
    if (options?.chapter_id) params.append('chapter_id', options.chapter_id);
    if (options?.annotation_type) params.append('annotation_type', options.annotation_type);
    if (options?.page_number) params.append('page_number', options.page_number.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());

    const response = await api.get<AnnotationListResponse>(
      `/api/annotations/${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async getChapterAnnotations(
    chapterId: string,
    options?: {
      annotation_type?: string;
      page_number?: number;
    }
  ): Promise<ChapterAnnotationsResponse> {
    const params = new URLSearchParams();
    if (options?.annotation_type) params.append('annotation_type', options.annotation_type);
    if (options?.page_number) params.append('page_number', options.page_number.toString());

    const response = await api.get<ChapterAnnotationsResponse>(
      `/api/annotations/chapters/${chapterId}${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async getPageAnnotations(
    chapterId: string,
    pageNumber: number,
    annotationType?: string
  ): Promise<AnnotationResponse[]> {
    const params = new URLSearchParams();
    if (annotationType) params.append('annotation_type', annotationType);
    
    const response = await api.get<AnnotationResponse[]>(
      `/api/annotations/chapters/${chapterId}/pages/${pageNumber}${
        params.toString() ? `?${params.toString()}` : ''
      }`
    );
    return response.data;
  },

  async createPageAnnotation(
    chapterId: string,
    pageNumber: number,
    data: AnnotationCreate
  ): Promise<AnnotationResponse> {
    const response = await api.post<AnnotationResponse>(
      `/api/annotations/chapters/${chapterId}/pages/${pageNumber}`,
      data
    );
    return response.data;
  },

  async deleteChapterAnnotations(
    chapterId: string,
    options?: {
      annotation_type?: string;
      page_number?: number;
    }
  ): Promise<void> {
    const params = new URLSearchParams();
    if (options?.annotation_type) params.append('annotation_type', options.annotation_type);
    if (options?.page_number) params.append('page_number', options.page_number.toString());

    await api.delete(
      `/api/annotations/chapters/${chapterId}${params.toString() ? `?${params.toString()}` : ''}`
    );
  },
};

export const tagsApi = {
  async getTags(options?: {
    skip?: number;
    limit?: number;
    search?: string;
    sort_by?: 'name' | 'usage' | 'created';
  }): Promise<TagListResponse> {
    const params = new URLSearchParams();
    if (options?.skip) params.append('skip', options.skip.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.search) params.append('search', options.search);
    if (options?.sort_by) params.append('sort_by', options.sort_by);

    const response = await api.get<TagListResponse>(
      `/api/tags${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },
};

// Download interfaces
export interface DownloadJobProgressInfo {
  total_chapters: number;
  downloaded_chapters: number;
  current_chapter?: {
    id: string;
    title: string;
    started_at: string;
  } | null;
  current_chapter_progress: number; // 0.0-1.0
  error_count: number;
  errors: Array<{
    chapter_id: string;
    error: string;
    timestamp: string;
  }>;
  started_at?: string;
  estimated_completion?: string;
}

export interface DownloadJobRequest {
  download_type: 'single' | 'batch' | 'series';
  manga_id: string;
  chapter_ids?: string[];
  volume_number?: string;
  series_id?: string;
  destination_path?: string;
  priority?: number; // 1-10
  notify_on_completion?: boolean;
}

export interface DownloadJobResponse {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  download_type: string;
  manga_id: string;
  series_id?: string;
  batch_type?: string;
  volume_number?: string;
  destination_path?: string;
  // Manga metadata for better UI display
  manga_title?: string;
  manga_author?: string;
  manga_cover_url?: string;
  progress?: DownloadJobProgressInfo;
  priority: number;
  retry_count: number;
  max_retries: number;
  error_message?: string;
  scheduled_at: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DownloadJobListResponse {
  jobs: DownloadJobResponse[];
  total: number;
  active_downloads: number;
  pending_downloads: number;
  failed_downloads: number;
  completed_downloads: number;
  status_filter?: string;
  download_type_filter?: string;
  pagination?: {
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
    has_prev: boolean;
    has_next: boolean;
    prev_page?: number;
    next_page?: number;
  };
}

export interface DownloadJobActionRequest {
  action: 'cancel' | 'retry' | 'pause' | 'resume';
  reason?: string;
}

export interface DownloadJobActionResponse {
  job_id: string;
  action: string;
  success: boolean;
  message: string;
  new_status?: string;
}

export interface DownloadStatsResponse {
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
  current_download_speed_mbps?: number;
  total_downloaded_size_gb?: number;
  available_storage_gb?: number;
  stats_generated_at?: string;
}

export interface BulkDownloadRequest {
  downloads: DownloadJobRequest[];
  global_priority?: number;
  batch_name?: string;
  stagger_delay_seconds?: number;
}

export interface BulkDownloadResponse {
  batch_id: string;
  status: string;
  message: string;
  total_requested: number;
  successfully_queued: number;
  failed_to_queue: number;
  job_ids: string[];
  errors: string[];
}

export const downloadsApi = {
  async createDownloadJob(request: DownloadJobRequest): Promise<DownloadJobResponse> {
    const response = await api.post<DownloadJobResponse>('/api/downloads/', request);
    return response.data;
  },

  async getDownloadJobs(options?: {
    status?: string;
    download_type?: string;
    page?: number;
    per_page?: number;
  }): Promise<DownloadJobListResponse> {
    const params = new URLSearchParams();
    if (options?.status) params.append('status_filter', options.status);
    if (options?.download_type) params.append('download_type_filter', options.download_type);
    if (options?.page) params.append('page', options.page.toString());
    if (options?.per_page) params.append('per_page', options.per_page.toString());

    const response = await api.get<DownloadJobListResponse>(
      `/api/downloads/${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async getDownloadJob(jobId: string): Promise<DownloadJobResponse> {
    const response = await api.get<DownloadJobResponse>(`/api/downloads/${jobId}`);
    return response.data;
  },

  async performJobAction(jobId: string, action: DownloadJobActionRequest): Promise<DownloadJobActionResponse> {
    const response = await api.post<DownloadJobActionResponse>(
      `/api/downloads/${jobId}/actions`,
      action
    );
    return response.data;
  },

  async createBulkDownloads(request: BulkDownloadRequest): Promise<BulkDownloadResponse> {
    const response = await api.post<BulkDownloadResponse>('/api/downloads/bulk', request);
    return response.data;
  },

  async getDownloadStats(): Promise<DownloadStatsResponse> {
    const response = await api.get<DownloadStatsResponse>('/api/downloads/stats/overview');
    return response.data;
  },

  async deleteDownloadJob(jobId: string, force?: boolean): Promise<{ message: string }> {
    const params = new URLSearchParams();
    if (force) params.append('force', 'true');

    const response = await api.delete<{ message: string }>(
      `/api/downloads/${jobId}${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },
};

// MangaDx integration interfaces
export interface MangaDxSearchRequest {
  title?: string;
  author?: string;
  artist?: string;
  year?: number;
  status?: 'ongoing' | 'completed' | 'hiatus' | 'cancelled';
  content_rating?: string;
  limit?: number;
  offset?: number;
}

export interface MangaDxCoverArt {
  id: string;
  type: 'cover_art';
  attributes: {
    fileName: string;
    volume?: string;
    locale?: string;
  };
}

export interface MangaDxMangaInfo {
  id: string;
  title: string;
  alternative_titles: string[];
  description?: string;
  author?: string;
  artist?: string;
  genres: string[];
  tags: string[];
  status: 'ongoing' | 'completed' | 'hiatus' | 'cancelled';
  content_rating: 'safe' | 'suggestive' | 'erotica' | 'pornographic';
  original_language: string;
  publication_year?: number;
  last_volume?: string;
  last_chapter?: string;
  cover_art_url?: string;
  mangadx_created_at?: string;
  mangadx_updated_at?: string;
}

export interface MangaDxSearchResponse {
  results: MangaDxMangaInfo[];
  total: number;
  has_more: boolean;
}

export interface MangaDxImportRequest {
  mangadx_id: string;
  import_cover_art?: boolean;
  import_chapters?: boolean;
  overwrite_existing?: boolean;
}

export interface MangaDxImportResponse {
  status: 'success' | 'error';
  message: string;
  series_id?: string;
  series?: SeriesResponse;
  created: boolean;
  enriched: boolean;
}

export interface MangaDxEnrichmentCandidate {
  mangadx_id: string;
  manga_info: MangaDxMangaInfo;
  confidence_score: number;
  match_reasons: string[];
}

export interface MangaDxEnrichmentResponse {
  series_id: string;
  series_title: string;
  candidates: MangaDxEnrichmentCandidate[];
  message: string;
}

export interface MangaDxHealthResponse {
  status: 'healthy' | 'unhealthy';
  api_accessible: boolean;
  response_time_ms?: number;
  error_message?: string;
  last_checked: string;
}

export interface MangaDxDownloadRequest {
  manga_id: string;
  download_type: 'series' | 'volume' | 'chapter_range';
  volume_number?: string;
  chapter_range?: {
    start: string;
    end: string;
  };
  destination_path?: string;
  priority?: number;
}

export const mangadxApi = {
  async search(request: MangaDxSearchRequest): Promise<MangaDxSearchResponse> {
    const response = await api.post<MangaDxSearchResponse>('/api/mangadx/search', request);
    return response.data;
  },

  async getManga(mangaId: string): Promise<MangaDxMangaInfo> {
    const response = await api.get<MangaDxMangaInfo>(`/api/mangadx/manga/${mangaId}`);
    return response.data;
  },

  async importManga(request: MangaDxImportRequest): Promise<MangaDxImportResponse> {
    const response = await api.post<MangaDxImportResponse>('/api/mangadx/import', request);
    return response.data;
  },

  async enrichSeries(seriesId: string): Promise<MangaDxEnrichmentResponse> {
    const response = await api.post<MangaDxEnrichmentResponse>(`/api/mangadx/enrich/${seriesId}`);
    return response.data;
  },

  async checkHealth(): Promise<MangaDxHealthResponse> {
    const response = await api.get<MangaDxHealthResponse>('/api/mangadx/health');
    return response.data;
  },

  async createDownload(request: MangaDxDownloadRequest): Promise<DownloadJobResponse> {
    const response = await api.post<DownloadJobResponse>(
      `/api/mangadx/manga/${request.manga_id}/download`,
      request
    );
    return response.data;
  },
};

// Notification interfaces
export interface NotificationResponse {
  id: string;
  user_id?: string;
  type: 'new_chapter' | 'chapter_available' | 'download_complete' | 'download_failed' | 'series_complete' | 'library_update';
  title: string;
  message?: string;
  link?: string;
  is_read: boolean;
  data?: Record<string, any>;
  created_at: string;
  read_at?: string;
}

export interface NotificationCreateRequest {
  type: NotificationResponse['type'];
  title: string;
  message?: string;
  link?: string;
  data?: Record<string, any>;
}

export interface NotificationListResponse {
  notifications: NotificationResponse[];
  total: number;
  unread_count: number;
}

// Watching interfaces
export interface WatchingResponse {
  series_id: string;
  series_title: string;
  watching_enabled: boolean;
  last_watched_check?: string | null;
  message?: string;
}

export interface WatchingToggleRequest {
  enabled: boolean;
}

// Notification API functions
export const notificationsApi = {
  async getNotifications(options?: {
    limit?: number;
    offset?: number;
    unread_only?: boolean;
  }): Promise<NotificationResponse[]> {
    const params = new URLSearchParams();
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());
    if (options?.unread_only) params.append('unread_only', 'true');

    const response = await api.get<NotificationListResponse>(
      `/api/notifications/${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data.notifications;
  },

  async getNotification(notificationId: string): Promise<NotificationResponse> {
    const response = await api.get<NotificationResponse>(`/api/notifications/${notificationId}`);
    return response.data;
  },

  async markAsRead(notificationId: string): Promise<NotificationResponse> {
    const response = await api.put<NotificationResponse>(
      `/api/notifications/${notificationId}/mark-read`
    );
    return response.data;
  },

  async markAllAsRead(): Promise<{ marked_count: number }> {
    const response = await api.put<{ marked_count: number }>('/api/notifications/mark-all-read');
    return response.data;
  },

  async deleteNotification(notificationId: string): Promise<void> {
    await api.delete(`/api/notifications/${notificationId}`);
  },

  async deleteAllRead(): Promise<{ deleted_count: number }> {
    const response = await api.delete<{ deleted_count: number }>('/api/notifications/read');
    return response.data;
  },

  async getStats(): Promise<{ total: number; unread: number }> {
    const response = await api.get<{ total: number; unread: number }>('/api/notifications/stats');
    return response.data;
  },
};

// Watching API functions
export const watchingApi = {
  async getWatchingList(options?: {
    limit?: number;
    offset?: number;
  }): Promise<WatchingResponse[]> {
    const params = new URLSearchParams();
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());

    const response = await api.get<WatchingResponse[]>(
      `/api/watching${params.toString() ? `?${params.toString()}` : ''}`
    );
    return response.data;
  },

  async getWatchingStatus(seriesId: string): Promise<WatchingResponse> {
    const response = await api.get<WatchingResponse>(`/api/watching/${seriesId}`);
    return response.data;
  },

  async toggleWatch(seriesId: string, enabled: boolean): Promise<WatchingResponse> {
    const response = await api.post<{
      series_id: string;
      series_title: string;
      watching_enabled: boolean;
      last_watched_check?: string | null;
      message: string;
    }>(`/api/series/${seriesId}/watch`, {
      enabled
    });
    
    // Convert the response to WatchingResponse format
    return {
      series_id: response.data.series_id,
      series_title: response.data.series_title,
      watching_enabled: response.data.watching_enabled,
      last_watched_check: response.data.last_watched_check,
      message: response.data.message
    };
  },

  async watchSeries(seriesId: string): Promise<WatchingResponse> {
    const response = await api.post<WatchingResponse>(`/api/watching/${seriesId}`);
    return response.data;
  },

  async unwatchSeries(seriesId: string): Promise<void> {
    await api.delete(`/api/watching/${seriesId}`);
  },
};

export default api;
