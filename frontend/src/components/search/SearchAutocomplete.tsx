"use client"

import React, { useState, useRef, useEffect } from 'react'
import { Search, Clock, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface SearchAutocompleteProps {
  value: string
  onChange: (value: string) => void
  onSearch: (query: string) => void
  suggestions: string[]
  loadingSuggestions: boolean
  onGetSuggestions: (query: string) => void
  onClearSuggestions: () => void
  recentSearches?: string[]
  onGetRecentSearches?: () => void
  onClearRecentSearches?: () => void
  placeholder?: string
  className?: string
  error?: string | null
}

export default function SearchAutocomplete({
  value,
  onChange,
  onSearch,
  suggestions,
  loadingSuggestions,
  onGetSuggestions,
  onClearSuggestions,
  recentSearches = [],
  onGetRecentSearches,
  onClearRecentSearches,
  placeholder = "Search manga, series, or authors...",
  className,
  error
}: SearchAutocompleteProps) {
  
  const [isOpen, setIsOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Combined suggestions and recent searches
  const allSuggestions = [
    ...suggestions,
    ...(suggestions.length === 0 && !loadingSuggestions ? recentSearches : [])
  ]
  
  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onChange(newValue)
    
    // Get suggestions for non-empty values
    if (newValue.trim().length >= 2) {
      onGetSuggestions(newValue.trim())
    } else {
      onClearSuggestions()
    }
    
    setSelectedIndex(-1)
    setIsOpen(true)
  }
  
  // Handle input focus
  const handleInputFocus = () => {
    setIsOpen(true)
    
    // Load recent searches if no current suggestions and no value
    if (suggestions.length === 0 && !value.trim() && onGetRecentSearches) {
      onGetRecentSearches()
    }
  }
  
  // Handle input blur
  const handleInputBlur = (e: React.FocusEvent) => {
    // Delay closing to allow clicking on suggestions
    setTimeout(() => {
      if (!dropdownRef.current?.contains(document.activeElement)) {
        setIsOpen(false)
        setSelectedIndex(-1)
      }
    }, 150)
  }
  
  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (selectedIndex >= 0 && allSuggestions[selectedIndex]) {
      const selectedSuggestion = allSuggestions[selectedIndex]
      onChange(selectedSuggestion)
      onSearch(selectedSuggestion)
    } else if (value.trim()) {
      onSearch(value.trim())
    }
    
    setIsOpen(false)
    setSelectedIndex(-1)
    inputRef.current?.blur()
  }
  
  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    onChange(suggestion)
    onSearch(suggestion)
    setIsOpen(false)
    setSelectedIndex(-1)
    inputRef.current?.blur()
  }
  
  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev < allSuggestions.length - 1 ? prev + 1 : 0
        )
        break
        
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : allSuggestions.length - 1
        )
        break
        
      case 'Escape':
        setIsOpen(false)
        setSelectedIndex(-1)
        inputRef.current?.blur()
        break
        
      case 'Tab':
        setIsOpen(false)
        setSelectedIndex(-1)
        break
    }
  }
  
  // Handle clear input
  const handleClear = () => {
    onChange('')
    onClearSuggestions()
    inputRef.current?.focus()
  }
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setIsOpen(false)
        setSelectedIndex(-1)
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])
  
  return (
    <div className={cn("relative w-full", className)}>
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          
          <Input
            ref={inputRef}
            type="text"
            placeholder={placeholder}
            value={value}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            onKeyDown={handleKeyDown}
            className={cn(
              "pl-10 pr-10 bg-input border-border text-foreground placeholder:text-muted-foreground",
              "focus:border-primary focus:ring-primary/20",
              "hover:border-accent transition-colors",
              error && "border-destructive focus:border-destructive focus:ring-destructive/20"
            )}
            aria-label="Search manga library"
            aria-invalid={!!error}
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            aria-activedescendant={selectedIndex >= 0 ? `suggestion-${selectedIndex}` : undefined}
            maxLength={200}
            autoComplete="off"
          />
          
          {value && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 p-0 hover:bg-accent"
              onClick={handleClear}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Clear search</span>
            </Button>
          )}
        </div>
        
        {error && (
          <div className="absolute top-full left-0 mt-1 text-xs text-destructive bg-background px-2 py-1 rounded border border-destructive/30 z-50">
            {error}
          </div>
        )}
      </form>
      
      {/* Dropdown */}
      {isOpen && (allSuggestions.length > 0 || loadingSuggestions) && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-md shadow-lg z-50 max-h-80 overflow-y-auto"
          role="listbox"
        >
          {loadingSuggestions ? (
            <div className="p-2 space-y-2">
              {Array.from({ length: 3 }, (_, index) => (
                <div key={index} className="flex items-center gap-3 px-3 py-2">
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-4 flex-1" />
                </div>
              ))}
            </div>
          ) : (
            <>
              {suggestions.length > 0 && (
                <div>
                  <div className="px-3 py-2 text-xs font-medium text-muted-foreground border-b border-border">
                    Suggestions
                  </div>
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={`suggestion-${index}`}
                      id={`suggestion-${index}`}
                      className={cn(
                        "w-full text-left px-3 py-2 text-sm hover:bg-accent transition-colors",
                        "flex items-center gap-3",
                        selectedIndex === index && "bg-accent"
                      )}
                      onClick={() => handleSuggestionClick(suggestion)}
                      role="option"
                      aria-selected={selectedIndex === index}
                    >
                      <Search className="h-4 w-4 text-muted-foreground" />
                      <span>{suggestion}</span>
                    </button>
                  ))}
                </div>
              )}
              
              {suggestions.length === 0 && recentSearches.length > 0 && !value.trim() && (
                <div>
                  <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                    <span className="text-xs font-medium text-muted-foreground">
                      Recent searches
                    </span>
                    {onClearRecentSearches && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-1 text-xs"
                        onClick={onClearRecentSearches}
                      >
                        Clear
                      </Button>
                    )}
                  </div>
                  {recentSearches.map((search, index) => (
                    <button
                      key={`recent-${index}`}
                      id={`suggestion-${index}`}
                      className={cn(
                        "w-full text-left px-3 py-2 text-sm hover:bg-accent transition-colors",
                        "flex items-center gap-3",
                        selectedIndex === index && "bg-accent"
                      )}
                      onClick={() => handleSuggestionClick(search)}
                      role="option"
                      aria-selected={selectedIndex === index}
                    >
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span>{search}</span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}