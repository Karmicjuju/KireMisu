'use client';

import { useState } from 'react';
import { Download, Plus, TrendingUp, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { DownloadQueue } from '@/components/downloads';
import { useDownloads } from '@/hooks/use-downloads';
import { useDownloadStats } from '@/hooks/use-download-progress';
import { useToast } from '@/hooks/use-toast';

export default function Downloads() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const { toast } = useToast();
  
  const { 
    downloads, 
    stats, 
    loading, 
    error, 
    refetch, 
    performAction, 
    deleteDownload 
  } = useDownloads({
    status: statusFilter === 'all' ? undefined : statusFilter,
    per_page: 50,
    pollInterval: 3000, // Poll every 3 seconds
  });

  const { stats: systemStats } = useDownloadStats({
    pollInterval: 10000, // Poll every 10 seconds for system stats
  });

  const handleCancel = async (jobId: string) => {
    await performAction(jobId, { action: 'cancel' });
  };

  const handleRetry = async (jobId: string) => {
    await performAction(jobId, { action: 'retry' });
  };

  const handleDelete = async (jobId: string, force = false) => {
    await deleteDownload(jobId, force);
  };

  const handleClearCompleted = async () => {
    const completedDownloads = downloads.filter(d => d.status === 'completed');
    
    if (completedDownloads.length === 0) {
      toast({
        title: 'No completed downloads',
        description: 'There are no completed downloads to clear',
      });
      return;
    }

    try {
      for (const download of completedDownloads) {
        await deleteDownload(download.id, false);
      }
      toast({
        title: 'Cleared completed downloads',
        description: `Removed ${completedDownloads.length} completed downloads`,
      });
    } catch (error) {
      toast({
        title: 'Failed to clear downloads',
        description: 'Some downloads could not be removed',
        variant: 'destructive',
      });
    }
  };

  const handleAddDownload = () => {
    // TODO: Open download modal or navigate to MangaDx search
    toast({
      title: 'Add Download',
      description: 'Navigate to MangaDx search to find and download manga',
    });
  };

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Downloads</h1>
            <p className="text-muted-foreground">Manage your manga downloads and queue</p>
          </div>
        </div>

        <GlassCard className="p-8 text-center">
          <div className="text-destructive mb-4">
            <Activity className="mx-auto mb-2 h-12 w-12" />
            <h3 className="mb-2 text-lg font-medium">Failed to load downloads</h3>
            <p className="text-sm">{error}</p>
          </div>
          <Button onClick={refetch} variant="outline">
            Try Again
          </Button>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Downloads</h1>
          <p className="text-muted-foreground">Manage your manga downloads and queue</p>
        </div>
        <Button 
          onClick={handleAddDownload}
          className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
        >
          <Plus className="mr-2 h-4 w-4" />
          Add Download
        </Button>
      </div>

      {/* Statistics Cards */}
      {systemStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <GlassCard className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/20 rounded-lg">
                <Download className="h-4 w-4 text-primary" />
              </div>
              <div>
                <div className="text-2xl font-bold">{systemStats.total_jobs}</div>
                <div className="text-xs text-muted-foreground">Total Downloads</div>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-500/20 rounded-lg">
                <Activity className="h-4 w-4 text-orange-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">{systemStats.active_jobs}</div>
                <div className="text-xs text-muted-foreground">Active Downloads</div>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <TrendingUp className="h-4 w-4 text-green-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {systemStats.success_rate_percentage.toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground">Success Rate</div>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Download className="h-4 w-4 text-blue-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">{systemStats.chapters_downloaded_today}</div>
                <div className="text-xs text-muted-foreground">Today's Chapters</div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Download Queue */}
      <div>
        <DownloadQueue
          downloads={downloads}
          stats={stats}
          loading={loading}
          onCancel={handleCancel}
          onRetry={handleRetry}
          onDelete={handleDelete}
          onRefresh={refetch}
          onClearCompleted={handleClearCompleted}
        />
      </div>
    </div>
  );
}
