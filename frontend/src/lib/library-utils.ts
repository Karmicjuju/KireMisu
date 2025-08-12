/**
 * Library utility functions for filtering, sorting, and managing series data
 */

import { SeriesResponse } from './api';

// Type definitions
export interface FilterState {
  status: string[];
  genres: string[];
  recentlyAdded: string | null;
  authors: string[];
}

export interface SortState {
  field: 'title' | 'author' | 'updated_at' | 'created_at' | 'read_progress';
  direction: 'asc' | 'desc';
}

// Storage keys for localStorage
export const STORAGE_KEYS = {
  LIBRARY_FILTERS: 'kiremisu:library-filters',
  LIBRARY_SORT: 'kiremisu:library-sort',
  LIBRARY_VIEW_MODE: 'kiremisu:library-view-mode',
} as const;

// Default states
const DEFAULT_FILTERS: FilterState = {
  status: [],
  genres: [],
  recentlyAdded: null,
  authors: [],
};

const DEFAULT_SORT: SortState = {
  field: 'title',
  direction: 'asc',
};

/**
 * Filter and sort series based on current filter and sort state
 */
export function getFilteredAndSortedSeries(
  series: SeriesResponse[],
  filters: FilterState,
  sort: SortState
): SeriesResponse[] {
  let filtered = [...series];

  // Apply status filters
  if (filters.status.length > 0) {
    filtered = filtered.filter((s) => {
      const readStatus = getReadingStatus(s);
      return filters.status.includes(readStatus);
    });
  }

  // Apply genre filters
  if (filters.genres.length > 0) {
    filtered = filtered.filter((s) =>
      filters.genres.some((genre) => s.genres.includes(genre))
    );
  }

  // Apply author filters
  if (filters.authors.length > 0) {
    filtered = filtered.filter((s) =>
      s.author && filters.authors.includes(s.author)
    );
  }

  // Apply recently added filter
  if (filters.recentlyAdded) {
    const now = new Date();
    const cutoffDate = new Date();
    
    switch (filters.recentlyAdded) {
      case 'last-week':
        cutoffDate.setDate(now.getDate() - 7);
        break;
      case 'last-month':
        cutoffDate.setMonth(now.getMonth() - 1);
        break;
      case 'last-3-months':
        cutoffDate.setMonth(now.getMonth() - 3);
        break;
      default:
        break;
    }

    if (filters.recentlyAdded !== 'all') {
      filtered = filtered.filter((s) => new Date(s.created_at) >= cutoffDate);
    }
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let aValue: any;
    let bValue: any;

    switch (sort.field) {
      case 'title':
        aValue = a.title_primary.toLowerCase();
        bValue = b.title_primary.toLowerCase();
        break;
      case 'author':
        aValue = (a.author || '').toLowerCase();
        bValue = (b.author || '').toLowerCase();
        break;
      case 'updated_at':
        aValue = new Date(a.updated_at);
        bValue = new Date(b.updated_at);
        break;
      case 'created_at':
        aValue = new Date(a.created_at);
        bValue = new Date(b.created_at);
        break;
      case 'read_progress':
        aValue = a.total_chapters > 0 ? a.read_chapters / a.total_chapters : 0;
        bValue = b.total_chapters > 0 ? b.read_chapters / b.total_chapters : 0;
        break;
      default:
        return 0;
    }

    if (aValue < bValue) {
      return sort.direction === 'asc' ? -1 : 1;
    }
    if (aValue > bValue) {
      return sort.direction === 'asc' ? 1 : -1;
    }
    return 0;
  });

  return filtered;
}

/**
 * Get unique genres from series list
 */
export function getAvailableGenres(series: SeriesResponse[]): string[] {
  const genreSet = new Set<string>();
  series.forEach((s) => {
    s.genres.forEach((genre) => genreSet.add(genre));
  });
  return Array.from(genreSet).sort();
}

/**
 * Get unique authors from series list
 */
export function getAvailableAuthors(series: SeriesResponse[]): string[] {
  const authorSet = new Set<string>();
  series.forEach((s) => {
    if (s.author) {
      authorSet.add(s.author);
    }
  });
  return Array.from(authorSet).sort();
}

/**
 * Get reading status for a series
 */
export function getReadingStatus(series: SeriesResponse): string {
  if (series.read_chapters === 0) {
    return 'unread';
  }
  if (series.read_chapters >= series.total_chapters && series.total_chapters > 0) {
    return 'completed';
  }
  return 'in-progress';
}

/**
 * Calculate reading progress percentage
 */
export function getReadingProgress(series: SeriesResponse): number {
  if (series.total_chapters === 0) return 0;
  return Math.round((series.read_chapters / series.total_chapters) * 100);
}

// localStorage utility functions

/**
 * Load filters from localStorage
 */
export function loadFiltersFromStorage(): FilterState {
  if (typeof window === 'undefined') return DEFAULT_FILTERS;
  
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.LIBRARY_FILTERS);
    if (stored) {
      return { ...DEFAULT_FILTERS, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.warn('Failed to load filters from storage:', error);
  }
  
  return DEFAULT_FILTERS;
}

/**
 * Save filters to localStorage
 */
export function saveFiltersToStorage(filters: FilterState): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem(STORAGE_KEYS.LIBRARY_FILTERS, JSON.stringify(filters));
  } catch (error) {
    console.warn('Failed to save filters to storage:', error);
  }
}

/**
 * Load sort state from localStorage
 */
export function loadSortFromStorage(): SortState {
  if (typeof window === 'undefined') return DEFAULT_SORT;
  
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.LIBRARY_SORT);
    if (stored) {
      return { ...DEFAULT_SORT, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.warn('Failed to load sort from storage:', error);
  }
  
  return DEFAULT_SORT;
}

/**
 * Save sort state to localStorage
 */
export function saveSortToStorage(sort: SortState): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem(STORAGE_KEYS.LIBRARY_SORT, JSON.stringify(sort));
  } catch (error) {
    console.warn('Failed to save sort to storage:', error);
  }
}

/**
 * Save view mode to localStorage
 */
export function saveViewModeToStorage(viewMode: 'grid' | 'list'): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem(STORAGE_KEYS.LIBRARY_VIEW_MODE, viewMode);
  } catch (error) {
    console.warn('Failed to save view mode to storage:', error);
  }
}

/**
 * Load view mode from localStorage
 */
export function loadViewModeFromStorage(): 'grid' | 'list' {
  if (typeof window === 'undefined') return 'grid';
  
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.LIBRARY_VIEW_MODE);
    if (stored === 'grid' || stored === 'list') {
      return stored;
    }
  } catch (error) {
    console.warn('Failed to load view mode from storage:', error);
  }
  
  return 'grid';
}

/**
 * Clear all library preferences from localStorage
 */
export function clearLibraryPreferences(): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.removeItem(STORAGE_KEYS.LIBRARY_FILTERS);
    localStorage.removeItem(STORAGE_KEYS.LIBRARY_SORT);
    localStorage.removeItem(STORAGE_KEYS.LIBRARY_VIEW_MODE);
  } catch (error) {
    console.warn('Failed to clear library preferences:', error);
  }
}