'use client'

import { useState, useEffect } from 'react'
import { History, RotateCcw, Calendar, User } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  MetadataHistory,
  SeriesHistory,
  ChapterHistory,
} from '@/types/metadata'
import { getSeriesHistory, getChapterHistory, restoreSeriesHistory, restoreChapterHistory } from '@/lib/api'

interface MetadataHistoryProps {
  entityType: 'series' | 'chapter'
  entityId: number
  entityTitle: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onRestore?: () => void
}

export function MetadataHistory({
  entityType,
  entityId,
  entityTitle,
  open,
  onOpenChange,
  onRestore
}: MetadataHistoryProps) {
  const [history, setHistory] = useState<MetadataHistory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isRestoring, setIsRestoring] = useState<number | null>(null)

  useEffect(() => {
    if (open && entityId) {
      fetchHistory()
    }
  }, [open, entityId, entityType])

  const fetchHistory = async () => {
    try {
      setIsLoading(true)
      let response
      
      if (entityType === 'series') {
        response = await getSeriesHistory(entityId)
      } else {
        response = await getChapterHistory(entityId)
      }
      
      setHistory(response.history || [])
    } catch (error) {
      console.error('Failed to fetch history:', error)
      alert(`Failed to load history: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRestore = async (historyId: number) => {
    try {
      setIsRestoring(historyId)
      
      if (entityType === 'series') {
        await restoreSeriesHistory(entityId, historyId)
      } else {
        await restoreChapterHistory(entityId, historyId)
      }
      
      alert('Successfully restored to this version!')
      
      if (onRestore) {
        onRestore()
      }
      
      onOpenChange(false)
    } catch (error) {
      console.error('Failed to restore:', error)
      alert(`Failed to restore: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsRestoring(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatValue = (value: any) => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">Empty</span>
    }
    
    if (Array.isArray(value)) {
      return value.length > 0 ? value.join(', ') : <span className="text-muted-foreground italic">Empty</span>
    }
    
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No'
    }
    
    if (typeof value === 'string' && value.length > 50) {
      return (
        <div className="space-y-1">
          <div className="line-clamp-2">{value}</div>
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">Show full text</summary>
            <div className="mt-2 p-2 bg-muted rounded text-foreground whitespace-pre-wrap">
              {value}
            </div>
          </details>
        </div>
      )
    }
    
    return String(value)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Change History - {entityTitle}
          </DialogTitle>
          <DialogDescription>
            View and restore previous versions of this {entityType}'s metadata.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner className="h-8 w-8" />
              <span className="ml-2">Loading history...</span>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold mb-2">No History Found</h3>
              <p>No changes have been recorded for this {entityType} yet.</p>
            </div>
          ) : (
            <ScrollArea className="h-[500px] pr-4">
              <div className="space-y-4">
                {history.map((entry) => (
                  <Card key={entry.id} className="relative">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                          {entry.field_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </CardTitle>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            <Calendar className="h-3 w-3 mr-1" />
                            {formatDate(entry.timestamp)}
                          </Badge>
                          {entry.changed_by && (
                            <Badge variant="outline" className="text-xs">
                              <User className="h-3 w-3 mr-1" />
                              {entry.changed_by}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-muted-foreground mb-2">Previous Value</h4>
                          <div className="text-sm p-2 bg-red-50 dark:bg-red-950/20 rounded border-l-2 border-red-200 dark:border-red-800">
                            {formatValue(entry.old_value)}
                          </div>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-muted-foreground mb-2">New Value</h4>
                          <div className="text-sm p-2 bg-green-50 dark:bg-green-950/20 rounded border-l-2 border-green-200 dark:border-green-800">
                            {formatValue(entry.new_value)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="mt-3 flex justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRestore(entry.id)}
                          disabled={isRestoring === entry.id}
                          className="text-xs"
                        >
                          {isRestoring === entry.id ? (
                            <>
                              <LoadingSpinner className="h-3 w-3 mr-1" />
                              Restoring...
                            </>
                          ) : (
                            <>
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Restore to this version
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={fetchHistory} disabled={isLoading}>
            Refresh History
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}