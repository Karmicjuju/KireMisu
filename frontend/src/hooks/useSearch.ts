"use client"

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/lib/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<any> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
      credentials: 'include',
      signal: options.signal,
    })
    
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
    
    const contentType = response.headers.get('content-type')
    if (!contentType || !contentType.includes('application/json')) {
      return {}
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof TypeError) {
      throw new ApiError('Network connection failed. Please check your connection and try again.', 0)
    }
    
    throw new ApiError('An unexpected error occurred', 0)
  }
}

export interface SearchResult {
  id: number
  title: string
  description?: string
  author?: string
  artist?: string
  status?: string
  cover_path?: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  limit: number
  offset: number
  query: string
}

export interface AutocompleteResponse {
  suggestions: string[]
  query: string
}

export interface RecentSearchesResponse {
  searches: string[]
}

interface UseSearchOptions {
  debounceMs?: number
  minQueryLength?: number
}

interface UseSearchReturn {
  // Search state
  query: string
  setQuery: (query: string) => void
  results: SearchResult[]
  total: number
  loading: boolean
  error: string | null
  
  // Pagination
  currentPage: number
  setCurrentPage: (page: number) => void
  hasNextPage: boolean
  hasPreviousPage: boolean
  
  // Actions
  search: (searchQuery?: string) => Promise<void>
  clearResults: () => void
  
  // Autocomplete
  suggestions: string[]
  loadingSuggestions: boolean
  getSuggestions: (partialQuery: string) => Promise<void>
  clearSuggestions: () => void
  
  // Recent searches
  recentSearches: string[]
  loadingRecentSearches: boolean
  getRecentSearches: () => Promise<void>
  clearRecentSearches: () => Promise<void>
}

export function useSearch({
  debounceMs = 300,
  minQueryLength = 1
}: UseSearchOptions = {}): UseSearchReturn {
  
  const { isAuthenticated } = useAuthStore()
  
  // Search state
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(20)
  
  // Autocomplete state
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  
  // Recent searches state
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const [loadingRecentSearches, setLoadingRecentSearches] = useState(false)
  
  // Debounced search function
  const [debouncedQuery, setDebouncedQuery] = useState('')
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, debounceMs)
    
    return () => clearTimeout(timer)
  }, [query, debounceMs])
  
  // Search function
  const search = useCallback(async (searchQuery?: string) => {
    const queryToSearch = searchQuery || debouncedQuery
    
    if (!queryToSearch || queryToSearch.length < minQueryLength) {
      setResults([])
      setTotal(0)
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const offset = (currentPage - 1) * pageSize
      const params = new URLSearchParams({
        q: queryToSearch,
        limit: pageSize.toString(),
        offset: offset.toString(),
      })
      
      const response = await fetchWithAuth(`/api/v1/search/?${params.toString()}`)
      
      setResults(response.results)
      setTotal(response.total)
      
    } catch (err: any) {
      console.error('Search error:', err)
      setError(err.response?.data?.detail || 'Search failed')
      setResults([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [debouncedQuery, currentPage, pageSize, minQueryLength])
  
  // Auto-search when debounced query or pagination changes
  useEffect(() => {
    if (debouncedQuery && debouncedQuery.length >= minQueryLength) {
      search()
    }
  }, [search, debouncedQuery, minQueryLength])
  
  // Clear results
  const clearResults = useCallback(() => {
    setResults([])
    setTotal(0)
    setError(null)
    setCurrentPage(1)
  }, [])
  
  // Get autocomplete suggestions
  const getSuggestions = useCallback(async (partialQuery: string) => {
    if (!partialQuery || partialQuery.length < 2) {
      setSuggestions([])
      return
    }
    
    setLoadingSuggestions(true)
    
    try {
      const params = new URLSearchParams({
        q: partialQuery,
        limit: '10'
      })
      
      const response = await fetchWithAuth(`/api/v1/search/autocomplete?${params.toString()}`)
      
      setSuggestions(response.suggestions)
    } catch (err) {
      console.error('Autocomplete error:', err)
      setSuggestions([])
    } finally {
      setLoadingSuggestions(false)
    }
  }, [])
  
  // Clear suggestions
  const clearSuggestions = useCallback(() => {
    setSuggestions([])
  }, [])
  
  // Get recent searches
  const getRecentSearches = useCallback(async () => {
    if (!isAuthenticated) {
      setRecentSearches([])
      return
    }
    
    setLoadingRecentSearches(true)
    
    try {
      const params = new URLSearchParams({
        limit: '10'
      })
      
      const response = await fetchWithAuth(`/api/v1/search/recent?${params.toString()}`)
      
      setRecentSearches(response.searches)
    } catch (err) {
      console.error('Recent searches error:', err)
      setRecentSearches([])
    } finally {
      setLoadingRecentSearches(false)
    }
  }, [isAuthenticated])
  
  // Clear recent searches
  const clearRecentSearches = useCallback(async () => {
    if (!isAuthenticated) return
    
    try {
      await fetchWithAuth('/api/v1/search/recent', { method: 'DELETE' })
      setRecentSearches([])
    } catch (err) {
      console.error('Clear recent searches error:', err)
    }
  }, [isAuthenticated])
  
  // Reset pagination when query changes
  useEffect(() => {
    if (currentPage !== 1) {
      setCurrentPage(1)
    }
  }, [query])
  
  // Calculate pagination info
  const totalPages = Math.ceil(total / pageSize)
  const hasNextPage = currentPage < totalPages
  const hasPreviousPage = currentPage > 1
  
  return {
    // Search state
    query,
    setQuery,
    results,
    total,
    loading,
    error,
    
    // Pagination
    currentPage,
    setCurrentPage,
    hasNextPage,
    hasPreviousPage,
    
    // Actions
    search,
    clearResults,
    
    // Autocomplete
    suggestions,
    loadingSuggestions,
    getSuggestions,
    clearSuggestions,
    
    // Recent searches
    recentSearches,
    loadingRecentSearches,
    getRecentSearches,
    clearRecentSearches,
  }
}