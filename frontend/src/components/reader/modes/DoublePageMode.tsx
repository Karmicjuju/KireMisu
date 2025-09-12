'use client'

import React, { useEffect, useRef } from 'react'
import { ReaderSettings, PageInfo } from '@/lib/reader-store'
import { cn } from '@/lib/utils'

interface DoublePageModeProps {
  chapterId: number
  leftPage: PageInfo | null
  rightPage: PageInfo | null
  settings: ReaderSettings
  onPageLoad?: (pageIndex: number) => void
  onPageError?: (pageIndex: number, error: string) => void
  className?: string
}

export function DoublePageMode({
  chapterId,
  leftPage,
  rightPage,
  settings,
  onPageLoad,
  onPageError,
  className
}: DoublePageModeProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Handle image load
  const handleImageLoad = (pageIndex: number) => {
    if (onPageLoad) {
      onPageLoad(pageIndex)
    }
  }

  // Handle image error
  const handleImageError = (pageIndex: number, page: PageInfo) => {
    const errorMsg = `Failed to load page ${page.index + 1}`
    if (onPageError) {
      onPageError(pageIndex, errorMsg)
    }
  }

  // Calculate spread layout based on reading direction
  const getPageOrder = () => {
    if (settings.readingDirection === 'rtl') {
      // Right-to-left: right page first, then left
      return { first: rightPage, second: leftPage }
    } else {
      // Left-to-right: left page first, then right
      return { first: leftPage, second: rightPage }
    }
  }

  const { first, second } = getPageOrder()

  // Calculate image style for double page
  const getImageStyle = (): React.CSSProperties => {
    return {
      transform: `scale(${settings.zoomLevel})`,
      transformOrigin: 'center',
      transition: 'transform 0.2s ease-out',
    }
  }

  // Build the image URL
  const getImageUrl = (page: PageInfo) => {
    return `/api/v1/reader/${chapterId}/pages/${page.filename}`
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'flex items-center justify-center w-full h-full overflow-auto',
        className
      )}
      style={getImageStyle()}
    >
      <div className="flex gap-0">
        {/* First page (left in LTR, right in RTL) */}
        {first && (
          <div className="relative flex-1">
            <img
              src={getImageUrl(first)}
              alt={`Page ${first.index + 1}`}
              onLoad={() => handleImageLoad(first.index)}
              onError={() => handleImageError(first.index, first)}
              className="h-screen w-auto object-contain select-none pointer-events-none"
              draggable={false}
            />

            {/* Page number overlay */}
            {settings.showPageNumbers && (
              <div className="absolute bottom-4 left-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
                {first.index + 1}
              </div>
            )}

            {/* Loading indicator */}
            {!first.loaded && !first.error && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full" />
              </div>
            )}

            {/* Error indicator */}
            {first.error && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="text-center text-white">
                  <div className="text-red-400 mb-2">Failed to load</div>
                  <div className="text-sm opacity-60">Page {first.index + 1}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Second page (right in LTR, left in RTL) */}
        {second && (
          <div className="relative flex-1">
            <img
              src={getImageUrl(second)}
              alt={`Page ${second.index + 1}`}
              onLoad={() => handleImageLoad(second.index)}
              onError={() => handleImageError(second.index, second)}
              className="h-screen w-auto object-contain select-none pointer-events-none"
              draggable={false}
            />

            {/* Page number overlay */}
            {settings.showPageNumbers && (
              <div className="absolute bottom-4 right-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
                {second.index + 1}
              </div>
            )}

            {/* Loading indicator */}
            {!second.loaded && !second.error && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full" />
              </div>
            )}

            {/* Error indicator */}
            {second.error && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="text-center text-white">
                  <div className="text-red-400 mb-2">Failed to load</div>
                  <div className="text-sm opacity-60">Page {second.index + 1}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty page placeholder if only one page */}
        {(first && !second) || (!first && second) ? (
          <div className="relative flex-1 bg-gray-900 min-h-screen">
            <div className="flex items-center justify-center h-full text-gray-600">
              <div className="text-center">
                <div className="text-sm">No page</div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}