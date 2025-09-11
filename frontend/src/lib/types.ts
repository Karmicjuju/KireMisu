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