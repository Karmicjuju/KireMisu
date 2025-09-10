'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Save, Eye, EyeOff } from 'lucide-react'
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
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import {
  Chapter,
  ChapterEditFormData,
  chapterEditSchema,
} from '@/types/metadata'
import { updateChapter } from '@/lib/api'

interface ChapterEditDialogProps {
  chapter: Chapter
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (updatedChapter: Chapter) => void
}

export function ChapterEditDialog({ chapter, open, onOpenChange, onSuccess }: ChapterEditDialogProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  const form = useForm<ChapterEditFormData>({
    resolver: zodResolver(chapterEditSchema),
    defaultValues: {
      number: chapter.number || 0,
      title: chapter.title || '',
      volume_number: chapter.volume_number || undefined,
      description: chapter.description || '',
      release_date: chapter.release_date || '',
      page_count: chapter.page_count || undefined
    }
  })

  // Reset form when chapter changes
  useEffect(() => {
    if (chapter) {
      form.reset({
        number: chapter.number || 0,
        title: chapter.title || '',
        volume_number: chapter.volume_number || undefined,
        description: chapter.description || '',
        release_date: chapter.release_date || '',
        page_count: chapter.page_count || undefined
      })
    }
  }, [chapter, form])

  const handlePreview = async (data: ChapterEditFormData) => {
    try {
      setIsLoading(true)
      const response = await updateChapter(chapter.id, data, true) // preview=true
      console.log('Preview response:', response)
      setShowPreview(true)
    } catch (error) {
      console.error('Preview error:', error)
      alert(`Preview Error: ${error instanceof Error ? error.message : "Failed to generate preview"}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async (data: ChapterEditFormData) => {
    try {
      setIsLoading(true)
      const response = await updateChapter(chapter.id, data, false)
      
      alert("Chapter metadata has been successfully updated.")
      
      if (onSuccess) {
        onSuccess(response.chapter)
      }
      
      onOpenChange(false)
    } catch (error) {
      console.error('Update error:', error)
      alert(`Update Error: ${error instanceof Error ? error.message : "Failed to update chapter"}`)
    } finally {
      setIsLoading(false)
    }
  }

  const onSubmit = async (data: ChapterEditFormData) => {
    if (showPreview) {
      await handleSave(data)
    } else {
      await handlePreview(data)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit Chapter Metadata</DialogTitle>
          <DialogDescription>
            Modify the metadata for Chapter {chapter.number}. Click Preview to see changes before saving.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Chapter Number */}
              <FormField
                control={form.control}
                name="number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Chapter Number *</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.1"
                        placeholder="1"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Volume Number */}
              <FormField
                control={form.control}
                name="volume_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Volume Number</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="1"
                        {...field}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Title */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Chapter Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter chapter title" {...field} />
                  </FormControl>
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
                      placeholder="Enter chapter description..."
                      className="min-h-[80px]"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              {/* Release Date */}
              <FormField
                control={form.control}
                name="release_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Release Date</FormLabel>
                    <FormControl>
                      <Input
                        type="date"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      When this chapter was originally released
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Page Count */}
              <FormField
                control={form.control}
                name="page_count"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Page Count</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="1"
                        placeholder="20"
                        {...field}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

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
      </DialogContent>
    </Dialog>
  )
}