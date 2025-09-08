'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { SeriesDetail } from '@/components/library/SeriesDetail'
import { useSeriesById } from '@/hooks/useSeries'

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

export default function SeriesDetailPage() {
  const params = useParams()
  const seriesId = parseInt(params.id as string)
  
  const { series, isLoading, error, refetch } = useSeriesById(seriesId)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chaptersLoading, setChaptersLoading] = useState(false)
  const [chaptersError, setChaptersError] = useState<string | null>(null)

  // Mock chapters data for now (this would come from the chapters API)
  useEffect(() => {
    if (series) {
      setChaptersLoading(true)
      // Simulate API call for chapters
      setTimeout(() => {
        const mockChapters: Chapter[] = [
          {
            id: 1,
            series_id: seriesId,
            number: 1,
            title: 'The Beginning',
            file_path: '/manga/series1/ch1.cbz',
            read_status: true,
            created_at: '2024-01-01T00:00:00Z'
          },
          {
            id: 2,
            series_id: seriesId,
            number: 2,
            title: 'The Journey Continues',
            file_path: '/manga/series1/ch2.cbz',
            read_status: true,
            created_at: '2024-01-02T00:00:00Z'
          },
          {
            id: 3,
            series_id: seriesId,
            number: 3,
            title: 'New Challenges',
            file_path: '/manga/series1/ch3.cbz',
            read_status: false,
            created_at: '2024-01-03T00:00:00Z'
          },
          {
            id: 4,
            series_id: seriesId,
            number: 4,
            title: 'The Plot Thickens',
            file_path: '/manga/series1/ch4.cbz',
            read_status: false,
            created_at: '2024-01-04T00:00:00Z'
          },
          {
            id: 5,
            series_id: seriesId,
            number: 5,
            title: 'Climax Approaches',
            file_path: '/manga/series1/ch5.cbz',
            read_status: false,
            created_at: '2024-01-05T00:00:00Z'
          }
        ]
        setChapters(mockChapters)
        setChaptersLoading(false)
      }, 1000)
    }
  }, [series, seriesId])

  const handleChapterRead = async (chapterId: number) => {
    // Update chapter read status
    setChapters(prev => prev.map(chapter => 
      chapter.id === chapterId 
        ? { ...chapter, read_status: !chapter.read_status }
        : chapter
    ))

    // Here you would make an API call to update the read status
    try {
      // await updateChapterReadStatus(chapterId, !chapter.read_status)
      console.log(`Toggling read status for chapter ${chapterId}`)
    } catch (error) {
      console.error('Failed to update chapter read status:', error)
      // Revert the optimistic update on error
      setChapters(prev => prev.map(chapter => 
        chapter.id === chapterId 
          ? { ...chapter, read_status: !chapter.read_status }
          : chapter
      ))
    }
  }

  const handleSeriesMarkRead = async (seriesId: number) => {
    // Mark all chapters as read
    setChapters(prev => prev.map(chapter => ({ ...chapter, read_status: true })))
    
    try {
      // await markSeriesAsRead(seriesId)
      console.log(`Marking series ${seriesId} as read`)
    } catch (error) {
      console.error('Failed to mark series as read:', error)
      // Revert on error
      refetch()
    }
  }

  const handleAddToList = async (seriesId: number) => {
    try {
      // await addSeriesToList(seriesId, listId)
      console.log(`Adding series ${seriesId} to list`)
    } catch (error) {
      console.error('Failed to add series to list:', error)
    }
  }

  // Show error if series ID is invalid
  if (!seriesId || isNaN(seriesId)) {
    return (
      <ProtectedRoute>
        <div className="p-6">
          <div className="text-center py-12">
            <h1 className="text-2xl font-bold text-destructive mb-2">
              Invalid Series ID
            </h1>
            <p className="text-muted-foreground">
              The series ID provided is not valid.
            </p>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="p-6">
        {series && (
          <SeriesDetail
            series={series}
            chapters={chapters}
            isLoading={isLoading || chaptersLoading}
            error={error || chaptersError}
            onChapterRead={handleChapterRead}
            onSeriesMarkRead={handleSeriesMarkRead}
            onAddToList={handleAddToList}
          />
        )}
      </div>
    </ProtectedRoute>
  )
}