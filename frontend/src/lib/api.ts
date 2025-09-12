import type { 
  LibraryPathResponse, 
  LibraryPathCreate, 
  LibraryPathUpdate, 
  PathValidationResult, 
  StorageInfo, 
  DirectoryBrowseResponse,
  FilterOptions,
  SeriesFilter,
  SortOption,
  FilterPreset,
  FilterPresetCreate,
  FilterPresetUpdate,
  FilteredSeriesResponse
} from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

// CSRF Token Management
let csrfToken: string | null = null

async function getCSRFToken(): Promise<string> {
  if (!csrfToken) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/csrf-token`, {
        method: 'GET',
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        csrfToken = data.csrf_token
      } else {
        throw new Error('Failed to get CSRF token')
      }
    } catch (error) {
      console.error('Failed to get CSRF token:', error)
      // Fallback: generate a token locally (not ideal but prevents blocking)
      const array = new Uint8Array(32)
      crypto.getRandomValues(array)
      csrfToken = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
    }
  }
  return csrfToken
}

function isStateChangingMethod(method: string): boolean {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<any> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  
  // Add CSRF token for state-changing operations
  const method = options.method || 'GET'
  if (typeof window !== 'undefined' && isStateChangingMethod(method)) {
    headers['X-CSRF-Token'] = await getCSRFToken()
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
      credentials: 'include', // Include cookies in requests
      // Add timeout and signal handling for better error management
      signal: options.signal,
    })
    
    // Handle 401 responses - don't auto-redirect, let components handle it
    if (response.status === 401) {
      throw new ApiError('Authentication required', 401)
    }
    
    if (!response.ok) {
      let errorData
      try {
        errorData = await response.json()
      } catch {
        errorData = { detail: `HTTP ${response.status}: ${response.statusText}` }
      }
      throw new ApiError(errorData.detail || 'Request failed', response.status)
    }
    
    // Handle empty responses (like 204 No Content)
    const contentType = response.headers.get('content-type')
    if (!contentType || !contentType.includes('application/json')) {
      return {}
    }
    
    return await response.json()
  } catch (error) {
    // Handle network errors, SSL issues, etc.
    if (error instanceof ApiError) {
      throw error
    }
    
    // Handle fetch errors (network issues, SSL problems, etc.)
    if (error instanceof TypeError) {
      throw new ApiError('Network connection failed. Please check your connection and try again.', 0)
    }
    
    // Handle other errors
    throw new ApiError('An unexpected error occurred', 0)
  }
}

export async function login(username: string, password: string) {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  
  const headers: HeadersInit = {
    'Content-Type': 'application/x-www-form-urlencoded',
  }
  
  // Add CSRF token for login
  if (typeof window !== 'undefined') {
    headers['X-CSRF-Token'] = getCSRFToken()
  }
  
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers,
    body: formData.toString(),
    credentials: 'include', // Include cookies in requests
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Invalid credentials' }))
    throw new ApiError(errorData.detail || 'Login failed', response.status)
  }
  
  // Login successful (204 No Content for FastAPI-Users)
  return { success: true }
}

export async function logout() {
  try {
    const headers: HeadersInit = {}
    
    // Add CSRF token for logout
    if (typeof window !== 'undefined') {
      headers['X-CSRF-Token'] = getCSRFToken()
    }
    
    // Call backend logout endpoint to clear cookies
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      headers,
      credentials: 'include',
    })
    
    // Redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  } catch (error) {
    // Even if server logout fails, redirect to login
    console.warn('Server logout failed, but redirecting to login:', error)
    
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }
}

export async function getCurrentUser() {
  try {
    return await fetchWithAuth('/api/v1/users/me')
  } catch (error) {
    // Add more specific error handling for auth failures
    if (error instanceof ApiError && error.status === 401) {
      throw new ApiError('Session expired or invalid', 401)
    }
    
    // Handle network/connection errors quietly for auth checks
    if (error instanceof ApiError && error.status === 0) {
      throw new ApiError('Unable to connect to server', 0)
    }
    
    throw error
  }
}

export async function getLibrary() {
  return fetchWithAuth('/api/v1/library')
}

export async function getSeries(seriesId: string) {
  return fetchWithAuth(`/api/v1/library/series/${seriesId}`)
}

export async function getChapter(chapterId: string) {
  return fetchWithAuth(`/api/v1/library/chapters/${chapterId}`)
}

// Reader API functions
export async function getChapterPages(chapterId: number) {
  return fetchWithAuth(`/api/v1/reader/chapters/${chapterId}/pages`)
}

export async function getPageImageUrl(chapterId: number, pageFilename: string, maxWidth?: number): Promise<string> {
  const params = new URLSearchParams()
  if (maxWidth) {
    params.append('max_width', maxWidth.toString())
  }
  const queryString = params.toString()
  const url = `${API_BASE_URL}/api/v1/reader/chapters/${chapterId}/pages/${encodeURIComponent(pageFilename)}${queryString ? '?' + queryString : ''}`
  return url
}

export async function updateReadingProgress(chapterId: number, pageNumber: number) {
  return fetchWithAuth(`/api/v1/reader/chapters/${chapterId}/progress`, {
    method: 'POST',
    body: JSON.stringify({ page_number: pageNumber })
  })
}

export async function getChapterNavigation(chapterId: number) {
  return fetchWithAuth(`/api/v1/reader/chapters/${chapterId}/navigation`)
}

export async function navigatePages(chapterId: number, direction: string, currentPage: number) {
  return fetchWithAuth(`/api/v1/reader/chapters/${chapterId}/navigate`, {
    method: 'POST',
    body: JSON.stringify({ direction, current_page: currentPage })
  })
}

export async function getChapterInfo(chapterId: number) {
  return fetchWithAuth(`/api/v1/reader/chapters/${chapterId}/info`)
}

export async function searchLibrary(query: string) {
  return fetchWithAuth(`/api/v1/search?query=${encodeURIComponent(query)}`)
}

// Metadata editing API functions
export async function updateSeries(seriesId: number, data: any, preview: boolean = false) {
  const params = preview ? '?preview=true' : ''
  return fetchWithAuth(`/api/v1/series/${seriesId}${params}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  })
}

