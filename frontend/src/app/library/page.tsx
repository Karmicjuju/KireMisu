'use client'

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { LibraryGrid } from "@/components/library/LibraryGrid"
import { useSeries } from "@/hooks/useSeries"
import { Button } from "@/components/ui/button"
import { RefreshCw, Plus } from "lucide-react"

export default function LibraryPage() {
  const { series, isLoading, error, refetch, setSearch } = useSeries({
    size: 50, // Load more items for better grid display
  })

  return (
    <ProtectedRoute>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Library</h1>
            <p className="text-muted-foreground">
              Browse and manage your manga collection
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={refetch}
              disabled={isLoading}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            
            <Button size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Add Series
            </Button>
          </div>
        </div>

        {/* Library Grid */}
        <LibraryGrid
          series={series}
          isLoading={isLoading}
          error={error}
          onSearch={setSearch}
          onRefresh={refetch}
        />
      </div>
    </ProtectedRoute>
  )
}