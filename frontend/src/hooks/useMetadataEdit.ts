'use client'

import { useState, useCallback } from 'react'
import {
  updateSeries,
  updateChapter,
  bulkUpdateSeries,
  bulkUpdateChapters
} from '@/lib/api'
import {
  Series,
  Chapter,
  SeriesEditFormData,
  ChapterEditFormData,
  BulkEditFormData
} from '@/types/metadata'

export function useSeriesEdit() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const editSeries = useCallback(async (
    seriesId: number,
    data: SeriesEditFormData,
    preview: boolean = false
  ) => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await updateSeries(seriesId, data, preview)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update series'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const bulkEditSeries = useCallback(async (
    seriesIds: number[],
    data: BulkEditFormData
  ) => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await bulkUpdateSeries(seriesIds, data)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to bulk update series'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    editSeries,
    bulkEditSeries,
    isLoading,
    error,
    clearError: () => setError(null)
  }
}

export function useChapterEdit() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const editChapter = useCallback(async (
    chapterId: number,
    data: ChapterEditFormData,
    preview: boolean = false
  ) => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await updateChapter(chapterId, data, preview)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update chapter'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const bulkEditChapters = useCallback(async (
    chapterIds: number[],
    data: any
  ) => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await bulkUpdateChapters(chapterIds, data)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to bulk update chapters'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    editChapter,
    bulkEditChapters,
    isLoading,
    error,
    clearError: () => setError(null)
  }
}

export function useMetadataEdit() {
  const seriesHook = useSeriesEdit()
  const chapterHook = useChapterEdit()

  return {
    series: seriesHook,
    chapter: chapterHook,
    isLoading: seriesHook.isLoading || chapterHook.isLoading
  }
}