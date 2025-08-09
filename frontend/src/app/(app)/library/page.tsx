'use client';

import { useState, useEffect, useMemo } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { GlassCard } from '@/components/ui/glass-card';
import { SeriesCard } from '@/components/library/series-card';
import { QuickActions } from '@/components/library/quick-actions';
import { LibraryStats } from '@/components/library/library-stats';
import { FilterDropdown } from '@/components/library/filter-dropdown';
import { SortDropdown } from '@/components/library/sort-dropdown';
import { Button } from '@/components/ui/button';
import { 
  BookOpen, 
  Grid3X3, 
  List, 
  Loader2
} from 'lucide-react';
import { seriesApi, type SeriesResponse } from '@/lib/api';
import { 
  FilterState, 
  SortState,
  getFilteredAndSortedSeries,
  getAvailableGenres,
  getAvailableAuthors,
  loadFiltersFromStorage,
  saveFiltersToStorage,
  loadSortFromStorage,
  saveSortToStorage,
  saveViewModeToStorage,
  STORAGE_KEYS
} from '@/lib/library-utils';

export default function Library() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<FilterState>({
    status: [],
    genres: [],
    recentlyAdded: null,
    authors: [],
  });
  const [sort, setSort] = useState<SortState>({
    field: 'title',
    direction: 'asc',
  });
  const [isClient, setIsClient] = useState(false);

  // Load preferences from localStorage on client
  useEffect(() => {
    setIsClient(true);
    setFilters(loadFiltersFromStorage());
    setSort(loadSortFromStorage());
    
    const savedViewMode = localStorage.getItem(STORAGE_KEYS.LIBRARY_VIEW_MODE) as 'grid' | 'list';
    if (savedViewMode) {
      setViewMode(savedViewMode);
    }
  }, []);

  // Save preferences to localStorage when they change
  useEffect(() => {
    if (isClient) {
      saveFiltersToStorage(filters);
    }
  }, [filters, isClient]);

  useEffect(() => {
    if (isClient) {
      saveSortToStorage(sort);
    }
  }, [sort, isClient]);

  useEffect(() => {
    if (isClient) {
      saveViewModeToStorage(viewMode);
    }
  }, [viewMode, isClient]);

  // Fetch series list with SWR
  const {
    data: seriesList,
    error,
    isLoading: loading,
  } = useSWR<SeriesResponse[]>(
    'series-list',
    () => seriesApi.getSeriesList(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000, // 30 seconds
    }
  );

  // Get available filter options from the data
  const availableGenres = useMemo(() => {
    return seriesList ? getAvailableGenres(seriesList) : [];
  }, [seriesList]);

  const availableAuthors = useMemo(() => {
    return seriesList ? getAvailableAuthors(seriesList) : [];
  }, [seriesList]);

  // Apply filters and sorting
  const processedSeriesList = useMemo(() => {
    if (!seriesList) return [];
    return getFilteredAndSortedSeries(seriesList, filters, sort);
  }, [seriesList, filters, sort]);

  // Calculate stats for the original library (before filtering)
  const stats = seriesList ? {
    total: seriesList.length,
    unread: seriesList.filter(s => s.read_chapters === 0).length,
    inProgress: seriesList.filter(s => s.read_chapters > 0 && s.read_chapters < s.total_chapters).length,
    completed: seriesList.filter(s => s.read_chapters === s.total_chapters && s.total_chapters > 0).length,
  } : { total: 0, unread: 0, inProgress: 0, completed: 0 };

  // Calculate filtered stats for display
  const filteredStats = {
    showing: processedSeriesList.length,
    total: seriesList?.length || 0,
  };

  const handleFiltersChange = (newFilters: FilterState) => {
    setFilters(newFilters);
  };

  const handleSortChange = (newSort: SortState) => {
    setSort(newSort);
  };

  return (
    <div className="space-y-6">
      {/* Header with Quick Actions */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          {/* Title */}
          <div>
            <h1 className="text-3xl font-bold">Library</h1>
            <p className="text-muted-foreground">Browse and manage your manga collection</p>
          </div>
          
          {/* Quick Actions */}
          <div className="sm:ml-4">
            <QuickActions />
          </div>
        </div>

        {/* Compact Stats */}
        <LibraryStats />
      </div>

      {/* Collection Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <BookOpen className="h-4 w-4" />
          <span>
            {filteredStats.showing === filteredStats.total 
              ? `${stats.total} series` 
              : `${filteredStats.showing} of ${filteredStats.total} series`
            } • {stats.inProgress} in progress • {stats.completed} completed
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid3X3 className="mr-2 h-4 w-4" />
            Grid
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="mr-2 h-4 w-4" />
            List
          </Button>
          <FilterDropdown 
            filters={filters}
            onFiltersChange={handleFiltersChange}
            availableGenres={availableGenres}
            availableAuthors={availableAuthors}
          />
          <SortDropdown 
            sort={sort}
            onSortChange={handleSortChange}
          />
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading your collection...</p>
          </div>
        </div>
      ) : error ? (
        <GlassCard className="p-12 text-center">
          <BookOpen className="mx-auto mb-6 h-16 w-16 text-destructive" />
          <h3 className="mb-4 text-xl font-semibold">Error loading collection</h3>
          <p className="mx-auto mb-6 max-w-md text-muted-foreground">
            Failed to load your manga collection. Please check your connection and try again.
          </p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </GlassCard>
      ) : !seriesList || seriesList.length === 0 ? (
        /* Empty State */
        <GlassCard className="p-12 text-center">
          <BookOpen className="mx-auto mb-6 h-16 w-16 text-muted-foreground" />
          <h3 className="mb-4 text-xl font-semibold">Your collection is empty</h3>
          <p className="mx-auto mb-6 max-w-md text-muted-foreground">
            Add some library paths in Settings and scan your manga collection to get started. 
            You can also discover new manga using the Discover button above.
          </p>
          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
              <Link href="/settings">
                <BookOpen className="mr-2 h-4 w-4" />
                Configure Library Paths
              </Link>
            </Button>
          </div>
        </GlassCard>
      ) : processedSeriesList.length === 0 ? (
        /* No results after filtering */
        <GlassCard className="p-12 text-center">
          <BookOpen className="mx-auto mb-6 h-16 w-16 text-muted-foreground" />
          <h3 className="mb-4 text-xl font-semibold">No series match your filters</h3>
          <p className="mx-auto mb-6 max-w-md text-muted-foreground">
            Try adjusting your filters or search criteria. You have {seriesList.length} series in your library.
          </p>
          <Button 
            onClick={() => setFilters({ status: [], genres: [], recentlyAdded: null, authors: [] })}
            className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600"
          >
            Clear All Filters
          </Button>
        </GlassCard>
      ) : (
        /* Series Grid/List */
        <div
          className={
            viewMode === 'grid'
              ? 'grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6'
              : 'space-y-2'
          }
        >
          {processedSeriesList.map((series) => (
            <SeriesCard 
              key={series.id} 
              series={series} 
              viewMode={viewMode}
            />
          ))}
        </div>
      )}
    </div>
  );
}