'use client'

import { useState, useEffect, useCallback } from 'react'

interface Series {
  id: number
  title: string
  description?: string
  author?: string
  artist?: string
  status?: string
  cover_path?: string
  metadata_json?: Record<string, any>
  created_at?: string
  updated_at?: string
}

interface SeriesListResponse {
  items: Series[]
  total: number
  page: number
  size: number
  pages: number
}

interface UseSeriesOptions {
  page?: number
  size?: number
  search?: string
  status?: string
  author?: string
  autoFetch?: boolean
}

interface UseSeriesReturn {
  series: Series[]
  total: number
  page: number
  pages: number
  isLoading: boolean
  error: string | null
  fetchSeries: () => Promise<void>
  refetch: () => Promise<void>
  setPage: (page: number) => void
  setSize: (size: number) => void
  setSearch: (search: string) => void
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useSeries(options: UseSeriesOptions = {}): UseSeriesReturn {
  const {
    page: initialPage = 1,
    size: initialSize = 20,
    search: initialSearch = '',
    status: initialStatus = '',
    author: initialAuthor = '',
    autoFetch = true
  } = options

  const [series, setSeries] = useState<Series[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(initialPage)
  const [size, setSize] = useState(initialSize)
  const [pages, setPages] = useState(0)
  const [search, setSearch] = useState(initialSearch)
  const [status, setStatus] = useState(initialStatus)
  const [author, setAuthor] = useState(initialAuthor)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSeries = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: size.toString(),
      })

      if (search.trim()) params.append('search', search)
      if (status) params.append('status', status)
      if (author) params.append('author', author)

      const response = await fetch(`${API_BASE_URL}/api/v1/series/?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        if (response.status === 403) {
          throw new Error('Access forbidden. Check your permissions.')
        }
        if (response.status >= 500) {
          throw new Error('Server error. Please try again later.')
        }
        throw new Error(`Failed to fetch series: ${response.statusText}`)
      }

      const data: SeriesListResponse = await response.json()
      
      setSeries(data.items || [])
      setTotal(data.total || 0)
      setPages(data.pages || 0)
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(errorMessage)
      console.error('Failed to fetch series:', err)
    } finally {
      setIsLoading(false)
    }
  }, [page, size, search, status, author])

  const refetch = useCallback(() => {
    return fetchSeries()
  }, [fetchSeries])

  // Auto-fetch when dependencies change
  useEffect(() => {
    if (autoFetch) {
      fetchSeries()
    }
  }, [fetchSeries, autoFetch])

  return {
    series,
    total,
    page,
    pages,
    isLoading,
    error,
    fetchSeries,
    refetch,
    setPage,
    setSize: (newSize: number) => {
      setSize(newSize)
      setPage(1) // Reset to first page when changing page size
    },
    setSearch: (newSearch: string) => {
      setSearch(newSearch)
      setPage(1) // Reset to first page when searching
    },
  }
}

// Hook for fetching a single series
export function useSeriesById(id: number) {
  const [series, setSeries] = useState<Series | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSeries = useCallback(async () => {
    if (!id) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/series/${id}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Series not found')
        }
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        throw new Error(`Failed to fetch series: ${response.statusText}`)
      }

      const data: Series = await response.json()
      setSeries(data)
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(errorMessage)
      console.error('Failed to fetch series:', err)
    } finally {
      setIsLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchSeries()
  }, [fetchSeries])

  return {
    series,
    isLoading,
    error,
    refetch: fetchSeries,
  }
}