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

export default api;
