'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { X, Save, Eye, EyeOff, Plus } from 'lucide-react'
import { sanitizeText, sanitizeArray, sanitizeMetadataForm, clientRateLimit } from '@/lib/security'
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
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
// import { useToast } from '@/hooks/use-toast'
import {
  Series,
  SeriesEditFormData,
  seriesEditSchema,
  COMMON_GENRES,
  SERIES_STATUS_OPTIONS
} from '@/types/metadata'
import { updateSeries } from '@/lib/api'

interface SeriesEditDialogProps {
  series: Series
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (updatedSeries: Series) => void
}

interface TagInputProps {
  tags: string[]
  onTagsChange: (tags: string[]) => void
  suggestions?: string[]
  placeholder?: string
  label?: string
}

// Security utilities are now imported from @/lib/security

function TagInput({ tags, onTagsChange, suggestions = [], placeholder, label }: TagInputProps) {
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)

  const filteredSuggestions = suggestions.filter(
    suggestion => 
      suggestion.toLowerCase().includes(inputValue.toLowerCase()) &&
      !tags.includes(suggestion)
  ).map(suggestion => sanitizeText(suggestion))

  const addTag = (tag: string) => {
    const sanitizedTag = sanitizeText(tag.trim())
    if (sanitizedTag && !tags.includes(sanitizedTag)) {
      onTagsChange([...tags, sanitizedTag])
    }
    setInputValue('')
    setShowSuggestions(false)
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
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
      removeTag(tags[tags.length - 1])
    }
  }

  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-medium">{label}</label>
      )}
      
      {/* Display current tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {tags.map((tag, index) => (
            <Badge key={index} variant="secondary" className="text-xs">
              {sanitizeText(tag)}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Input field */}
      <div className="relative">
        <Input
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value)
            setShowSuggestions(e.target.value.length > 0)
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowSuggestions(inputValue.length > 0)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          placeholder={placeholder}
        />

        {/* Suggestions dropdown */}
        {showSuggestions && filteredSuggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-48 overflow-auto rounded-md border bg-popover shadow-md">
            {filteredSuggestions.slice(0, 10).map((suggestion, index) => (
              <button
                key={index}
                type="button"
                className="w-full px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                onClick={() => addTag(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function SeriesEditDialog({ series, open, onOpenChange, onSuccess }: SeriesEditDialogProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewData, setPreviewData] = useState<Series | null>(null)
  // const { toast } = useToast()

  const form = useForm<SeriesEditFormData>({
    resolver: zodResolver(seriesEditSchema),
    defaultValues: {
      title: series.title || '',
      author: series.author || '',
      artist: series.artist || '',
      description: series.description || '',
      status: series.status,
      cover_url: series.cover_path || '',
      genres: series.genres || [],
      tags: series.tags || []
    }
  })

  // Reset form when series changes
  useEffect(() => {
    if (series) {
      form.reset({
        title: series.title || '',
        author: series.author || '',
        artist: series.artist || '',
        description: series.description || '',
        status: series.status,
        cover_url: series.cover_path || '',
        genres: series.genres || [],
        tags: series.tags || []
      })
    }
  }, [series, form])

  const handlePreview = async (data: SeriesEditFormData) => {
    // Client-side rate limiting to prevent abuse
    if (!clientRateLimit.isAllowed('series-preview', 5, 60000)) {
      alert('Too many preview requests. Please wait a moment before trying again.')
      return
    }
    
    try {
      setIsLoading(true)
      // Sanitize form data before sending to backend
      const sanitizedData = sanitizeMetadataForm(data)
      const response = await updateSeries(series.id, sanitizedData, true) // preview=true
      setPreviewData(response.preview || response.series)
      setShowPreview(true)
    } catch (error) {
      console.error('Preview error:', error)
      alert(`Preview Error: ${error instanceof Error ? error.message : "Failed to generate preview"}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async (data: SeriesEditFormData) => {
    // Client-side rate limiting to prevent abuse
    if (!clientRateLimit.isAllowed('series-save', 3, 60000)) {
      alert('Too many save requests. Please wait a moment before trying again.')
      return
    }
    
    try {
      setIsLoading(true)
      // Sanitize form data before sending to backend
      const sanitizedData = sanitizeMetadataForm(data)
      const response = await updateSeries(series.id, sanitizedData, false)
      
      alert("Series metadata has been successfully updated.")
      
      if (onSuccess) {
        onSuccess(response.series)
      }
      
      onOpenChange(false)
    } catch (error) {
      console.error('Update error:', error)
      alert(`Update Error: ${error instanceof Error ? error.message : "Failed to update series"}`)
    } finally {
      setIsLoading(false)
    }
  }

  const onSubmit = async (data: SeriesEditFormData) => {
    if (showPreview) {
      await handleSave(data)
    } else {
      await handlePreview(data)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Series Metadata</DialogTitle>
          <DialogDescription>
            Modify the metadata for "{series.title}". Click Preview to see changes before saving.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Form Section */}
          <div className="space-y-4">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                {/* Title */}
                <FormField
                  control={form.control}
                  name="title"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Title *</FormLabel>
                      <FormControl>
                        <Input placeholder="Enter series title" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Author */}
                <FormField
                  control={form.control}
                  name="author"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Author</FormLabel>
                      <FormControl>
                        <Input placeholder="Enter author name" {...field} />
                      </FormControl>
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
                        <Input placeholder="Enter artist name" {...field} />
                      </FormControl>
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
                          <option value="">Select status</option>
                          {SERIES_STATUS_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Cover URL */}
                <FormField
                  control={form.control}
                  name="cover_url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cover Image URL</FormLabel>
                      <FormControl>
                        <Input placeholder="https://..." {...field} />
                      </FormControl>
                      <FormDescription>
                        URL to the cover image for this series
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Description */}
                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Enter series description..."
                          className="min-h-[100px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Genres */}
                <FormField
                  control={form.control}
                  name="genres"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <TagInput
                          label="Genres"
                          tags={field.value}
                          onTagsChange={field.onChange}
                          suggestions={COMMON_GENRES}
                          placeholder="Add genres (press Enter or comma to add)"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Custom Tags */}
                <FormField
                  control={form.control}
                  name="tags"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <TagInput
                          label="Custom Tags"
                          tags={field.value}
                          onTagsChange={field.onChange}
                          placeholder="Add custom tags (press Enter or comma to add)"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Form Buttons */}
                <DialogFooter className="gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => onOpenChange(false)}
                    disabled={isLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowPreview(!showPreview)}
                    disabled={isLoading}
                  >
                    {showPreview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                    {showPreview ? 'Hide Preview' : 'Show Preview'}
                  </Button>
                  <Button type="submit" disabled={isLoading}>
                    {isLoading && <LoadingSpinner className="h-4 w-4 mr-2" />}
                    {showPreview ? (
                      <>
                        <Save className="h-4 w-4 mr-2" />
                        Save Changes
                      </>
                    ) : (
                      <>
                        <Eye className="h-4 w-4 mr-2" />
                        Preview Changes
                      </>
                    )}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </div>

          {/* Preview Section */}
          {showPreview && previewData && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Preview</h3>
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">{sanitizeText(previewData.title)}</CardTitle>
                  <div className="flex flex-wrap gap-2">
                    {previewData.author && (
                      <Badge variant="outline">Author: {sanitizeText(previewData.author)}</Badge>
                    )}
                    {previewData.artist && previewData.artist !== previewData.author && (
                      <Badge variant="outline">Artist: {sanitizeText(previewData.artist)}</Badge>
                    )}
                    {previewData.status && (
                      <Badge variant={previewData.status === 'completed' ? 'default' : 'secondary'}>
                        {sanitizeText(previewData.status)}
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {previewData.description && (
                    <div className="mb-4">
                      <h4 className="font-medium mb-2">Description</h4>
                      <p className="text-sm text-muted-foreground">
                        {sanitizeText(previewData.description)}
                      </p>
                    </div>
                  )}
                  
                  {previewData.genres && previewData.genres.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-medium mb-2">Genres</h4>
                      <div className="flex flex-wrap gap-1">
                        {sanitizeArray(previewData.genres).map((genre, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {genre}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {previewData.tags && previewData.tags.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-medium mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-1">
                        {sanitizeArray(previewData.tags).map((tag, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}