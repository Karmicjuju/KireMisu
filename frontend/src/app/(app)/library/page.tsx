'use client';

import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { GlassCard } from '@/components/ui/glass-card';
import { SeriesCard } from '@/components/library/series-card';
import { BookOpen, Grid3X3, List, Search, Filter, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { seriesApi, type SeriesResponse } from '@/lib/api';

export default function Library() {
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Fetch series list with SWR
  const {
    data: seriesList,
    error,
    isLoading: loading,
  } = useSWR<SeriesResponse[]>(
    ['series-list', searchTerm],
    () => seriesApi.getSeriesList({ search: searchTerm || undefined }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000, // 30 seconds
    }
  );

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Library</h1>
          <p className="text-slate-400">Browse and organize your manga collection</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant={viewMode === 'grid' ? 'outline' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid3X3 className="mr-2 h-4 w-4" />
            Grid
          </Button>
          <Button
            variant={viewMode === 'list' ? 'outline' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="mr-2 h-4 w-4" />
            List
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search your library..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
            className="border-slate-700/50 bg-slate-900/50 pl-10 focus:border-orange-500/50 focus:ring-orange-500/20"
          />
        </div>
        <Button variant="outline" className="flex-shrink-0">
          <Filter className="mr-2 h-4 w-4" />
          Filters
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-orange-500" />
            <p className="text-slate-400">Loading library...</p>
          </div>
        </div>
      ) : error ? (
        <GlassCard className="p-12 text-center">
          <BookOpen className="mx-auto mb-6 h-16 w-16 text-red-500" />
          <h2 className="mb-4 text-2xl font-semibold text-slate-300">Error loading library</h2>
          <p className="mx-auto mb-6 max-w-md text-slate-500">
            Failed to load your manga collection. Please check your connection and try again.
          </p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </GlassCard>
      ) : !seriesList || seriesList.length === 0 ? (
        /* Empty State */
        <GlassCard className="p-12 text-center">
          <BookOpen className="mx-auto mb-6 h-16 w-16 text-slate-500" />
          <h2 className="mb-4 text-2xl font-semibold text-slate-300">Your library is empty</h2>
          <p className="mx-auto mb-6 max-w-md text-slate-500">
            Add some library paths in Settings and scan your manga collection to get started. You
            can also discover new series from MangaDx.
          </p>
          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button
              asChild
              className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
            >
              <Link href="/settings">
                <BookOpen className="mr-2 h-4 w-4" />
                Go to Settings
              </Link>
            </Button>
            <Button variant="outline" disabled>
              <Search className="mr-2 h-4 w-4" />
              Discover Manga
            </Button>
          </div>
        </GlassCard>
      ) : (
        /* Series Grid/List */
        <div
          className={
            viewMode === 'grid'
              ? 'grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
              : 'space-y-4'
          }
        >
          {seriesList.map((series) => (
            <SeriesCard key={series.id} series={series} />
          ))}
        </div>
      )}
    </div>
  );
}
