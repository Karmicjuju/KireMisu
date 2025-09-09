'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { LibraryGrid } from "@/components/library/LibraryGrid"
import { useSeries } from "@/hooks/useSeries"
import { useSearch } from "@/hooks/useSearch"
import { Button } from "@/components/ui/button"
import { RefreshCw, Plus } from "lucide-react"
import SearchResults from "@/components/search/SearchResults"

export default function LibraryPage() {
  const searchParams = useSearchParams()
  const searchQuery = searchParams.get('q')
  const [isSearchMode, setIsSearchMode] = useState(!!searchQuery)
  
  // Regular series data for non-search mode
  const { series, isLoading: seriesLoading, error: seriesError, refetch, setSearch } = useSeries({
    size: 50, // Load more items for better grid display
  })
  
  // Search functionality
  const {
    query,
    setQuery,
    results: searchResults,
    total: searchTotal,
    loading: searchLoading,
    error: searchError,
    currentPage,
    setCurrentPage,
    hasNextPage,
    hasPreviousPage,
    search,
    clearResults
  } = useSearch()
  
  // Handle URL search parameter changes
  useEffect(() => {
    const urlQuery = searchParams.get('q')
    if (urlQuery && urlQuery !== query) {
      setQuery(urlQuery)
      setIsSearchMode(true)
      search(urlQuery)
    } else if (!urlQuery && isSearchMode) {
      setIsSearchMode(false)
      clearResults()
      setQuery('')
    }
  }, [searchParams, query, search, clearResults, setQuery, isSearchMode])
  
  // Determine what to display
  const displayLoading = isSearchMode ? searchLoading : seriesLoading
  const displayError = isSearchMode ? searchError : seriesError
  const displayData = isSearchMode ? searchResults : series

  return (
    <ProtectedRoute>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              {isSearchMode && query ? `Search Results` : 'Library'}
            </h1>
            <p className="text-muted-foreground">
              {isSearchMode && query 
                ? `Showing results for "${query}"` 
                : 'Browse and manage your manga collection'
              }
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={isSearchMode ? () => search(query) : refetch}
              disabled={displayLoading}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${displayLoading ? 'animate-spin' : ''}`} />
              {isSearchMode ? 'Search Again' : 'Refresh'}
            </Button>
            
            <Button size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Add Series
            </Button>
          </div>
        </div>

        {/* Content */}
        {isSearchMode ? (
          <SearchResults
            results={searchResults}
            loading={searchLoading}
            error={searchError}
            total={searchTotal}
            query={query}
            onResultClick={(result) => {
              // Navigate to series detail page
              window.location.href = `/library/series/${result.id}`
            }}
          />
        ) : (
          <LibraryGrid
            series={series}
            isLoading={seriesLoading}
            error={seriesError}
            onSearch={setSearch}
            onRefresh={refetch}
          />
        )}
        
        {/* Pagination for search results */}
        {isSearchMode && searchResults.length > 0 && (searchTotal > searchResults.length) && (
          <div className="flex justify-center items-center gap-4 mt-8">
            <Button
              variant="outline"
              disabled={!hasPreviousPage || searchLoading}
              onClick={() => setCurrentPage(currentPage - 1)}
            >
              Previous
            </Button>
            
            <span className="text-sm text-muted-foreground">
              Page {currentPage} of {Math.ceil(searchTotal / 20)}
            </span>
            
            <Button
              variant="outline"
              disabled={!hasNextPage || searchLoading}
              onClick={() => setCurrentPage(currentPage + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </ProtectedRoute>
  )
}