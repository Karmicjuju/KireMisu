// Filtering and Sorting Types

export interface FilterOptions {
  genres: string[]
  tags: string[]
  authors: string[]
  artists: string[]
  statuses: string[]
  demographics: string[]
  min_rating?: number
  max_rating?: number
  min_year?: number
  max_year?: number
}

export interface SeriesFilter {
  genres?: string[]
  tags?: string[]
  authors?: string[]
  artists?: string[]
  statuses?: string[]
  demographics?: string[]
  rating_range?: [number, number]
  year_range?: [number, number]
  date_added_range?: [string, string]
  last_read_range?: [string, string]
  read_status?: 'read' | 'unread' | 'reading'
  title_search?: string
  combination_logic?: 'AND' | 'OR'
}

export interface SortOption {
  field: 'title' | 'date_added' | 'last_read' | 'rating' | 'author' | 'year' | 'chapter_count'
  direction: 'asc' | 'desc'
}

export interface FilterPreset {
  id: number
  name: string
  description?: string
  filters: SeriesFilter
  sort_options?: SortOption[]
  is_default?: boolean
  created_at: string
  updated_at: string
}

export interface FilterPresetCreate {
  name: string
  description?: string
  filters: SeriesFilter
  sort_options?: SortOption[]
  is_default?: boolean
}

export interface FilterPresetUpdate {
  name?: string
  description?: string
  filters?: SeriesFilter
  sort_options?: SortOption[]
  is_default?: boolean
}

export interface FilteredSeriesResponse {
  series: any[]
  total_count: number
  filtered_count: number
  page: number
  page_size: number
  total_pages: number
}

// API Response Types for Library Path Management

export interface LibraryPathResponse {
  id: number
  name: string
  path: string
  is_active: boolean
  priority: number
  created_at: string
  updated_at: string
}

export interface LibraryPathCreate {
  name: string
  path: string
  is_active?: boolean
  priority?: number
}

export interface LibraryPathUpdate {
  name?: string
  is_active?: boolean
  priority?: number
}

export interface DirectoryItem {
  name: string
  path: string
  is_directory: boolean
  size?: number
  modified_at?: string
}

export interface DirectoryBrowseResponse {
  current_path: string
  parent_path?: string
  items: DirectoryItem[]
  total_items: number
}

export interface PathValidationResult {
  is_valid: boolean
  exists: boolean
  is_directory: boolean
  is_readable: boolean
  is_writable: boolean
  error_message?: string
  total_space?: number
  free_space?: number
}

export interface StorageInfo {
  total_space: number
  used_space: number
  free_space: number
  usage_percentage: number
}

// UI Types
export interface FileBrowserProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectPath: (path: string) => void
  initialPath?: string
}

export interface DirectoryTreeProps {
  items: DirectoryItem[]
  currentPath: string
  onNavigate: (path: string) => void
  onSelectPath: (path: string) => void
  selectedPath?: string
}