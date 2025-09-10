'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Save, Plus, Minus } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Checkbox } from '@/components/ui/checkbox'
import {
  BulkEditFormData,
  bulkEditSchema,
  COMMON_GENRES,
  SERIES_STATUS_OPTIONS
} from '@/types/metadata'
import { bulkUpdateSeries } from '@/lib/api'

interface BulkEditDialogProps {
  selectedIds: number[]
  selectedTitles: string[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

interface TagInputProps {
  tags: string[]
  onTagsChange: (tags: string[]) => void
  suggestions?: string[]
  placeholder?: string
}

function TagInput({ tags, onTagsChange, suggestions = [], placeholder }: TagInputProps) {
  const [inputValue, setInputValue] = useState('')

  const addTag = (tag: string) => {
    if (tag.trim() && !tags.includes(tag.trim())) {
      onTagsChange([...tags, tag.trim()])
    }
    setInputValue('')
  }

  const removeTag = (tagToRemove: string) => {
    onTagsChange(tags.filter(tag => tag !== tagToRemove))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      if (inputValue.trim()) {
        addTag(inputValue.trim())
      }
    }
  }

  return (
    <div className="space-y-2">
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag, index) => (
            <Badge key={index} variant="secondary" className="text-xs">
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="ml-1 hover:text-destructive"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      )}
      <Input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
      />
    </div>
  )
}

export function BulkEditDialog({
  selectedIds,
  selectedTitles,
  open,
  onOpenChange,
  onSuccess
}: BulkEditDialogProps) {
  const [isLoading, setIsLoading] = useState(false)

  const form = useForm<BulkEditFormData>({
    resolver: zodResolver(bulkEditSchema),
    defaultValues: {
      author: '',
      artist: '',
      status: undefined,
      genres: [],
      tags: [],
      addGenres: [],
      removeGenres: [],
      addTags: [],
      removeTags: []
    }
  })

  const handleSave = async (data: BulkEditFormData) => {
    try {
      setIsLoading(true)
      
      // Filter out empty values
      const updateData = Object.fromEntries(
        Object.entries(data).filter(([_, value]) => {
          if (Array.isArray(value)) {
            return value.length > 0
          }
          return value !== '' && value !== undefined && value !== null
        })
      )

      if (Object.keys(updateData).length === 0) {
        alert('Please select at least one field to update.')
        return
      }

      await bulkUpdateSeries(selectedIds, updateData)
      
      alert(`Successfully updated ${selectedIds.length} series.`)
      
      if (onSuccess) {
        onSuccess()
      }
      
      onOpenChange(false)
    } catch (error) {
      console.error('Bulk update error:', error)
      alert(`Bulk Update Error: ${error instanceof Error ? error.message : "Failed to update series"}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Bulk Edit Metadata</DialogTitle>
          <DialogDescription>
            Update metadata for {selectedIds.length} selected series. Only filled fields will be updated.
          </DialogDescription>
        </DialogHeader>

        {/* Selected Items Preview */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-sm">Selected Series ({selectedIds.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-20 overflow-y-auto">
              <div className="flex flex-wrap gap-1">
                {selectedTitles.slice(0, 10).map((title, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {title}
                  </Badge>
                ))}
                {selectedTitles.length > 10 && (
                  <Badge variant="secondary" className="text-xs">
                    +{selectedTitles.length - 10} more
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSave)} className="space-y-4">
            {/* Author */}
            <FormField
              control={form.control}
              name="author"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Author</FormLabel>
                  <FormControl>
                    <Input placeholder="Leave empty to keep current values" {...field} />
                  </FormControl>
                  <FormDescription>
                    Set the author for all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Artist */}
            <FormField
              control={form.control}
              name="artist"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Artist</FormLabel>
                  <FormControl>
                    <Input placeholder="Leave empty to keep current values" {...field} />
                  </FormControl>
                  <FormDescription>
                    Set the artist for all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Status */}
            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <FormControl>
                    <select
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      {...field}
                    >
                      <option value="">Keep current status</option>
                      {SERIES_STATUS_OPTIONS.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormDescription>
                    Set the status for all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Add Genres */}
            <FormField
              control={form.control}
              name="addGenres"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Add Genres</FormLabel>
                  <FormControl>
                    <TagInput
                      tags={field.value}
                      onTagsChange={field.onChange}
                      suggestions={COMMON_GENRES}
                      placeholder="Add genres to all selected series"
                    />
                  </FormControl>
                  <FormDescription>
                    These genres will be added to all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Remove Genres */}
            <FormField
              control={form.control}
              name="removeGenres"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Remove Genres</FormLabel>
                  <FormControl>
                    <TagInput
                      tags={field.value}
                      onTagsChange={field.onChange}
                      suggestions={COMMON_GENRES}
                      placeholder="Remove genres from all selected series"
                    />
                  </FormControl>
                  <FormDescription>
                    These genres will be removed from all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Add Tags */}
            <FormField
              control={form.control}
              name="addTags"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Add Custom Tags</FormLabel>
                  <FormControl>
                    <TagInput
                      tags={field.value}
                      onTagsChange={field.onChange}
                      placeholder="Add custom tags to all selected series"
                    />
                  </FormControl>
                  <FormDescription>
                    These tags will be added to all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Remove Tags */}
            <FormField
              control={form.control}
              name="removeTags"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Remove Custom Tags</FormLabel>
                  <FormControl>
                    <TagInput
                      tags={field.value}
                      onTagsChange={field.onChange}
                      placeholder="Remove custom tags from all selected series"
                    />
                  </FormControl>
                  <FormDescription>
                    These tags will be removed from all selected series
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <LoadingSpinner className="h-4 w-4 mr-2" />}
                <Save className="h-4 w-4 mr-2" />
                Update {selectedIds.length} Series
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}