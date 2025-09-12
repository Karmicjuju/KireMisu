import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { shallow } from 'zustand/shallow'
import type { 
  SeriesFilter, 
  SortOption, 
  FilterPreset, 
  FilterOptions,
  FilteredSeriesResponse 
} from './types'

export interface FilterState {
  // Current filter state
  activeFilters: SeriesFilter
  sortOptions: SortOption[]
  
  // Available options
  filterOptions: FilterOptions | null
  
  // UI state
  isFilterPanelOpen: boolean
  isLoading: boolean
  error: string | null
  
  // Filter presets
  presets: FilterPreset[]
  activePresetId: number | null
  
  // Filtered results
  filteredSeries: any[]
  totalCount: number
  filteredCount: number
  currentPage: number
  totalPages: number
  
  // Actions
  setActiveFilters: (filters: SeriesFilter) => void
  updateFilter: (key: keyof SeriesFilter, value: any) => void
  clearFilters: () => void
  setSortOptions: (options: SortOption[]) => void
  addSortOption: (option: SortOption) => void
  removeSortOption: (field: string) => void
  setFilterOptions: (options: FilterOptions) => void
  toggleFilterPanel: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setPresets: (presets: FilterPreset[]) => void
  setActivePreset: (presetId: number | null) => void
  loadPreset: (preset: FilterPreset) => void
  setFilteredResults: (results: FilteredSeriesResponse) => void
  setCurrentPage: (page: number) => void
  reset: () => void
}

const defaultFilters: SeriesFilter = {
  genres: [],
  tags: [],
  authors: [],
  artists: [],
  statuses: [],
  demographics: [],
  combination_logic: 'AND'
}

const defaultSortOptions: SortOption[] = [
  { field: 'title', direction: 'asc' }
]

export const useFilterStore = create<FilterState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        activeFilters: defaultFilters,
        sortOptions: defaultSortOptions,
        filterOptions: null,
        isFilterPanelOpen: false,
        isLoading: false,
        error: null,
        presets: [],
        activePresetId: null,
        filteredSeries: [],
        totalCount: 0,
        filteredCount: 0,
        currentPage: 1,
        totalPages: 1,
        
        // Actions
        setActiveFilters: (filters: SeriesFilter) => {
          set({ activeFilters: filters, activePresetId: null })
        },
        
        updateFilter: (key: keyof SeriesFilter, value: any) => {
          set(state => ({
            activeFilters: {
              ...state.activeFilters,
              [key]: value
            },
            activePresetId: null, // Clear active preset when manually updating filters
            currentPage: 1 // Reset to first page when filters change
          }))
        },
        
        clearFilters: () => {
          set({
            activeFilters: defaultFilters,
            activePresetId: null,
            currentPage: 1
          })
        },
        
        setSortOptions: (options: SortOption[]) => {
          set({ sortOptions: options, currentPage: 1 })
        },
        
        addSortOption: (option: SortOption) => {
          set(state => {
            // Remove existing sort for the same field
            const filtered = state.sortOptions.filter(opt => opt.field !== option.field)
            return {
              sortOptions: [...filtered, option],
              currentPage: 1
            }
          })
        },
        
        removeSortOption: (field: string) => {
          set(state => ({
            sortOptions: state.sortOptions.filter(opt => opt.field !== field),
            currentPage: 1
          }))
        },
        
        setFilterOptions: (options: FilterOptions) => {
          set({ filterOptions: options })
        },
        
        toggleFilterPanel: () => {
          set(state => ({ isFilterPanelOpen: !state.isFilterPanelOpen }))
        },
        
        setLoading: (loading: boolean) => {
          set({ isLoading: loading })
        },
        
        setError: (error: string | null) => {
          set({ error })
        },
        
        setPresets: (presets: FilterPreset[]) => {
          set({ presets })
        },
        
        setActivePreset: (presetId: number | null) => {
          set({ activePresetId: presetId })
        },
        
        loadPreset: (preset: FilterPreset) => {
          set({
            activeFilters: preset.filters,
            sortOptions: preset.sort_options || defaultSortOptions,
            activePresetId: preset.id,
            currentPage: 1
          })
        },
        
        setFilteredResults: (results: FilteredSeriesResponse) => {
          set({
            filteredSeries: results.series,
            totalCount: results.total_count,
            filteredCount: results.filtered_count,
            currentPage: results.page,
            totalPages: results.total_pages
          })
        },
        
        setCurrentPage: (page: number) => {
          set({ currentPage: page })
        },
        
        reset: () => {
          set({
            activeFilters: defaultFilters,
            sortOptions: defaultSortOptions,
            isFilterPanelOpen: false,
            isLoading: false,
            error: null,
            activePresetId: null,
            filteredSeries: [],
            totalCount: 0,
            filteredCount: 0,
            currentPage: 1,
            totalPages: 1
          })
        }
      }),
      {
        name: 'filter-store',
        partialize: (state) => ({
          // Only persist user preferences, not results or UI state
          activeFilters: state.activeFilters,
          sortOptions: state.sortOptions,
          isFilterPanelOpen: state.isFilterPanelOpen,
          activePresetId: state.activePresetId
        })
      }
    ),
    {
      name: 'filter-store'
    }
  )
)

// Convenience selectors
export const useActiveFilters = () => useFilterStore(state => state.activeFilters)
export const useSortOptions = () => useFilterStore(state => state.sortOptions)
export const useFilterPanel = () => useFilterStore(state => ({
  isOpen: state.isFilterPanelOpen,
  toggle: state.toggleFilterPanel
}), shallow)
// Commented out - causes infinite loop, use direct selectors instead
// export const useFilteredResults = () => useFilterStore(state => ({
//   series: state.filteredSeries,
//   totalCount: state.totalCount,
//   filteredCount: state.filteredCount,
//   currentPage: state.currentPage,
//   totalPages: state.totalPages
// }), shallow)

// Helper functions
export const hasActiveFilters = (filters: SeriesFilter): boolean => {
  return !!(
    filters.genres?.length ||
    filters.tags?.length ||
    filters.authors?.length ||
    filters.artists?.length ||
    filters.statuses?.length ||
    filters.demographics?.length ||
    filters.rating_range ||
    filters.year_range ||
    filters.date_added_range ||
    filters.last_read_range ||
    filters.read_status ||
    filters.title_search
  )
}

export const getFilterCount = (filters: SeriesFilter): number => {
  let count = 0
  if (filters.genres?.length) count++
  if (filters.tags?.length) count++
  if (filters.authors?.length) count++
  if (filters.artists?.length) count++
  if (filters.statuses?.length) count++
  if (filters.demographics?.length) count++
  if (filters.rating_range) count++
  if (filters.year_range) count++
  if (filters.date_added_range) count++
  if (filters.last_read_range) count++
  if (filters.read_status) count++
  if (filters.title_search) count++
  return count
}