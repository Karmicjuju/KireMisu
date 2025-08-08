'use client';

import { useState, useCallback, useRef } from 'react';
import { 
  MangaDxSearchRequest,
  MangaDxSearchResponse,
  MangaDxMangaInfo,
  MangaDxImportRequest,
  MangaDxImportResponse,
  MangaDxDownloadRequest,
  DownloadJobResponse,
  mangadxApi 
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface UseMangaDxSearchOptions {
  enabled?: boolean;
}

interface UseMangaDxSearchReturn {
  results: MangaDxMangaInfo[];
  total: number;
  hasMore: boolean;
  loading: boolean;
  error: string | null;
  search: (request: MangaDxSearchRequest) => Promise<void>;
  clearResults: () => void;
}

export function useMangaDxSearch(options: UseMangaDxSearchOptions = {}): UseMangaDxSearchReturn {
  const [results, setResults] = useState<MangaDxMangaInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const { enabled = true } = options;
  const mountedRef = useRef(true);

  const search = useCallback(async (request: MangaDxSearchRequest) => {
    if (!enabled || !mountedRef.current) return;

    try {
      setLoading(true);
      setError(null);

      const response = await mangadxApi.search(request);

      if (!mountedRef.current) return;

      setResults(response.results);
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (err) {
      if (!mountedRef.current) return;
      const errorMessage = err instanceof Error ? err.message : 'Failed to search manga';
      setError(errorMessage);
      console.error('MangaDx search failed:', err);
      
      toast({
        title: 'Search Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled, toast]);

  const clearResults = useCallback(() => {
    setResults([]);
    setTotal(0);
    setHasMore(false);
    setError(null);
  }, []);

  return {
    results,
    total,
    hasMore,
    loading,
    error,
    search,
    clearResults,
  };
}

interface UseMangaDxImportOptions {
  onImportSuccess?: (response: MangaDxImportResponse) => void;
  onDownloadSuccess?: (response: DownloadJobResponse) => void;
}

interface UseMangaDxImportReturn {
  importLoading: boolean;
  downloadLoading: boolean;
  importManga: (request: MangaDxImportRequest) => Promise<MangaDxImportResponse | null>;
  createDownload: (request: MangaDxDownloadRequest) => Promise<DownloadJobResponse | null>;
}

export function useMangaDxImport(options: UseMangaDxImportOptions = {}): UseMangaDxImportReturn {
  const [importLoading, setImportLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const { toast } = useToast();

  const { onImportSuccess, onDownloadSuccess } = options;

  const importManga = useCallback(async (request: MangaDxImportRequest): Promise<MangaDxImportResponse | null> => {
    try {
      setImportLoading(true);

      const response = await mangadxApi.importManga(request);

      if (response.status === 'success') {
        toast({
          title: 'Import Successful',
          description: response.message,
        });
        onImportSuccess?.(response);
      } else {
        toast({
          title: 'Import Failed',
          description: response.message,
          variant: 'destructive',
        });
      }

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to import manga';
      toast({
        title: 'Import Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      console.error('MangaDx import failed:', err);
      return null;
    } finally {
      setImportLoading(false);
    }
  }, [toast, onImportSuccess]);

  const createDownload = useCallback(async (request: MangaDxDownloadRequest): Promise<DownloadJobResponse | null> => {
    try {
      setDownloadLoading(true);

      const response = await mangadxApi.createDownload(request);

      toast({
        title: 'Download Started',
        description: `Download job created successfully for ${request.download_type} download`,
      });
      onDownloadSuccess?.(response);

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create download';
      toast({
        title: 'Download Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      console.error('MangaDx download failed:', err);
      return null;
    } finally {
      setDownloadLoading(false);
    }
  }, [toast, onDownloadSuccess]);

  return {
    importLoading,
    downloadLoading,
    importManga,
    createDownload,
  };
}

interface UseMangaDxHealthReturn {
  health: {
    status: 'healthy' | 'unhealthy';
    apiAccessible: boolean;
    responseTimeMs?: number;
    errorMessage?: string;
    lastChecked: string;
  } | null;
  loading: boolean;
  checkHealth: () => Promise<void>;
}

export function useMangaDxHealth(): UseMangaDxHealthReturn {
  const [health, setHealth] = useState<UseMangaDxHealthReturn['health']>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = useCallback(async () => {
    try {
      setLoading(true);
      const response = await mangadxApi.checkHealth();
      setHealth({
        status: response.status,
        apiAccessible: response.api_accessible,
        responseTimeMs: response.response_time_ms,
        errorMessage: response.error_message,
        lastChecked: response.last_checked,
      });
    } catch (err) {
      console.error('Failed to check MangaDx health:', err);
      setHealth({
        status: 'unhealthy',
        apiAccessible: false,
        errorMessage: err instanceof Error ? err.message : 'Health check failed',
        lastChecked: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    health,
    loading,
    checkHealth,
  };
}