"use client"

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { SearchResult } from '@/hooks/useSearch'
import { cn } from '@/lib/utils'

interface SearchResultsProps {
  results: SearchResult[]
  loading: boolean
  error: string | null
  total: number
  query: string
  onResultClick?: (result: SearchResult) => void
  className?: string
}

interface SearchResultItemProps {
  result: SearchResult
  query: string
  onClick?: (result: SearchResult) => void
}

// Function to highlight search terms in text
function highlightSearchTerms(text: string, query: string): React.ReactNode {
  if (!query || !text) return text
  
  // Split query into individual words and escape special regex characters
  const searchTerms = query
    .toLowerCase()
    .split(/\s+/)
    .filter(term => term.length > 0)
    .map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  
  if (searchTerms.length === 0) return text
  
  // Create regex pattern for highlighting
  const pattern = new RegExp(`(${searchTerms.join('|')})`, 'gi')
  const parts = text.split(pattern)
  
  return parts.map((part, index) => {
    const isMatch = searchTerms.some(term => 
      part.toLowerCase() === term.toLowerCase().replace(/\\\\/g, '\\')
    )
    
    return isMatch ? (
      <mark key={index} className="bg-yellow-200 dark:bg-yellow-800/30 px-0.5 rounded">
        {part}
      </mark>
    ) : (
      part
    )
  })
}

function SearchResultItem({ result, query, onClick }: SearchResultItemProps) {
  const handleClick = () => {
    onClick?.(result)
  }
  
  return (
    <Card 
      className={cn(
        "cursor-pointer transition-all duration-200 hover:shadow-md hover:border-primary/50",
        "bg-card hover:bg-accent/5"
      )}
      onClick={handleClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="text-lg font-semibold text-foreground line-clamp-2">
            {highlightSearchTerms(result.title, query)}
          </CardTitle>
          {result.status && (
            <Badge variant="secondary" className="shrink-0">
              {result.status}
            </Badge>
          )}
        </div>
        
        {(result.author || result.artist) && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {result.author && (
              <span>
                By {highlightSearchTerms(result.author, query)}
              </span>
            )}
            {result.author && result.artist && result.author !== result.artist && (
              <span>•</span>
            )}
            {result.artist && result.artist !== result.author && (
              <span>
                Art by {highlightSearchTerms(result.artist, query)}
              </span>
            )}
          </div>
        )}
      </CardHeader>
      
      {result.description && (
        <CardContent className="pt-0">
          <p className="text-sm text-muted-foreground line-clamp-3">
            {highlightSearchTerms(result.description, query)}
          </p>
        </CardContent>
      )}
    </Card>
  )
}

function SearchResultsSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }, (_, index) => (
        <Card key={index}>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-2">
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
              <Skeleton className="h-6 w-20" />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function EmptyResults({ query }: { query: string }) {
  return (
    <div className="text-center py-12">
      <div className="max-w-md mx-auto">
        <div className="text-muted-foreground mb-4">
          <svg
            className="mx-auto h-12 w-12 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        
        <h3 className="text-lg font-medium text-foreground mb-2">
          No results found
        </h3>
        
        <p className="text-sm text-muted-foreground mb-4">
          No manga found for "{query}". Try:
        </p>
        
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• Checking your spelling</li>
          <li>• Using different keywords</li>
          <li>• Using broader search terms</li>
          <li>• Searching by author name</li>
        </ul>
      </div>
    </div>
  )
}

function ErrorDisplay({ error, query }: { error: string; query: string }) {
  return (
    <div className="text-center py-12">
      <div className="max-w-md mx-auto">
        <div className="text-destructive mb-4">
          <svg
            className="mx-auto h-12 w-12 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        
        <h3 className="text-lg font-medium text-foreground mb-2">
          Search Error
        </h3>
        
        <p className="text-sm text-muted-foreground mb-4">
          {error}
        </p>
        
        <p className="text-xs text-muted-foreground">
          Please try again or contact support if the problem persists.
        </p>
      </div>
    </div>
  )
}

export default function SearchResults({
  results,
  loading,
  error,
  total,
  query,
  onResultClick,
  className
}: SearchResultsProps) {
  if (loading) {
    return (
      <div className={className}>
        <SearchResultsSkeleton />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className={className}>
        <ErrorDisplay error={error} query={query} />
      </div>
    )
  }
  
  if (!loading && results.length === 0 && query) {
    return (
      <div className={className}>
        <EmptyResults query={query} />
      </div>
    )
  }
  
  return (
    <div className={className}>
      {query && results.length > 0 && (
        <div className="mb-6">
          <p className="text-sm text-muted-foreground">
            Found {total.toLocaleString()} result{total !== 1 ? 's' : ''} for "{query}"
          </p>
        </div>
      )}
      
      <div className="space-y-4">
        {results.map((result) => (
          <SearchResultItem
            key={result.id}
            result={result}
            query={query}
            onClick={onResultClick}
          />
        ))}
      </div>
    </div>
  )
}