'use client'

import React, { useEffect, useRef } from 'react'
import Image from 'next/image'
import { ReaderSettings, PageInfo } from '@/lib/reader-store'
import { cn } from '@/lib/utils'

interface SinglePageModeProps {
  chapterId: number
  page: PageInfo
  settings: ReaderSettings
  onPageLoad?: () => void
  onPageError?: (error: string) => void
  className?: string
}

export function SinglePageMode({
  chapterId,
  page,
  settings,
  onPageLoad,
  onPageError,
  className
}: SinglePageModeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  // Calculate image dimensions based on fit mode
  const getImageStyle = () => {
    const baseStyle: React.CSSProperties = {
      transform: `scale(${settings.zoomLevel})`,
      transformOrigin: 'center',
      transition: 'transform 0.2s ease-out',
    }

    switch (settings.pageFit) {
      case 'width':
        return {
          ...baseStyle,
          width: '100%',
          height: 'auto',
          maxHeight: 'none',
        }
      case 'height':
        return {
          ...baseStyle,
          width: 'auto',
          height: '100vh',
          maxWidth: 'none',
        }
      case 'screen':
        return {
          ...baseStyle,
          maxWidth: '100%',
          maxHeight: '100vh',
          width: 'auto',
          height: 'auto',
        }
      default:
        return baseStyle
    }
  }

  // Handle image load
  const handleImageLoad = () => {
    if (onPageLoad) {
      onPageLoad()
    }
  }

  // Handle image error
  const handleImageError = () => {
    const errorMsg = `Failed to load page ${page.index + 1}`
    if (onPageError) {
      onPageError(errorMsg)
    }
  }

  // Preload adjacent pages
  useEffect(() => {
    if (settings.preloadPages > 0 && page.loaded) {
      // Preload logic will be handled by parent component
      // This is just a placeholder for future enhancement
    }
  }, [page, settings.preloadPages])

  // Build the image URL
  const imageUrl = `/api/v1/reader/${chapterId}/pages/${page.filename}`

  return (
    <div
      ref={containerRef}
      className={cn(
        'flex items-center justify-center w-full h-full overflow-auto',
        className
      )}
    >
      <div 
        className="relative"
        style={getImageStyle()}
      >
        {/* Main page image */}
        <img
          ref={imageRef}
          src={imageUrl}
          alt={`Page ${page.index + 1}`}
          onLoad={handleImageLoad}
          onError={handleImageError}
          className={cn(
            'select-none pointer-events-none',
            settings.readingDirection === 'rtl' && 'scale-x-[-1]'
          )}
          draggable={false}
        />

        {/* Page number overlay */}
        {settings.showPageNumbers && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
            {page.index + 1}
          </div>
        )}

        {/* Loading indicator */}
        {!page.loaded && !page.error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full" />
          </div>
        )}

        {/* Error indicator */}
        {page.error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="text-center text-white">
              <div className="text-red-400 mb-2">Failed to load page</div>
              <div className="text-sm opacity-60">{page.error}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}