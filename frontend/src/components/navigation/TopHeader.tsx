"use client"

import React, { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { z } from 'zod'

interface TopHeaderProps {
  sidebarCollapsed?: boolean
  className?: string
}

// Schema for search input validation
const searchSchema = z.object({
  query: z
    .string()
    .max(200, 'Search query too long')
    .regex(/^[a-zA-Z0-9\s\-_\.]+$/, 'Only letters, numbers, spaces, hyphens, underscores, and periods allowed')
    .optional()
})

// Sanitize input to prevent XSS attacks
function sanitizeSearchInput(input: string): string {
  // Remove any HTML tags and dangerous characters
  return input
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .replace(/[<>'"&]/g, '') // Remove potentially dangerous characters
    .trim()
    .slice(0, 200) // Limit length
}

export function TopHeader({ sidebarCollapsed = false, className }: TopHeaderProps) {
  const [searchValue, setSearchValue] = useState('')
  const [searchError, setSearchError] = useState<string | null>(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768)
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Handle search input change with validation
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value
    const sanitizedValue = sanitizeSearchInput(rawValue)
    
    // Validate the sanitized input
    const validation = searchSchema.safeParse({ query: sanitizedValue })
    
    if (!validation.success && sanitizedValue.length > 0) {
      setSearchError(validation.error.errors[0]?.message || 'Invalid search input')
    } else {
      setSearchError(null)
    }
    
    setSearchValue(sanitizedValue)
  }

  // Handle search submission
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (searchError || !searchValue.trim()) {
      return
    }
    
    // TODO: Implement search functionality
    console.log('Searching for:', searchValue)
  }

  // Calculate left padding based on sidebar state
  const leftPadding = isMobile ? 'pl-16' : sidebarCollapsed ? 'md:pl-20' : 'md:pl-64'

  return (
    <header className={cn(
      "fixed top-0 right-0 z-40 h-16 bg-[#1a1d29] border-b border-gray-800 transition-all duration-300",
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
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              type="text"
              placeholder="Search manga, series, or authors..."
              value={searchValue}
              onChange={handleSearchChange}
              className={cn(
                "pl-10 bg-[#151821] border-gray-700 text-white placeholder:text-gray-400",
                "focus:border-[#ff6b35] focus:ring-[#ff6b35]/20",
                "hover:border-gray-600 transition-colors",
                searchError && "border-red-500 focus:border-red-500 focus:ring-red-500/20"
              )}
              aria-label="Search manga library"
              aria-invalid={!!searchError}
              aria-describedby={searchError ? "search-error" : undefined}
              maxLength={200}
            />
            {searchError && (
              <div
                id="search-error"
                className="absolute top-full left-0 mt-1 text-xs text-red-400 bg-[#1a1d29] px-2 py-1 rounded border border-red-500/30"
              >
                {searchError}
              </div>
            )}
          </form>
        </div>

        {/* Right section - could be used for user menu or notifications */}
        <div className="flex items-center space-x-4">
          {/* Placeholder for future user menu, notifications, etc. */}
        </div>
      </div>
    </header>
  )
}