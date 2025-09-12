"use client"

import React from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useFilterStore } from '@/lib/filter-store'
import type { SortOption } from '@/lib/types'
import { cn } from '@/lib/utils'

const SORT_OPTIONS = [
  { field: 'title' as const, label: 'Title' },
  { field: 'date_added' as const, label: 'Date Added' },
  { field: 'last_read' as const, label: 'Last Read' },
  { field: 'rating' as const, label: 'Rating' },
  { field: 'author' as const, label: 'Author' },
  { field: 'year' as const, label: 'Year' },
  { field: 'chapter_count' as const, label: 'Chapter Count' },
]

interface SortControlsProps {
  className?: string
  compact?: boolean
}

export function SortControls({ className, compact = false }: SortControlsProps) {
  const { sortOptions, setSortOptions, addSortOption, removeSortOption } = useFilterStore()

  const handleDirectionToggle = (field: string) => {
    const existing = sortOptions.find(opt => opt.field === field)
    if (existing) {
      const newDirection = existing.direction === 'asc' ? 'desc' : 'asc'
      addSortOption({ field: field as any, direction: newDirection })
    }
  }

  const handleAddSort = (field: string) => {
    addSortOption({ field: field as any, direction: 'asc' })
  }

  const handleRemoveSort = (field: string) => {
    removeSortOption(field)
  }

  const getFieldLabel = (field: string) => {
    return SORT_OPTIONS.find(opt => opt.field === field)?.label || field
  }

  const getDirectionIcon = (direction: 'asc' | 'desc') => {
    return direction === 'asc' ? ArrowUp : ArrowDown
  }

  const availableFields = SORT_OPTIONS.filter(
    opt => !sortOptions.some(sort => sort.field === opt.field)
  )

  if (compact) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        {/* Current sorts as badges */}
        {sortOptions.length > 0 && (
          <div className="flex items-center gap-1">
            {sortOptions.map((sort, index) => {
              const DirectionIcon = getDirectionIcon(sort.direction)
              return (
                <Badge
                  key={`${sort.field}-${index}`}
                  variant="secondary"
                  className="flex items-center gap-1 cursor-pointer hover:bg-secondary/80"
                  onClick={() => handleDirectionToggle(sort.field)}
                >
                  <span className="text-xs">{getFieldLabel(sort.field)}</span>
                  <DirectionIcon className="h-3 w-3" />
                  <button
                    className="ml-1 hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveSort(sort.field)
                    }}
                  >
                    <X className="h-2 w-2" />
                  </button>
                </Badge>
              )
            })}
          </div>
        )}

        {/* Add sort dropdown */}
        {availableFields.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Plus className="h-3 w-3 mr-1" />
                Sort
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {availableFields.map((option) => (
                <DropdownMenuItem
                  key={option.field}
                  onClick={() => handleAddSort(option.field)}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    )
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Sort Options List */}
      {sortOptions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Sort Order</h4>
          <div className="space-y-2">
            {sortOptions.map((sort, index) => {
              const DirectionIcon = getDirectionIcon(sort.direction)
              return (
                <div
                  key={`${sort.field}-${index}`}
                  className="flex items-center justify-between p-2 bg-secondary/50 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {index + 1}.
                    </span>
                    <span className="font-medium">{getFieldLabel(sort.field)}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDirectionToggle(sort.field)}
                      className="h-6 px-2"
                    >
                      <DirectionIcon className="h-3 w-3 mr-1" />
                      <span className="text-xs capitalize">{sort.direction}</span>
                    </Button>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveSort(sort.field)}
                    className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Add New Sort */}
      {availableFields.length > 0 && (
        <>
          {sortOptions.length > 0 && <Separator />}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Add Sort Field</h4>
            <Select onValueChange={handleAddSort}>
              <SelectTrigger>
                <SelectValue placeholder="Choose field to sort by..." />
              </SelectTrigger>
              <SelectContent>
                {availableFields.map((option) => (
                  <SelectItem key={option.field} value={option.field}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}

      {/* Clear All Sorts */}
      {sortOptions.length > 0 && (
        <>
          <Separator />
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSortOptions([])}
            className="w-full"
          >
            <X className="h-3 w-3 mr-2" />
            Clear All Sorts
          </Button>
        </>
      )}

      {sortOptions.length === 0 && (
        <div className="text-center py-6 text-muted-foreground">
          <ArrowUpDown className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No custom sorting applied</p>
          <p className="text-xs">Results will be sorted by title (A-Z)</p>
        </div>
      )}
    </div>
  )
}

interface QuickSortProps {
  className?: string
}

export function QuickSort({ className }: QuickSortProps) {
  const { sortOptions, addSortOption } = useFilterStore()

  const quickSortOptions = [
    { field: 'title' as const, direction: 'asc' as const, label: 'Title A-Z' },
    { field: 'title' as const, direction: 'desc' as const, label: 'Title Z-A' },
    { field: 'date_added' as const, direction: 'desc' as const, label: 'Newest First' },
    { field: 'date_added' as const, direction: 'asc' as const, label: 'Oldest First' },
    { field: 'rating' as const, direction: 'desc' as const, label: 'Highest Rated' },
    { field: 'rating' as const, direction: 'asc' as const, label: 'Lowest Rated' },
    { field: 'last_read' as const, direction: 'desc' as const, label: 'Recently Read' },
  ]

  const currentSort = sortOptions.length > 0 
    ? `${sortOptions[0].field}-${sortOptions[0].direction}` 
    : 'title-asc'

  const handleQuickSort = (field: string, direction: 'asc' | 'desc') => {
    addSortOption({ field: field as any, direction })
  }

  return (
    <Select
      value={currentSort}
      onValueChange={(value) => {
        const [field, direction] = value.split('-')
        handleQuickSort(field, direction as 'asc' | 'desc')
      }}
    >
      <SelectTrigger className={cn("w-[180px]", className)}>
        <ArrowUpDown className="h-4 w-4 mr-2" />
        <SelectValue placeholder="Sort by..." />
      </SelectTrigger>
      <SelectContent>
        {quickSortOptions.map((option) => (
          <SelectItem 
            key={`${option.field}-${option.direction}`} 
            value={`${option.field}-${option.direction}`}
          >
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}