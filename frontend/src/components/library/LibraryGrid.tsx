'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Grid, List, Search, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Toggle } from '@/components/ui/toggle'
import { Skeleton } from '@/components/ui/skeleton'
import { SeriesCard } from './SeriesCard'
import { cn } from '@/lib/utils'

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

interface LibraryGridProps {
  series?: Series[]
  isLoading?: boolean
  error?: string | null
  onSearch?: (query: string) => void
  onRefresh?: () => void
  className?: string
}

type ViewMode = 'grid' | 'list'
type GridDensity = 'comfortable' | 'compact' | 'cozy'

export function LibraryGrid({
  series = [],
  isLoading = false,
  error = null,
  onSearch,
  onRefresh,
  className
}: LibraryGridProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [gridDensity, setGridDensity] = useState<GridDensity>('comfortable')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSeries, setSelectedSeries] = useState<number[]>([])
  const [currentFocus, setCurrentFocus] = useState<number>(-1)

  // Load preferences from localStorage
  useEffect(() => {
    try {
      const savedViewMode = localStorage.getItem('library-view-mode') as ViewMode
      const savedGridDensity = localStorage.getItem('library-grid-density') as GridDensity
      
      // Validate values before setting
      if (savedViewMode && ['grid', 'list'].includes(savedViewMode)) {
        setViewMode(savedViewMode)
      }
      if (savedGridDensity && ['comfortable', 'compact', 'cozy'].includes(savedGridDensity)) {
        setGridDensity(savedGridDensity)
      }
    } catch (error) {
      // localStorage might not be available or corrupted
      console.warn('Failed to load preferences from localStorage:', error)
    }
  }, [])

  // Save preferences to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('library-view-mode', viewMode)
    } catch (error) {
      console.warn('Failed to save view mode to localStorage:', error)
    }
  }, [viewMode])

  useEffect(() => {
    try {
      localStorage.setItem('library-grid-density', gridDensity)
    } catch (error) {
      console.warn('Failed to save grid density to localStorage:', error)
    }
  }, [gridDensity])

  // Filter series based on search query
  const filteredSeries = useMemo(() => {
    if (!searchQuery.trim()) return series
    
    const query = searchQuery.toLowerCase()
    return series.filter(s => 
      s.title.toLowerCase().includes(query) ||
      s.author?.toLowerCase().includes(query) ||
      s.artist?.toLowerCase().includes(query) ||
      s.description?.toLowerCase().includes(query)
    )
  }, [series, searchQuery])

  // Handle search with debouncing
  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value)
    if (onSearch) {
      // Simple debouncing
      const timeoutId = setTimeout(() => onSearch(value), 300)
      return () => clearTimeout(timeoutId)
    }
  }, [onSearch])

  // Handle series selection
  const handleSeriesSelect = useCallback((series: Series) => {
    setSelectedSeries(prev => 
      prev.includes(series.id) 
        ? prev.filter(id => id !== series.id)
        : [...prev, series.id]
    )
  }, [])

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (filteredSeries.length === 0) return

    const maxIndex = filteredSeries.length - 1
    
    switch (e.key) {
      case 'ArrowRight':
        e.preventDefault()
        setCurrentFocus(prev => Math.min(prev + 1, maxIndex))
        break
      case 'ArrowLeft':
        e.preventDefault()
        setCurrentFocus(prev => Math.max(prev - 1, 0))
        break
      case 'ArrowDown':
        e.preventDefault()
        if (viewMode === 'grid') {
          // Calculate columns based on screen width for grid navigation
          const cols = getGridColumns()
          setCurrentFocus(prev => Math.min(prev + cols, maxIndex))
        } else {
          setCurrentFocus(prev => Math.min(prev + 1, maxIndex))
        }
        break
      case 'ArrowUp':
        e.preventDefault()
        if (viewMode === 'grid') {
          const cols = getGridColumns()
          setCurrentFocus(prev => Math.max(prev - cols, 0))
        } else {
          setCurrentFocus(prev => Math.max(prev - 1, 0))
        }
        break
      case 'Enter':
      case ' ':
        if (currentFocus >= 0) {
          e.preventDefault()
          handleSeriesSelect(filteredSeries[currentFocus])
        }
        break
      case 'Escape':
        setCurrentFocus(-1)
        setSelectedSeries([])
        break
    }
  }, [filteredSeries, viewMode, currentFocus, handleSeriesSelect])

  // Helper function to determine grid columns based on density and screen
  const getGridColumns = () => {
    switch (gridDensity) {
      case 'compact': return 6
      case 'cozy': return 4
      case 'comfortable': return 3
      default: return 3
    }
  }

  // Get grid classes based on density
  const getGridClasses = () => {
    const baseClasses = 'grid gap-4 w-full'
    switch (gridDensity) {
      case 'compact':
        return `${baseClasses} grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8`
      case 'cozy':
        return `${baseClasses} grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
      case 'comfortable':
      default:
        return `${baseClasses} grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
    }
  }

  // Loading skeleton
  const renderLoadingSkeleton = () => {
    const skeletonCount = viewMode === 'grid' ? 12 : 8
    
    if (viewMode === 'list') {
      return (
        <div className="space-y-4">
          {Array.from({ length: skeletonCount }).map((_, index) => (
            <div key={index} className="flex space-x-4">
              <Skeleton className="h-32 w-24 flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </div>
          ))}
        </div>
      )
    }

    return (
      <div className={getGridClasses()}>
        {Array.from({ length: skeletonCount }).map((_, index) => (
          <div key={index} className="space-y-3">
            <Skeleton className="aspect-[3/4] w-full" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Empty state
  const renderEmptyState = () => (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-muted p-6 mb-4">
        <Search className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">
        {searchQuery ? 'No results found' : 'No series in your library'}
      </h3>
      <p className="text-muted-foreground mb-4 max-w-md">
        {searchQuery 
          ? `No series match "${searchQuery}". Try adjusting your search terms.`
          : 'Start building your manga collection by adding series to your library.'
        }
      </p>
      {searchQuery ? (
        <Button 
          variant="outline" 
          onClick={() => setSearchQuery('')}
        >
          Clear search
        </Button>
      ) : onRefresh ? (
        <Button onClick={onRefresh}>
          Refresh Library
        </Button>
      ) : null}
    </div>
  )

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="rounded-full bg-destructive/10 p-6 mb-4">
          <Search className="h-12 w-12 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold mb-2 text-destructive">
          Failed to load library
        </h3>
        <p className="text-muted-foreground mb-4 max-w-md">
          {error}
        </p>
        {onRefresh && (
          <Button variant="outline" onClick={onRefresh}>
            Try again
          </Button>
        )}
      </div>
    )
  }

  return (
    <div 
      className={cn('space-y-6', className)}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      {/* Header with controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="Search manga by title, author, or artist..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Grid density selector */}
          {viewMode === 'grid' && (
            <div className="flex items-center border rounded-md">
              {(['comfortable', 'cozy', 'compact'] as GridDensity[]).map((density) => (
                <Toggle
                  key={density}
                  size="sm"
                  pressed={gridDensity === density}
                  onPressedChange={() => setGridDensity(density)}
                  className="capitalize border-0 rounded-none data-[state=on]:bg-primary data-[state=on]:text-primary-foreground first:rounded-l-md last:rounded-r-md"
                  aria-label={`${density} density`}
                >
                  {density}
                </Toggle>
              ))}
            </div>
          )}
          
          {/* View mode toggle */}
          <div className="flex items-center border rounded-md">
            <Toggle
              size="sm"
              pressed={viewMode === 'grid'}
              onPressedChange={() => setViewMode('grid')}
              className="border-0 rounded-none rounded-l-md"
              aria-label="Grid view"
            >
              <Grid className="h-4 w-4" />
            </Toggle>
            <Toggle
              size="sm"
              pressed={viewMode === 'list'}
              onPressedChange={() => setViewMode('list')}
              className="border-0 rounded-none rounded-r-md"
              aria-label="List view"
            >
              <List className="h-4 w-4" />
            </Toggle>
          </div>

          {/* Filter button (future functionality) */}
          <Button variant="outline" size="sm" disabled>
            <SlidersHorizontal className="h-4 w-4 mr-2" />
            Filter
          </Button>
        </div>
      </div>

      {/* Results counter */}
      <div className="text-sm text-muted-foreground">
        {isLoading ? (
          'Loading...'
        ) : (
          `${filteredSeries.length} of ${series.length} series`
        )}
        {selectedSeries.length > 0 && (
          <span className="ml-2">
            • {selectedSeries.length} selected
          </span>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        renderLoadingSkeleton()
      ) : filteredSeries.length === 0 ? (
        renderEmptyState()
      ) : (
        <div className={viewMode === 'grid' ? getGridClasses() : 'space-y-4'}>
          {filteredSeries.map((series, index) => (
            <SeriesCard
              key={series.id}
              series={series}
              viewMode={viewMode}
              onSelect={handleSeriesSelect}
              isSelected={selectedSeries.includes(series.id)}
              className={cn(
                'transition-all duration-200',
                currentFocus === index && 'ring-2 ring-primary ring-offset-2'
              )}
            />
          ))}
        </div>
      )}
    </div>
  )
}