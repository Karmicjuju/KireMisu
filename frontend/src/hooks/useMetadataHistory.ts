'use client'

import { useState, useCallback } from 'react'
import {
  getSeriesHistory,
  getChapterHistory,
  restoreSeriesHistory,
  restoreChapterHistory
} from '@/lib/api'
import {
  MetadataHistory
} from '@/types/metadata'

export function useMetadataHistory(entityType: 'series' | 'chapter') {
  const [history, setHistory] = useState<MetadataHistory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchHistory = useCallback(async (entityId: number) => {
    try {
      setIsLoading(true)
      setError(null)
      
      let response
      if (entityType === 'series') {
        response = await getSeriesHistory(entityId)
      } else {
        response = await getChapterHistory(entityId)
      }
      
      setHistory(response.history || [])
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch history'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [entityType])

  const restoreVersion = useCallback(async (entityId: number, historyId: number) => {
    try {
      setIsRestoring(true)
      setError(null)
      
      if (entityType === 'series') {
        await restoreSeriesHistory(entityId, historyId)
      } else {
        await restoreChapterHistory(entityId, historyId)
      }
      
      // Refresh history after restoration
      await fetchHistory(entityId)
      
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to restore version'
      setError(errorMessage)
      throw err
    } finally {
      setIsRestoring(false)
    }
  }, [entityType, fetchHistory])

  const clearHistory = useCallback(() => {
    setHistory([])
    setError(null)
  }, [])

  return {
    history,
    isLoading,
    isRestoring,
    error,
    fetchHistory,
    restoreVersion,
    clearHistory,
    clearError: () => setError(null)
  }
}