export async function getSeriesHistory(seriesId: number) {
  return fetchWithAuth(`/api/v1/series/${seriesId}/history`)
}

export async function restoreSeriesHistory(seriesId: number, historyId: number) {
  return fetchWithAuth(`/api/v1/series/${seriesId}/restore/${historyId}`, {
    method: 'POST'
  })
}

export async function bulkUpdateSeries(seriesIds: number[], data: any) {
  return fetchWithAuth('/api/v1/series/bulk', {
    method: 'PATCH',
    body: JSON.stringify({
      series_ids: seriesIds,
      update_data: data
    })
  })
}

export async function getChapters(seriesId?: number) {
  const params = seriesId ? `?series_id=${seriesId}` : ''
  return fetchWithAuth(`/api/v1/chapters/${params}`)
}

export async function createChapter(data: any) {
  return fetchWithAuth('/api/v1/chapters/', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function getChapterById(chapterId: number) {
  return fetchWithAuth(`/api/v1/chapters/${chapterId}`)
}

export async function updateChapter(chapterId: number, data: any, preview: boolean = false) {
  const params = preview ? '?preview=true' : ''
  return fetchWithAuth(`/api/v1/chapters/${chapterId}${params}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  })
}

export async function deleteChapter(chapterId: number) {
  return fetchWithAuth(`/api/v1/chapters/${chapterId}`, {
    method: 'DELETE'
  })
}

export async function bulkUpdateChapters(chapterIds: number[], data: any) {
  return fetchWithAuth('/api/v1/chapters/bulk', {
    method: 'PATCH',
    body: JSON.stringify({
      chapter_ids: chapterIds,
      update_data: data
    })
  })
}

export async function getChapterHistory(chapterId: number) {
  return fetchWithAuth(`/api/v1/chapters/${chapterId}/history`)
}

export async function restoreChapterHistory(chapterId: number, historyId: number) {
  return fetchWithAuth(`/api/v1/chapters/${chapterId}/restore/${historyId}`, {
    method: 'POST'
  })
}

// Library Path API functions
export async function getLibraryPaths(includeInactive: boolean = false): Promise<LibraryPathResponse[]> {
  const params = includeInactive ? '?include_inactive=true' : ''
  return fetchWithAuth(`/api/v1/library-paths/${params}`)
}

export async function createLibraryPath(data: LibraryPathCreate): Promise<LibraryPathResponse> {
  return fetchWithAuth('/api/v1/library-paths/', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function updateLibraryPath(pathId: number, data: LibraryPathUpdate): Promise<LibraryPathResponse> {
  return fetchWithAuth(`/api/v1/library-paths/${pathId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export async function deleteLibraryPath(pathId: number): Promise<void> {
  return fetchWithAuth(`/api/v1/library-paths/${pathId}`, {
    method: 'DELETE'
  })
}

export async function validatePath(path: string): Promise<PathValidationResult> {
  const params = `?path=${encodeURIComponent(path)}`
  return fetchWithAuth(`/api/v1/library-paths/validate-path${params}`, {
    method: 'POST'
  })
}

export async function getStorageInfo(pathId: number): Promise<StorageInfo> {
  return fetchWithAuth(`/api/v1/library-paths/${pathId}/storage-info`)
}

export async function browsePaths(path: string, showHidden: boolean = false): Promise<DirectoryBrowseResponse> {
  const encodedPath = encodeURIComponent(path)
  const params = showHidden ? '?show_hidden=true' : '?show_hidden=false'
  return fetchWithAuth(`/api/v1/library-paths/browse/${encodedPath}${params}`)
}

// Directory browsing function
export async function browseDirectory(path: string, showHidden: boolean = false): Promise<DirectoryBrowseResponse> {
  const encodedPath = encodeURIComponent(path)
  const params = showHidden ? '?show_hidden=true' : '?show_hidden=false'
  return fetchWithAuth(`/api/v1/library-paths/browse/${encodedPath}${params}`)
}

// Convenience functions for library path management
export async function activateLibraryPath(pathId: number): Promise<LibraryPathResponse> {
  return updateLibraryPath(pathId, { is_active: true })
}

export async function deactivateLibraryPath(pathId: number): Promise<LibraryPathResponse> {
  return updateLibraryPath(pathId, { is_active: false })
}

export async function updateLibraryPathPriority(pathId: number, priority: number): Promise<LibraryPathResponse> {
  return updateLibraryPath(pathId, { priority })
}

// Filtering and Sorting API functions
export async function filterSeries(
  filters: SeriesFilter,
  sortOptions?: SortOption[],
  page: number = 1,
  pageSize: number = 50
): Promise<FilteredSeriesResponse> {
  return fetchWithAuth('/api/v1/series/filter', {
    method: 'POST',
    body: JSON.stringify({
      filters,
      sort_options: sortOptions,
      page,
      page_size: pageSize
    })
  })
}

export async function getFilterOptions(): Promise<FilterOptions> {
  return fetchWithAuth('/api/v1/series/filter/options')
}

// Filter Preset API functions
export async function getFilterPresets(): Promise<FilterPreset[]> {
  return fetchWithAuth('/api/v1/filter-presets/')
}

export async function createFilterPreset(data: FilterPresetCreate): Promise<FilterPreset> {
  return fetchWithAuth('/api/v1/filter-presets/', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function getFilterPreset(presetId: number): Promise<FilterPreset> {
  return fetchWithAuth(`/api/v1/filter-presets/${presetId}`)
}

export async function updateFilterPreset(presetId: number, data: FilterPresetUpdate): Promise<FilterPreset> {
  return fetchWithAuth(`/api/v1/filter-presets/${presetId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export async function deleteFilterPreset(presetId: number): Promise<void> {
  return fetchWithAuth(`/api/v1/filter-presets/${presetId}`, {
    method: 'DELETE'
  })
}