'use client';

import React, { useState } from 'react';
import { Plus, Trash2, Folder, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import {
  libraryApi,
  jobsApi,
  type LibraryPath,
  type LibraryScanResponse,
  type JobResponse,
} from '@/lib/api';
import { formatRelativeTime } from '@/lib/utils';
import { LibraryPathStatusIndicator } from '@/components/ui/job-status-badge';
import useSWR, { mutate } from 'swr';

interface LibraryPathFormData {
  path: string;
  enabled: boolean;
  scan_interval_hours: number;
}

const SCAN_INTERVAL_OPTIONS = [
  { value: 1, label: '1 hour' },
  { value: 2, label: '2 hours' },
  { value: 6, label: '6 hours' },
  { value: 12, label: '12 hours' },
  { value: 24, label: '24 hours' },
  { value: 48, label: '48 hours' },
  { value: 168, label: '1 week' },
];

export function LibraryPaths() {
  const { toast } = useToast();
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isScanningAll, setIsScanningAll] = useState(false);
  const [scanningPathId, setScanningPathId] = useState<string | null>(null);
  const [formData, setFormData] = useState<LibraryPathFormData>({
    path: '',
    enabled: true,
    scan_interval_hours: 24,
  });

  const { data: pathsData, error, isLoading } = useSWR('library-paths', libraryApi.getPaths);
  const { data: recentJobs } = useSWR(
    'recent-jobs',
    () => jobsApi.getRecentJobs('library_scan', 20),
    {
      refreshInterval: 10000, // Poll every 10 seconds for library path updates
    }
  );

  // Helper functions for job status
  const getPathJobStatus = (pathId: string) => {
    if (!recentJobs?.jobs) return { isScanning: false, hasError: false, lastJob: null };

    // Find the most recent job for this path
    const pathJobs = recentJobs.jobs.filter(
      (job) =>
        job.payload.library_path_id === pathId ||
        (job.payload.library_path_id === null && job.job_type === 'library_scan')
    );

    if (pathJobs.length === 0) return { isScanning: false, hasError: false, lastJob: null };

    const lastJob = pathJobs[0]; // Most recent job
    const isScanning = lastJob.status === 'running' || lastJob.status === 'pending';
    const hasError = lastJob.status === 'failed';

    return { isScanning, hasError, lastJob };
  };

  const getGlobalScanStatus = () => {
    if (!recentJobs?.jobs) return { isScanning: false, hasError: false };

    const runningJobs = recentJobs.jobs.filter(
      (job) => job.status === 'running' && job.job_type === 'library_scan'
    );
    const failedJobs = recentJobs.jobs.filter(
      (job) => job.status === 'failed' && job.job_type === 'library_scan'
    );

    return {
      isScanning: runningJobs.length > 0,
      hasError: failedJobs.length > 0 && runningJobs.length === 0,
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingId) {
        await libraryApi.updatePath(editingId, formData);
        toast({
          title: 'Path updated',
          description: 'Library path has been updated successfully.',
        });
        setEditingId(null);
      } else {
        await libraryApi.createPath(formData);
        toast({
          title: 'Path added',
          description: 'Library path has been added successfully.',
        });
        setIsAdding(false);
      }

      setFormData({ path: '', enabled: true, scan_interval_hours: 24 });
      mutate('library-paths');
    } catch (error: any) {
      const errorMessage =
        typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : error.response?.data?.detail?.[0]?.msg || 'Failed to save library path.';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const handleEdit = (path: LibraryPath) => {
    setFormData({
      path: path.path,
      enabled: path.enabled,
      scan_interval_hours: path.scan_interval_hours,
    });
    setEditingId(path.id);
    setIsAdding(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this library path?')) {
      return;
    }

    try {
      await libraryApi.deletePath(id);
      toast({
        title: 'Path deleted',
        description: 'Library path has been deleted successfully.',
      });
      mutate('library-paths');
    } catch (error: any) {
      const errorMessage =
        typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : error.response?.data?.detail?.[0]?.msg || 'Failed to delete library path.';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const formatScanResults = (stats: LibraryScanResponse['stats']): string => {
    const { series_found, chapters_found } = stats;
    return `Found ${series_found} series with ${chapters_found} chapters`;
  };

  const handleScanAll = async () => {
    setIsScanningAll(true);
    try {
      const result = await jobsApi.scheduleJob({
        job_type: 'library_scan',
        priority: 8, // High priority for manual scans
      });
      toast({
        title: 'Library scan scheduled',
        description: result.message,
      });
      // Refresh the job data to see the new job
      mutate('recent-jobs');
      mutate('library-paths');
    } catch (error: any) {
      const errorMessage =
        typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : error.response?.data?.detail?.[0]?.msg || 'Failed to schedule library scan.';
      toast({
        title: 'Library scan failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsScanningAll(false);
    }
  };

  const handleScanPath = async (pathId: string) => {
    setScanningPathId(pathId);
    try {
      const result = await jobsApi.scheduleJob({
        job_type: 'library_scan',
        library_path_id: pathId,
        priority: 8, // High priority for manual scans
      });
      toast({
        title: 'Library scan scheduled',
        description: result.message,
      });
      // Refresh the job data to see the new job
      mutate('recent-jobs');
      mutate('library-paths');
    } catch (error: any) {
      const errorMessage =
        typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : error.response?.data?.detail?.[0]?.msg || 'Failed to schedule library scan.';
      toast({
        title: 'Library scan failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setScanningPathId(null);
    }
  };

  const handleCancel = () => {
    setIsAdding(false);
    setEditingId(null);
    setFormData({ path: '', enabled: true, scan_interval_hours: 24 });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Library Paths</h2>
          <div className="mt-1">
            <LibraryPathStatusIndicator {...getGlobalScanStatus()} />
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleScanAll}
            variant="secondary"
            size="sm"
            disabled={isScanningAll || scanningPathId !== null || getGlobalScanStatus().isScanning}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isScanningAll || getGlobalScanStatus().isScanning ? 'animate-spin' : ''}`}
            />
            {isScanningAll || getGlobalScanStatus().isScanning
              ? 'Scanning...'
              : 'Scan All Libraries'}
          </Button>
          {!isAdding && (
            <Button onClick={() => setIsAdding(true)} size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Path
            </Button>
          )}
        </div>
      </div>

      {error && pathsData?.paths?.length && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
          <div className="text-destructive">
            Some library paths may not be displaying correctly.
          </div>
        </div>
      )}

      {isAdding && (
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
          <h3 className="text-lg font-semibold">
            {editingId ? 'Edit Library Path' : 'Add New Library Path'}
          </h3>

          <div className="space-y-2">
            <label htmlFor="path" className="text-sm font-medium">
              Directory Path
            </label>
            <div className="flex gap-2">
              <Input
                id="path"
                type="text"
                placeholder="/path/to/manga/library"
                value={formData.path}
                onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                required
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => {
                  // Note: In a real implementation, you'd use the File System Access API
                  // or electron dialog for directory picking
                  const path = prompt('Enter directory path:');
                  if (path) {
                    setFormData({ ...formData, path });
                  }
                }}
              >
                <Folder className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="enabled"
              checked={formData.enabled}
              onCheckedChange={(checked) => setFormData({ ...formData, enabled: checked })}
            />
            <label htmlFor="enabled" className="text-sm font-medium">
              Enable automatic scanning
            </label>
          </div>

          <div className="space-y-2">
            <label htmlFor="interval" className="text-sm font-medium">
              Scan Interval
            </label>
            <Select
              value={formData.scan_interval_hours.toString()}
              onValueChange={(value) =>
                setFormData({ ...formData, scan_interval_hours: parseInt(value) })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCAN_INTERVAL_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value.toString()}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            <Button type="submit">{editingId ? 'Update Path' : 'Add Path'}</Button>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {isLoading ? (
          <div>Loading library paths...</div>
        ) : !pathsData?.paths?.length ? (
          <div className="py-8 text-center text-muted-foreground">
            No library paths configured. Add a path to get started.
          </div>
        ) : (
          pathsData.paths.map((path) => {
            const jobStatus = getPathJobStatus(path.id);
            const isPathScanning = jobStatus.isScanning || scanningPathId === path.id;

            return (
              <div
                key={path.id}
                className="flex items-center justify-between rounded-lg border bg-card p-4"
              >
                <div className="flex-1">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <div className="font-medium text-foreground">{path.path}</div>
                      <LibraryPathStatusIndicator
                        isScanning={isPathScanning}
                        hasError={jobStatus.hasError}
                      />
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Scan interval:{' '}
                      {
                        SCAN_INTERVAL_OPTIONS.find((o) => o.value === path.scan_interval_hours)
                          ?.label
                      }
                      {path.last_scan && ` • Last scan: ${formatRelativeTime(path.last_scan)}`}
                      {jobStatus.lastJob && jobStatus.lastJob.error_message && (
                        <span className="ml-2 text-destructive">
                          • Error: {jobStatus.lastJob.error_message}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {path.enabled ? 'Auto-scan Enabled' : 'Auto-scan Disabled'}
                    </span>
                    <div
                      className={`h-2 w-2 rounded-full ${path.enabled ? 'bg-green-500' : 'bg-muted-foreground'}`}
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleScanPath(path.id)}
                      disabled={
                        isScanningAll ||
                        scanningPathId !== null ||
                        isPathScanning ||
                        getGlobalScanStatus().isScanning
                      }
                    >
                      <RefreshCw
                        className={`mr-2 h-4 w-4 ${isPathScanning ? 'animate-spin' : ''}`}
                      />
                      {isPathScanning ? 'Scanning...' : 'Scan'}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(path)}>
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(path.id)}
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
