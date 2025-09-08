'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Play, Check, Clock, Calendar, ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

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

interface ChapterListProps {
  chapters: Chapter[]
  groupedChapters?: Record<string, Chapter[]>
  seriesId: number
  onChapterRead?: (chapterId: number) => void
  showReadChapters?: boolean
  className?: string
}

interface ChapterItemProps {
  chapter: Chapter
  seriesId: number
  onChapterRead?: (chapterId: number) => void
  className?: string
}

function ChapterItem({ chapter, seriesId, onChapterRead, className }: ChapterItemProps) {
  const handleMarkAsRead = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (onChapterRead) {
      onChapterRead(chapter.id)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const chapterTitle = chapter.title || `Chapter ${chapter.number}`

  return (
    <Card className={cn(
      'p-4 transition-all duration-200 hover:shadow-md group',
      chapter.read_status && 'opacity-60',
      className
    )}>
      <div className="flex items-center gap-3">
        {/* Chapter Status Icon */}
        <div className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          chapter.read_status 
            ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-muted text-muted-foreground'
        )}>
          {chapter.read_status ? (
            <Check className="h-4 w-4" />
          ) : (
            <Clock className="h-4 w-4" />
          )}
        </div>

        {/* Chapter Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Link
              href={`/library/series/${seriesId}/chapter/${chapter.id}`}
              className="font-medium text-foreground hover:text-primary transition-colors group-hover:text-primary"
            >
              {chapterTitle}
            </Link>
            {!chapter.read_status && (
              <Badge variant="secondary" className="text-xs">
                New
              </Badge>
            )}
          </div>
          
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDate(chapter.created_at)}
            </span>
            
            {/* Chapter number badge */}
            <Badge variant="outline" className="text-xs">
              #{chapter.number}
            </Badge>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button asChild size="sm" variant="outline">
            <Link href={`/library/series/${seriesId}/chapter/${chapter.id}`}>
              <Play className="h-3 w-3 mr-1" />
              Read
            </Link>
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={handleMarkAsRead}
            className="text-xs"
          >
            {chapter.read_status ? 'Mark Unread' : 'Mark Read'}
          </Button>
        </div>
      </div>
    </Card>
  )
}

function VolumeGroup({ 
  volume, 
  chapters, 
  seriesId, 
  onChapterRead,
  showReadChapters = true 
}: {
  volume: string
  chapters: Chapter[]
  seriesId: number
  onChapterRead?: (chapterId: number) => void
  showReadChapters?: boolean
}) {
  const [isExpanded, setIsExpanded] = useState(true)
  
  const filteredChapters = showReadChapters 
    ? chapters 
    : chapters.filter(c => !c.read_status)
  
  const readCount = chapters.filter(c => c.read_status).length
  const totalCount = chapters.length
  const progressPercentage = totalCount > 0 ? (readCount / totalCount) * 100 : 0

  if (filteredChapters.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      {/* Volume Header */}
      <div 
        className="flex items-center justify-between p-3 bg-muted/30 rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <h4 className="font-medium">{volume}</h4>
          <Badge variant="secondary" className="text-xs">
            {filteredChapters.length} chapters
          </Badge>
        </div>
        
        {/* Volume Progress */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>{readCount}/{totalCount} read</span>
          <div className="w-16 h-1 bg-secondary rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Volume Chapters */}
      {isExpanded && (
        <div className="space-y-2 pl-4">
          {filteredChapters.map((chapter) => (
            <ChapterItem
              key={chapter.id}
              chapter={chapter}
              seriesId={seriesId}
              onChapterRead={onChapterRead}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function ChapterList({ 
  chapters, 
  groupedChapters,
  seriesId, 
  onChapterRead,
  showReadChapters = true,
  className 
}: ChapterListProps) {
  if (chapters.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No chapters available</p>
      </div>
    )
  }

  // If grouped chapters are provided, use volume grouping
  if (groupedChapters && Object.keys(groupedChapters).length > 1) {
    return (
      <div className={cn('space-y-4', className)}>
        {Object.entries(groupedChapters)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([volume, volumeChapters]) => (
            <VolumeGroup
              key={volume}
              volume={volume}
              chapters={volumeChapters}
              seriesId={seriesId}
              onChapterRead={onChapterRead}
              showReadChapters={showReadChapters}
            />
          ))}
      </div>
    )
  }

  // Regular flat list
  return (
    <div className={cn('space-y-2', className)}>
      {chapters.map((chapter) => (
        <ChapterItem
          key={chapter.id}
          chapter={chapter}
          seriesId={seriesId}
          onChapterRead={onChapterRead}
        />
      ))}
    </div>
  )
}