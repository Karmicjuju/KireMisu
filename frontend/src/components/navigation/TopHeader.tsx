"use client"

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { UserMenu } from '@/components/auth/UserMenu'
import { useAuthStore } from '@/lib/auth-store'
import { cn } from '@/lib/utils'
import { useSearch } from '@/hooks/useSearch'
import SearchAutocomplete from '@/components/search/SearchAutocomplete'

interface TopHeaderProps {
  sidebarCollapsed?: boolean
  className?: string
}


export function TopHeader({ sidebarCollapsed = false, className }: TopHeaderProps) {
  const [isMobile, setIsMobile] = useState(false)
  const { isAuthenticated } = useAuthStore()
  const router = useRouter()
  
  // Search functionality
  const {
    query,
    setQuery,
    search,
    suggestions,
    loadingSuggestions,
    getSuggestions,
    clearSuggestions,
    recentSearches,
    getRecentSearches,
    clearRecentSearches,
    error
  } = useSearch()

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768)
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Handle search submission
  const handleSearchSubmit = async (searchQuery: string) => {
    if (!searchQuery.trim()) return
    
    // Perform search
    await search(searchQuery)
    
    // Navigate to search results page
    const params = new URLSearchParams({
      q: searchQuery.trim(),
    })
    router.push(`/library?${params.toString()}`)
  }

  // Calculate left padding based on sidebar state
  const leftPadding = isMobile ? 'pl-16' : sidebarCollapsed ? 'md:pl-20' : 'md:pl-64'

  return (
    <header className={cn(
      "fixed top-0 right-0 z-40 h-16 bg-background border-b border-border transition-all duration-300",
      leftPadding,
      "left-0",
      className
    )}>
      <div className="flex h-full items-center justify-between px-6">
        {/* Left section - could be used for breadcrumbs or page title in future */}
        <div className="flex items-center">
          {/* Placeholder for future breadcrumbs or page title */}
        </div>

        {/* Center section - Search bar */}
        <div className="flex-1 max-w-md mx-4">
          <SearchAutocomplete
            value={query}
            onChange={setQuery}
            onSearch={handleSearchSubmit}
            suggestions={suggestions}
            loadingSuggestions={loadingSuggestions}
            onGetSuggestions={getSuggestions}
            onClearSuggestions={clearSuggestions}
            recentSearches={recentSearches}
            onGetRecentSearches={getRecentSearches}
            onClearRecentSearches={clearRecentSearches}
            placeholder="Search manga, series, or authors..."
            error={error}
          />
        </div>

        {/* Right section - Theme toggle and user menu */}
        <div className="flex items-center space-x-4">
          <ThemeToggle />
          {isAuthenticated && <UserMenu />}
        </div>
      </div>
    </header>
  )
}