'use client'

import { useState, useMemo } from 'react'
import Image from 'next/image'
import { ArrowLeft, BookOpen, Clock, Star, MoreVertical, Play, Plus, Check, Eye, EyeOff, Edit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Toggle } from '@/components/ui/toggle'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { ChapterList } from './ChapterList'
import { SeriesEditDialog } from '@/components/metadata/SeriesEditDialog'
import { cn } from '@/lib/utils'
import Link from 'next/link'

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

interface Chapter {
  id: number
  series_id: number
  number: number
  title?: string
  file_path: string
  read_status: boolean
  created_at: string
  updated_at?: string
}

interface SeriesDetailProps {
  series: Series
  chapters?: Chapter[]
  isLoading?: boolean
  error?: string | null
  onChapterRead?: (chapterId: number) => void
  onSeriesMarkRead?: (seriesId: number) => void
  onAddToList?: (seriesId: number) => void
  className?: string
}

type SortOption = 'number-asc' | 'number-desc' | 'title-asc' | 'title-desc' | 'date-asc' | 'date-desc'

export function SeriesDetail({
  series,
  chapters = [],
  isLoading = false,
  error = null,
  onChapterRead,
  onSeriesMarkRead,
  onAddToList,
  className
}: SeriesDetailProps) {
  const [imageError, setImageError] = useState(false)
  const [sortBy, setSortBy] = useState<SortOption>('number-asc')
  const [showReadChapters, setShowReadChapters] = useState(true)
  const [expandedDescription, setExpandedDescription] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)

  // Calculate reading statistics
  const readingStats = useMemo(() => {
    const totalChapters = chapters.length
    const readChapters = chapters.filter(c => c.read_status).length
    const progressPercentage = totalChapters > 0 ? (readChapters / totalChapters) * 100 : 0
    const lastReadChapter = chapters
      .filter(c => c.read_status)
      .sort((a, b) => b.number - a.number)[0]

    return {
      totalChapters,
      readChapters,
      progressPercentage,
      lastReadChapter,
      isCompleted: readChapters === totalChapters && totalChapters > 0
    }
  }, [chapters])

  // Sort chapters
  const sortedChapters = useMemo(() => {
    let sorted = [...chapters]
    
    switch (sortBy) {
      case 'number-desc':
        sorted = sorted.sort((a, b) => b.number - a.number)
        break
      case 'title-asc':
        sorted = sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''))
        break
      case 'title-desc':
        sorted = sorted.sort((a, b) => (b.title || '').localeCompare(a.title || ''))
        break
      case 'date-asc':
        sorted = sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
        break
      case 'date-desc':
        sorted = sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        break
      case 'number-asc':
      default:
        sorted = sorted.sort((a, b) => a.number - b.number)
        break
    }

    // Filter by read status if needed
    if (!showReadChapters) {
      sorted = sorted.filter(c => !c.read_status)
    }

    return sorted
  }, [chapters, sortBy, showReadChapters])

  // Group chapters by volume (if volume info is available in metadata)
  const groupedChapters = useMemo(() => {
    const groups: Record<string, Chapter[]> = {}
    
    sortedChapters.forEach(chapter => {
      // Try to extract volume from chapter number or metadata
      let volume = 'Volume 1' // Default volume
      
      if (chapter.number >= 1 && chapter.number < 50) {
        volume = `Volume ${Math.ceil(chapter.number / 10)}`
      }
      
      if (!groups[volume]) {
        groups[volume] = []
      }
      groups[volume].push(chapter)
    })

    return groups
  }, [sortedChapters])

  const handleImageError = () => {
    setImageError(true)
  }

  const handleMarkAsRead = () => {
    if (onSeriesMarkRead) {
      onSeriesMarkRead(series.id)
    }
  }

  const handleAddToList = () => {
    if (onAddToList) {
      onAddToList(series.id)
    }
  }

  // Find next unread chapter
  const nextUnreadChapter = chapters
    .filter(c => !c.read_status)
    .sort((a, b) => a.number - b.number)[0]

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="rounded-full bg-destructive/10 p-6 mb-4">
          <BookOpen className="h-12 w-12 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold mb-2 text-destructive">
          Failed to load series
        </h3>
        <p className="text-muted-foreground mb-4 max-w-md">
          {error}
        </p>
        <Button asChild variant="outline">
          <Link href="/library">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Library
          </Link>
        </Button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        {/* Loading skeleton */}
        <div className="flex gap-6">
          <Skeleton className="w-64 aspect-[3/4] flex-shrink-0" />
          <div className="flex-1 space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>
        </div>
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button asChild variant="ghost" size="sm">
          <Link href="/library">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Library
          </Link>
        </Button>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cover and Basic Info */}
        <div className="lg:col-span-1">
          <Card>
            <CardContent className="p-6">
              {/* Cover Image */}
              <div className="relative aspect-[3/4] w-full mb-4 overflow-hidden rounded-lg">
                {series.cover_path && !imageError ? (
                  <Image
                    src={series.cover_path}
                    alt={`Cover for ${series.title}`}
                    fill
                    className="object-cover"
                    sizes="(max-width: 1024px) 100vw, 33vw"
                    onError={handleImageError}
                    priority
                  />
                ) : (
                  <div className="w-full h-full bg-muted flex items-center justify-center">
                    <BookOpen className="h-16 w-16 text-muted-foreground" />
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                {nextUnreadChapter ? (
                  <Button asChild className="w-full">
                    <Link href={`/library/series/${series.id}/chapter/${nextUnreadChapter.id}`}>
                      <Play className="h-4 w-4 mr-2" />
                      Continue Reading
                    </Link>
                  </Button>
                ) : readingStats.isCompleted ? (
                  <Button disabled className="w-full">
                    <Check className="h-4 w-4 mr-2" />
                    Completed
                  </Button>
                ) : (
                  <Button asChild className="w-full">
                    <Link href={`/library/series/${series.id}/chapter/${chapters[0]?.id}`}>
                      <Play className="h-4 w-4 mr-2" />
                      Start Reading
                    </Link>
                  </Button>
                )}

                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleMarkAsRead} className="flex-1">
                    <Check className="h-4 w-4 mr-2" />
                    Mark as Read
                  </Button>
                  <Button variant="outline" onClick={handleAddToList} className="flex-1">
                    <Plus className="h-4 w-4 mr-2" />
                    Add to List
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem onClick={() => setEditDialogOpen(true)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit Metadata
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        Refresh from MangaDex
                      </DropdownMenuItem>
                      <DropdownMenuItem className="text-destructive">
                        Remove from Library
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              {/* Reading Progress */}
              {chapters.length > 0 && (
                <Card className="mt-4">
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Reading Progress</span>
                        <span>{Math.round(readingStats.progressPercentage)}%</span>
                      </div>
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div 
                          className="bg-primary h-2 rounded-full transition-all duration-500"
                          style={{ width: `${readingStats.progressPercentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {readingStats.readChapters} of {readingStats.totalChapters} chapters
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Metadata and Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Title and Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-3xl">{series.title}</CardTitle>
              <div className="flex flex-wrap gap-2">
                {series.author && (
                  <Badge variant="outline">
                    Author: {series.author}
                  </Badge>
                )}
                {series.artist && series.artist !== series.author && (
                  <Badge variant="outline">
                    Artist: {series.artist}
                  </Badge>
                )}
                {series.status && (
                  <Badge 
                    variant={series.status === 'completed' ? 'default' : 'secondary'}
                  >
                    {series.status}
                  </Badge>
                )}
              </div>
            </CardHeader>
            {series.description && (
              <CardContent>
                <div className="prose prose-sm max-w-none">
                  <p className={cn(
                    'text-muted-foreground leading-relaxed',
                    !expandedDescription && 'line-clamp-3'
                  )}>
                    {series.description}
                  </p>
                  {series.description.length > 200 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedDescription(!expandedDescription)}
                      className="mt-2 p-0 h-auto"
                    >
                      {expandedDescription ? 'Show less' : 'Show more'}
                    </Button>
                  )}
                </div>
              </CardContent>
            )}
          </Card>

          {/* Chapter List */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Chapters ({chapters.length})
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Toggle
                    pressed={showReadChapters}
                    onPressedChange={setShowReadChapters}
                    size="sm"
                    aria-label="Show read chapters"
                  >
                    {showReadChapters ? (
                      <Eye className="h-4 w-4" />
                    ) : (
                      <EyeOff className="h-4 w-4" />
                    )}
                  </Toggle>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as SortOption)}
                    className="px-3 py-1 text-sm border rounded-md bg-background"
                  >
                    <option value="number-asc">Chapter ↑</option>
                    <option value="number-desc">Chapter ↓</option>
                    <option value="title-asc">Title A-Z</option>
                    <option value="title-desc">Title Z-A</option>
                    <option value="date-asc">Date ↑</option>
                    <option value="date-desc">Date ↓</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {chapters.length > 0 ? (
                <ChapterList
                  chapters={sortedChapters}
                  groupedChapters={groupedChapters}
                  seriesId={series.id}
                  onChapterRead={onChapterRead}
                  showReadChapters={showReadChapters}
                />
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <BookOpen className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No chapters found for this series.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Dialog */}
      <SeriesEditDialog
        series={series}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSuccess={(updatedSeries) => {
          // You could update the local state here if needed
          console.log('Series updated:', updatedSeries)
        }}
      />
    </div>
  )
}