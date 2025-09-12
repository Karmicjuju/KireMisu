"use client"

import React, { useState, useEffect } from 'react'
import { X, Filter, RotateCcw, Save, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { MultiSelect } from '@/components/ui/multi-select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useFilterStore, hasActiveFilters, getFilterCount } from '@/lib/filter-store'
import { getFilterOptions, getFilterPresets } from '@/lib/api'
import type { FilterOptions, FilterPreset } from '@/lib/types'
import { cn } from '@/lib/utils'

interface CollapsibleSectionProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  badge?: number | string
}

function CollapsibleSection({ title, children, defaultOpen = false, badge }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border rounded-lg">
      <button
        className="flex items-center justify-between w-full p-3 text-left hover:bg-accent/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <span className="font-medium">{title}</span>
          {badge && (
            <Badge variant="secondary" className="text-xs">
              {badge}
            </Badge>
          )}
        </div>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {isOpen && (
        <div className="p-3 pt-0 border-t">
          {children}
        </div>
      )}
    </div>
  )
}

interface DateRangeInputProps {
  value: [string, string] | undefined
  onChange: (value: [string, string] | undefined) => void
  placeholder?: [string, string]
}

function DateRangeInput({ value, onChange, placeholder = ["Start date", "End date"] }: DateRangeInputProps) {
  const [startDate, endDate] = value || ["", ""]

  const handleStartChange = (newStart: string) => {
    if (newStart || endDate) {
      onChange([newStart, endDate])
    } else {
      onChange(undefined)
    }
  }

  const handleEndChange = (newEnd: string) => {
    if (startDate || newEnd) {
      onChange([startDate, newEnd])
    } else {
      onChange(undefined)
    }
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      <Input
        type="date"
        value={startDate}
        onChange={(e) => handleStartChange(e.target.value)}
        placeholder={placeholder[0]}
      />
      <Input
        type="date"
        value={endDate}
        onChange={(e) => handleEndChange(e.target.value)}
        placeholder={placeholder[1]}
      />
    </div>
  )
}

