'use client';

import { useState } from 'react';
import { Download, Plus, TrendingUp, Activity, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { DownloadQueue } from '@/components/downloads';
import { MangaDxSearchDialog } from '@/components/mangadx';
import { useDownloads } from '@/hooks/use-downloads';
import { useDownloadStats } from '@/hooks/use-download-progress';
import { useToast } from '@/hooks/use-toast';

export default function Downloads() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showMangaDxDialog, setShowMangaDxDialog] = useState(false);
  const { toast } = useToast();
  
  const { 
    downloads, 
    stats, 
    loading, 
    refreshing,
    error, 
    refetch, 
    performAction, 
    deleteDownload,
  } = useDownloads({
    status: statusFilter === 'all' ? undefined : statusFilter,
    per_page: 50,
    // Polling settings are now automatically loaded from localStorage via usePollingSettings
  });

  const { stats: systemStats } = useDownloadStats({
    pollInterval: 60000, // 1 minute stats polling
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
    setShowMangaDxDialog(true);
  };

  const handleImportSuccess = () => {
    // Refresh downloads list when a manga is successfully imported
    refetch();
    toast({
      title: 'Import Successful',
      description: 'Manga has been imported. You can now download chapters.',
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
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refetch}
            disabled={refreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button 
            onClick={handleAddDownload}
            className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Download
          </Button>
        </div>
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
              <div className="flex-1">
                <div className="text-2xl font-bold">{systemStats.active_jobs}</div>
                <div className="text-xs text-muted-foreground">Active Downloads</div>
              </div>
              {systemStats.active_jobs > 0 && (
                <div className="text-xs text-green-600 font-medium">
                  Live
                </div>
              )}
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
                <div className="text-xs text-muted-foreground">Today&apos;s Chapters</div>
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
          refreshing={refreshing}
          onCancel={handleCancel}
          onRetry={handleRetry}
          onDelete={handleDelete}
          onRefresh={refetch}
          onClearCompleted={handleClearCompleted}
        />
      </div>

      {/* MangaDx Search Dialog */}
      <MangaDxSearchDialog
        open={showMangaDxDialog}
        onOpenChange={setShowMangaDxDialog}
        onImportSuccess={handleImportSuccess}
      />
    </div>
  );
}
