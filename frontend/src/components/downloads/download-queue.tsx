'use client';

import React from 'react';
import { 
  Filter, 
  Download, 
  RefreshCw, 
  Trash2, 
  Search,
  AlertCircle,
  CheckCircle,
  Clock,
  Play,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { DownloadItem } from './download-item';
import { DownloadJobResponse } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DownloadQueueStats {
  total: number;
  active_downloads: number;
  pending_downloads: number;
  failed_downloads: number;
  completed_downloads: number;
}

interface DownloadQueueProps {
  downloads: DownloadJobResponse[];
  stats: DownloadQueueStats;
  loading: boolean;
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onDelete: (jobId: string) => Promise<void>;
  onRefresh: () => Promise<void>;
  onClearCompleted: () => Promise<void>;
  className?: string;
}

export function DownloadQueue({
  downloads,
  stats,
  loading,
  onCancel,
  onRetry,
  onDelete,
  onRefresh,
  onClearCompleted,
  className
}: DownloadQueueProps) {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedStatus, setSelectedStatus] = React.useState('all');
  const [selectedType, setSelectedType] = React.useState('all');

  // Filter downloads based on search and filters
  const filteredDownloads = React.useMemo(() => {
    return downloads.filter(download => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesTitle = download.manga_title?.toLowerCase().includes(query);
        const matchesAuthor = download.manga_author?.toLowerCase().includes(query);
        const matchesId = download.id.toLowerCase().includes(query);
        
        if (!matchesTitle && !matchesAuthor && !matchesId) {
          return false;
        }
      }

      // Status filter
      if (selectedStatus !== 'all' && download.status !== selectedStatus) {
        return false;
      }

      // Type filter
      if (selectedType !== 'all' && download.download_type !== selectedType) {
        return false;
      }

      return true;
    });
  }, [downloads, searchQuery, selectedStatus, selectedType]);

  // Get unique download types for filter
  const downloadTypes = React.useMemo(() => {
    const types = [...new Set(downloads.map(d => d.download_type))];
    return types.sort();
  }, [downloads]);

  // Status tabs with counts
  const statusTabs = [
    { value: 'all', label: 'All', count: stats.total, icon: Download },
    { value: 'running', label: 'Active', count: stats.active_downloads, icon: Play },
    { value: 'pending', label: 'Pending', count: stats.pending_downloads, icon: Clock },
    { value: 'completed', label: 'Completed', count: stats.completed_downloads, icon: CheckCircle },
    { value: 'failed', label: 'Failed', count: stats.failed_downloads, icon: AlertCircle },
  ];

  const handleStatusChange = (status: string) => {
    setSelectedStatus(status);
  };

  const handleClearCompleted = async () => {
    if (stats.completed_downloads === 0) return;
    
    if (window.confirm(`Remove all ${stats.completed_downloads} completed downloads?`)) {
      await onClearCompleted();
    }
  };

  // Empty state component
  const EmptyState = ({ status }: { status: string }) => {
    const getEmptyStateContent = () => {
      switch (status) {
        case 'running':
          return {
            icon: Play,
            title: 'No active downloads',
            description: 'All downloads are either pending, completed, or failed.',
          };
        case 'pending':
          return {
            icon: Clock,
            title: 'No pending downloads',
            description: 'All downloads have either started, completed, or failed.',
          };
        case 'completed':
          return {
            icon: CheckCircle,
            title: 'No completed downloads',
            description: 'Downloads will appear here once they finish successfully.',
          };
        case 'failed':
          return {
            icon: AlertCircle,
            title: 'No failed downloads',
            description: 'Failed downloads will appear here for retry or removal.',
          };
        default:
          return {
            icon: Download,
            title: 'No downloads yet',
            description: 'Start downloading manga chapters to see them here.',
          };
      }
    };

    const { icon: Icon, title, description } = getEmptyStateContent();

    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="p-4 bg-white/5 rounded-full mb-4">
          <Icon className="h-8 w-8 text-white/40" />
        </div>
        <h3 className="text-lg font-medium text-white/80 mb-2">{title}</h3>
        <p className="text-sm text-white/60 max-w-md">{description}</p>
      </div>
    );
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Controls Section */}
      <GlassCard className="p-6">
        <div className="space-y-4">
          {/* Search and Filters Row */}
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-white/40" />
                <Input
                  placeholder="Search by title, author, or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Type Filter */}
            <div className="lg:w-48">
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {downloadTypes.map(type => (
                    <SelectItem key={type} value={type}>
                      {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={loading}
                className="flex items-center gap-2"
              >
                <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                Refresh
              </Button>

              {stats.completed_downloads > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearCompleted}
                  className="flex items-center gap-2 hover:bg-red-500/20 hover:border-red-500/30"
                >
                  <Trash2 className="h-4 w-4" />
                  Clear Completed ({stats.completed_downloads})
                </Button>
              )}
            </div>
          </div>

          {/* Status Tabs */}
          <Tabs value={selectedStatus} onValueChange={handleStatusChange} className="w-full">
            <TabsList className="grid w-full grid-cols-5 h-auto p-1">
              {statusTabs.map(({ value, label, count, icon: Icon }) => (
                <TabsTrigger
                  key={value}
                  value={value}
                  className="flex flex-col items-center gap-1 py-3 data-[state=active]:bg-white/20"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    <span className="hidden sm:inline">{label}</span>
                  </div>
                  <Badge 
                    variant={value === selectedStatus ? "default" : "secondary"}
                    className="text-xs px-1.5 py-0.5 min-w-[1.5rem] h-5"
                  >
                    {count}
                  </Badge>
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          {/* Active Filters Summary */}
          {(searchQuery || selectedType !== 'all') && (
            <div className="flex flex-wrap items-center gap-2 text-sm text-white/70">
              <span>Filters:</span>
              {searchQuery && (
                <Badge variant="outline" className="text-xs">
                  Search: "{searchQuery}"
                  <button
                    onClick={() => setSearchQuery('')}
                    className="ml-1 hover:text-white"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
              {selectedType !== 'all' && (
                <Badge variant="outline" className="text-xs">
                  Type: {selectedType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  <button
                    onClick={() => setSelectedType('all')}
                    className="ml-1 hover:text-white"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
              <span className="text-white/50">({filteredDownloads.length} results)</span>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Downloads List */}
      <div className="space-y-4">
        {loading && downloads.length === 0 ? (
          // Loading state
          <GlassCard className="p-12 text-center">
            <div className="flex items-center justify-center gap-3 text-white/60">
              <RefreshCw className="h-5 w-5 animate-spin" />
              <span>Loading downloads...</span>
            </div>
          </GlassCard>
        ) : filteredDownloads.length === 0 ? (
          // Empty state
          <GlassCard>
            <EmptyState status={selectedStatus} />
          </GlassCard>
        ) : (
          // Downloads list
          filteredDownloads.map((download) => (
            <DownloadItem
              key={download.id}
              download={download}
              onCancel={onCancel}
              onRetry={onRetry}
              onDelete={onDelete}
            />
          ))
        )}
      </div>

      {/* Results Summary */}
      {filteredDownloads.length > 0 && (
        <div className="text-center text-sm text-white/60">
          Showing {filteredDownloads.length} of {downloads.length} downloads
        </div>
      )}
    </div>
  );
}