export function FilterPanel() {
  const {
    activeFilters,
    filterOptions,
    isFilterPanelOpen,
    isLoading,
    error,
    presets,
    activePresetId,
    updateFilter,
    clearFilters,
    setFilterOptions,
    toggleFilterPanel,
    setPresets,
    loadPreset,
    setLoading,
    setError
  } = useFilterStore()

  const [newPresetName, setNewPresetName] = useState("")
  const [showSavePreset, setShowSavePreset] = useState(false)

  // Load filter options and presets on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [options, presetsData] = await Promise.all([
          getFilterOptions(),
          getFilterPresets()
        ])
        setFilterOptions(options)
        setPresets(presetsData)
      } catch (error) {
        setError('Failed to load filter data')
        console.error('Error loading filter data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (isFilterPanelOpen && !filterOptions) {
      loadData()
    }
  }, [isFilterPanelOpen, filterOptions, setFilterOptions, setPresets, setLoading, setError])

  const activeFilterCount = getFilterCount(activeFilters)
  const hasFilters = hasActiveFilters(activeFilters)

  const handleClearFilters = () => {
    clearFilters()
    setShowSavePreset(false)
  }

  const handleSavePreset = async () => {
    if (!newPresetName.trim()) return

    try {
      // Implementation for saving preset would go here
      console.log('Saving preset:', newPresetName, activeFilters)
      setNewPresetName("")
      setShowSavePreset(false)
    } catch (error) {
      console.error('Error saving preset:', error)
    }
  }

  const handleLoadPreset = (preset: FilterPreset) => {
    loadPreset(preset)
  }

  const renderFilterContent = () => (
    <div className="space-y-4">
      {/* Filter Presets */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center justify-between">
            Filter Presets
            {showSavePreset && (
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setShowSavePreset(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Preset List */}
          <div className="grid gap-2 max-h-32 overflow-y-auto">
            {(Array.isArray(presets) ? presets : []).map((preset) => (
              <Button
                key={preset.id}
                variant={activePresetId === preset.id ? "default" : "outline"}
                size="sm"
                className="justify-start text-left h-auto p-2"
                onClick={() => handleLoadPreset(preset)}
              >
                <div>
                  <div className="font-medium">{preset.name}</div>
                  {preset.description && (
                    <div className="text-xs text-muted-foreground">{preset.description}</div>
                  )}
                </div>
              </Button>
            ))}
          </div>

          {/* Save New Preset */}
          {showSavePreset ? (
            <div className="flex gap-2">
              <Input
                placeholder="Preset name"
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSavePreset()}
              />
              <Button size="sm" onClick={handleSavePreset} disabled={!newPresetName.trim()}>
                <Save className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSavePreset(true)}
              disabled={!hasFilters}
              className="w-full"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Current Filters
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Filter Actions */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={handleClearFilters}
          disabled={!hasFilters}
          className="flex-1"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Clear All
        </Button>
        <Select
          value={activeFilters.combination_logic || 'AND'}
          onValueChange={(value: 'AND' | 'OR') => updateFilter('combination_logic', value)}
        >
          <SelectTrigger className="w-20">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="AND">AND</SelectItem>
            <SelectItem value="OR">OR</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Separator />

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="text-muted-foreground">Loading filter options...</div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center py-8">
          <div className="text-destructive">{error}</div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Title Search */}
          <CollapsibleSection 
            title="Search" 
            defaultOpen={!!activeFilters.title_search}
            badge={activeFilters.title_search ? "✓" : undefined}
          >
            <div className="space-y-2">
              <Label>Title Search</Label>
              <Input
                placeholder="Search by title..."
                value={activeFilters.title_search || ""}
                onChange={(e) => updateFilter('title_search', e.target.value || undefined)}
              />
            </div>
          </CollapsibleSection>

          {/* Genres */}
          <CollapsibleSection 
            title="Genres" 
            badge={activeFilters.genres?.length || undefined}
          >
            <MultiSelect
              options={filterOptions?.genres || []}
              selected={activeFilters.genres || []}
              onChange={(selected) => updateFilter('genres', selected.length ? selected : undefined)}
              placeholder="Select genres..."
              searchPlaceholder="Search genres..."
            />
          </CollapsibleSection>

          {/* Tags */}
          <CollapsibleSection 
            title="Tags" 
            badge={activeFilters.tags?.length || undefined}
          >
            <MultiSelect
              options={filterOptions?.tags || []}
              selected={activeFilters.tags || []}
              onChange={(selected) => updateFilter('tags', selected.length ? selected : undefined)}
              placeholder="Select tags..."
              searchPlaceholder="Search tags..."
            />
          </CollapsibleSection>

          {/* Authors */}
          <CollapsibleSection 
            title="Authors" 
            badge={activeFilters.authors?.length || undefined}
          >
            <MultiSelect
              options={filterOptions?.authors || []}
              selected={activeFilters.authors || []}
              onChange={(selected) => updateFilter('authors', selected.length ? selected : undefined)}
              placeholder="Select authors..."
              searchPlaceholder="Search authors..."
            />
          </CollapsibleSection>

          {/* Artists */}
          <CollapsibleSection 
            title="Artists" 
            badge={activeFilters.artists?.length || undefined}
          >
            <MultiSelect
              options={filterOptions?.artists || []}
              selected={activeFilters.artists || []}
              onChange={(selected) => updateFilter('artists', selected.length ? selected : undefined)}
              placeholder="Select artists..."
              searchPlaceholder="Search artists..."
            />
          </CollapsibleSection>

          {/* Status */}
          <CollapsibleSection 
            title="Status" 
            badge={activeFilters.statuses?.length || undefined}
          >
            <MultiSelect
              options={filterOptions?.statuses || []}
              selected={activeFilters.statuses || []}
              onChange={(selected) => updateFilter('statuses', selected.length ? selected : undefined)}
              placeholder="Select status..."
              searchPlaceholder="Search status..."
            />
          </CollapsibleSection>

          {/* Demographics */}
          <CollapsibleSection 
            title="Demographics" 
            badge={activeFilters.demographics?.length || undefined}
          >
            <MultiSelect
              options={filterOptions?.demographics || []}
              selected={activeFilters.demographics || []}
              onChange={(selected) => updateFilter('demographics', selected.length ? selected : undefined)}
              placeholder="Select demographics..."
              searchPlaceholder="Search demographics..."
            />
          </CollapsibleSection>

          {/* Rating Range */}
          <CollapsibleSection 
            title="Rating" 
            badge={activeFilters.rating_range ? "✓" : undefined}
          >
            <div className="space-y-4">
              <Label>Rating Range</Label>
              <div className="px-2">
                <Slider
                  value={activeFilters.rating_range || [filterOptions?.min_rating || 0, filterOptions?.max_rating || 10]}
                  onValueChange={(value) => updateFilter('rating_range', value as [number, number])}
                  min={filterOptions?.min_rating || 0}
                  max={filterOptions?.max_rating || 10}
                  step={0.1}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-muted-foreground mt-1">
                  <span>{(activeFilters.rating_range?.[0] || filterOptions?.min_rating || 0).toFixed(1)}</span>
                  <span>{(activeFilters.rating_range?.[1] || filterOptions?.max_rating || 10).toFixed(1)}</span>
                </div>
              </div>
            </div>
          </CollapsibleSection>

          {/* Year Range */}
          <CollapsibleSection 
            title="Publication Year" 
            badge={activeFilters.year_range ? "✓" : undefined}
          >
            <div className="space-y-4">
              <Label>Year Range</Label>
              <div className="px-2">
                <Slider
                  value={activeFilters.year_range || [filterOptions?.min_year || 1990, filterOptions?.max_year || new Date().getFullYear()]}
                  onValueChange={(value) => updateFilter('year_range', value as [number, number])}
                  min={filterOptions?.min_year || 1990}
                  max={filterOptions?.max_year || new Date().getFullYear()}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-muted-foreground mt-1">
                  <span>{activeFilters.year_range?.[0] || filterOptions?.min_year || 1990}</span>
                  <span>{activeFilters.year_range?.[1] || filterOptions?.max_year || new Date().getFullYear()}</span>
                </div>
              </div>
            </div>
          </CollapsibleSection>

          {/* Date Added Range */}
          <CollapsibleSection 
            title="Date Added" 
            badge={activeFilters.date_added_range ? "✓" : undefined}
          >
            <div className="space-y-2">
              <Label>Date Added Range</Label>
              <DateRangeInput
                value={activeFilters.date_added_range}
                onChange={(value) => updateFilter('date_added_range', value)}
                placeholder={["From date", "To date"]}
              />
            </div>
          </CollapsibleSection>

          {/* Last Read Range */}
          <CollapsibleSection 
            title="Last Read" 
            badge={activeFilters.last_read_range ? "✓" : undefined}
          >
            <div className="space-y-2">
              <Label>Last Read Range</Label>
              <DateRangeInput
                value={activeFilters.last_read_range}
                onChange={(value) => updateFilter('last_read_range', value)}
                placeholder={["From date", "To date"]}
              />
            </div>
          </CollapsibleSection>

          {/* Read Status */}
          <CollapsibleSection 
            title="Read Status" 
            badge={activeFilters.read_status ? "✓" : undefined}
          >
            <Select
              value={activeFilters.read_status || ""}
              onValueChange={(value) => updateFilter('read_status', value || undefined)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select read status..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All</SelectItem>
                <SelectItem value="unread">Unread</SelectItem>
                <SelectItem value="reading">Reading</SelectItem>
                <SelectItem value="read">Read</SelectItem>
              </SelectContent>
            </Select>
          </CollapsibleSection>
        </div>
      )}
    </div>
  )

  return (
    <Sheet open={isFilterPanelOpen} onOpenChange={toggleFilterPanel}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="relative">
          <Filter className="h-4 w-4 mr-2" />
          Filter
          {activeFilterCount > 0 && (
            <Badge 
              variant="secondary" 
              className="ml-2 px-1 py-0 text-xs min-w-[1.2rem] h-5"
            >
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-80 sm:w-96">
        <SheetHeader>
          <SheetTitle>Filter Library</SheetTitle>
          <SheetDescription>
            Refine your manga collection with advanced filtering options.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 h-full overflow-y-auto">
          {renderFilterContent()}
        </div>
      </SheetContent>
    </Sheet>
  )
}