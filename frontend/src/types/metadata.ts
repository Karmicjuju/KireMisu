import { z } from 'zod'

// Base interfaces for series and chapter metadata
export interface Series {
  id: number
  title: string
  description?: string
  author?: string
  artist?: string
  status?: 'ongoing' | 'completed' | 'hiatus' | 'cancelled'
  cover_path?: string
  metadata_json?: Record<string, any>
  created_at?: string
  updated_at?: string
  genres?: string[]
  tags?: string[]
}

export interface Chapter {
  id: number
  series_id: number
  number: number
  title?: string
  volume_number?: number
  description?: string
  release_date?: string
  page_count?: number
  file_path: string
  read_status: boolean
  created_at: string
  updated_at?: string
}

// Zod schemas for form validation
export const seriesEditSchema = z.object({
  title: z.string().min(1, 'Title is required').max(255, 'Title too long'),
  author: z.string().max(255, 'Author name too long').optional().or(z.literal('')),
  artist: z.string().max(255, 'Artist name too long').optional().or(z.literal('')),
  description: z.string().max(2000, 'Description too long').optional().or(z.literal('')),
  status: z.enum(['ongoing', 'completed', 'hiatus', 'cancelled']).optional(),
  cover_url: z.string().url('Invalid URL format').optional().or(z.literal('')),
  genres: z.array(z.string()).default([]),
  tags: z.array(z.string()).default([])
})

export const chapterEditSchema = z.object({
  number: z.number().min(0, 'Chapter number must be positive'),
  title: z.string().max(255, 'Title too long').optional().or(z.literal('')),
  volume_number: z.number().min(0, 'Volume number must be positive').optional(),
  description: z.string().max(1000, 'Description too long').optional().or(z.literal('')),
  release_date: z.string().optional().or(z.literal('')),
  page_count: z.number().min(1, 'Page count must be at least 1').optional()
})

export const bulkEditSchema = z.object({
  author: z.string().max(255, 'Author name too long').optional(),
  artist: z.string().max(255, 'Artist name too long').optional(),
  status: z.enum(['ongoing', 'completed', 'hiatus', 'cancelled']).optional(),
  genres: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  addGenres: z.array(z.string()).default([]),
  removeGenres: z.array(z.string()).default([]),
  addTags: z.array(z.string()).default([]),
  removeTags: z.array(z.string()).default([])
})

// Form types derived from schemas
export type SeriesEditFormData = z.infer<typeof seriesEditSchema>
export type ChapterEditFormData = z.infer<typeof chapterEditSchema>
export type BulkEditFormData = z.infer<typeof bulkEditSchema>

// History interfaces
export interface MetadataHistory {
  id: number
  timestamp: string
  field_name: string
  old_value: any
  new_value: any
  changed_by?: string
}

export interface SeriesHistory extends MetadataHistory {
  series_id: number
}

export interface ChapterHistory extends MetadataHistory {
  chapter_id: number
}

// API response interfaces
export interface SeriesUpdateResponse {
  success: boolean
  series: Series
  preview?: Series
}

export interface ChapterUpdateResponse {
  success: boolean
  chapter: Chapter
  preview?: Chapter
}

export interface BulkUpdateResponse {
  success: boolean
  updated_count: number
  failed_items?: Array<{
    id: number
    error: string
  }>
}

export interface HistoryResponse {
  history: MetadataHistory[]
  total_count: number
}

// Common genre and tag options for dropdowns
export const COMMON_GENRES = [
  'Action', 'Adventure', 'Comedy', 'Drama', 'Fantasy', 'Horror',
  'Mystery', 'Romance', 'Sci-Fi', 'Slice of Life', 'Sports', 'Supernatural',
  'Thriller', 'Historical', 'Psychological', 'Seinen', 'Shoujo', 'Shounen',
  'Josei', 'Yaoi', 'Yuri', 'Ecchi', 'Harem', 'Mecha', 'School', 'Military'
] as const

export const SERIES_STATUS_OPTIONS = [
  { value: 'ongoing', label: 'Ongoing' },
  { value: 'completed', label: 'Completed' },
  { value: 'hiatus', label: 'On Hiatus' },
  { value: 'cancelled', label: 'Cancelled' }
] as const

// Utility types for forms
export interface SelectOption {
  value: string
  label: string
}

export interface TagInput {
  id: string
  value: string
}