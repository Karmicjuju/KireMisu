'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { MangaReader } from '@/components/reader/MangaReader'
import { useReader } from '@/hooks/useReader'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function ReaderPage() {
  const params = useParams()
  const router = useRouter()
  const reader = useReader()
  
  const seriesId = params.seriesId as string
  const chapterId = parseInt(params.chapterId as string)
  
  useEffect(() => {
    if (chapterId && !isNaN(chapterId)) {
      reader.loadChapter(chapterId)
    }
  }, [chapterId, reader.loadChapter])
  
  // Handle chapter navigation
  useEffect(() => {
    const handleChapterChange = (newChapterId: number) => {
      if (newChapterId !== chapterId) {
        router.push(`/reader/${seriesId}/${newChapterId}`)
      }
    }
    
    // This could be triggered by reader navigation
    return () => {}
  }, [chapterId, seriesId, router])
  
  if (reader.isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center text-white">
          <LoadingSpinner className="mx-auto mb-4" />
          <p>Loading chapter...</p>
        </div>
      </div>
    )
  }
  
  if (reader.error) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <Alert className="max-w-md">
          <AlertDescription className="text-center">
            {reader.error}
          </AlertDescription>
        </Alert>
      </div>
    )
  }
  
  if (!reader.chapterId || reader.pages.length === 0) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <p className="text-white">No chapter data available</p>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-black">
      <MangaReader 
        onChapterChange={(newChapterId) => {
          router.push(`/reader/${seriesId}/${newChapterId}`)
        }}
      />
    </div>
  )
}