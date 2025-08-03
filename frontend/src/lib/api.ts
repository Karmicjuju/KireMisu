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

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
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

  async triggerScan(): Promise<{ message: string; paths_to_scan: number; status: string }> {
    const response = await api.post('/api/library/scan');
    return response.data;
  },
};

export default api;
