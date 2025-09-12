'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { ReaderSettings, PageInfo } from '@/lib/reader-store'
import { cn } from '@/lib/utils'

interface VerticalScrollModeProps {
  chapterId: number
  pages: PageInfo[]
  currentPageIndex: number
  settings: ReaderSettings
  onPageChange?: (pageIndex: number) => void
  onPageLoad?: (pageIndex: number) => void
  onPageError?: (pageIndex: number, error: string) => void
  className?: string
}

export function VerticalScrollMode({
  chapterId,
  pages,
  currentPageIndex,
  settings,
  onPageChange,
  onPageLoad,
  onPageError,
  className
}: VerticalScrollModeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const [visiblePages, setVisiblePages] = useState<Set<number>>(new Set())
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Build the image URL
  const getImageUrl = (page: PageInfo) => {
    return `/api/v1/reader/${chapterId}/pages/${page.filename}`
  }

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

  // Set up intersection observer for lazy loading and current page detection
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const newVisiblePages = new Set<number>()
        let mostVisiblePage = currentPageIndex
        let maxVisibility = 0

        entries.forEach((entry) => {
          const pageIndex = parseInt(entry.target.getAttribute('data-page-index') || '0')
          
          if (entry.isIntersecting) {
            newVisiblePages.add(pageIndex)
            
            // Track which page is most visible
            if (entry.intersectionRatio > maxVisibility) {
              maxVisibility = entry.intersectionRatio
              mostVisiblePage = pageIndex
            }
          }
        })

        setVisiblePages(newVisiblePages)

        // Update current page based on most visible page
        if (onPageChange && mostVisiblePage !== currentPageIndex && maxVisibility > 0.5) {
          // Debounce page change to avoid rapid updates
          if (scrollTimeoutRef.current) {
            clearTimeout(scrollTimeoutRef.current)
          }
          
          scrollTimeoutRef.current = setTimeout(() => {
            onPageChange(mostVisiblePage)
          }, 100)
        }
      },
      {
        root: containerRef.current,
        rootMargin: '100px 0px', // Preload pages slightly before they come into view
        threshold: [0, 0.25, 0.5, 0.75, 1.0]
      }
    )

    // Observe all page elements
    pageRefs.current.forEach((element) => {
      observer.observe(element)
    })

    return () => {
      observer.disconnect()
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
    }
  }, [pages, currentPageIndex, onPageChange])

  // Scroll to current page when it changes externally
  useEffect(() => {
    const pageElement = pageRefs.current.get(currentPageIndex)
    if (pageElement && containerRef.current) {
      const container = containerRef.current
      const containerRect = container.getBoundingClientRect()
      const pageRect = pageElement.getBoundingClientRect()
      
      // Check if page is not fully visible
      if (pageRect.top < containerRect.top || pageRect.bottom > containerRect.bottom) {
        pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }, [currentPageIndex])

  // Calculate image style
  const getImageStyle = (): React.CSSProperties => {
    const baseStyle: React.CSSProperties = {
      transform: `scale(${settings.zoomLevel})`,
      transformOrigin: 'center top',
      transition: 'transform 0.2s ease-out',
    }

    switch (settings.pageFit) {
      case 'width':
        return {
          ...baseStyle,
          width: '100%',
          height: 'auto',
        }
      case 'height':
        return {
          ...baseStyle,
          width: 'auto',
          maxWidth: '100%',
        }
      case 'screen':
        return {
          ...baseStyle,
          maxWidth: '100%',
          width: 'auto',
          height: 'auto',
        }
      default:
        return baseStyle
    }
  }

  // Handle lazy loading - only render images for visible pages + buffer
  const shouldLoadImage = (pageIndex: number) => {
    const buffer = settings.preloadPages || 2
    const isNearVisible = Math.abs(pageIndex - currentPageIndex) <= buffer
    return visiblePages.has(pageIndex) || isNearVisible
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'w-full h-full overflow-y-auto overflow-x-hidden',
        'scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900',
        className
      )}
    >
      <div className="max-w-4xl mx-auto px-4 py-8">
        {pages.map((page, index) => (
          <div
            key={page.filename}
            ref={(el) => {
              if (el) pageRefs.current.set(index, el)
              else pageRefs.current.delete(index)
            }}
            data-page-index={index}
            className={cn(
              'relative mb-2',
              index === currentPageIndex && 'ring-2 ring-orange-500 ring-offset-2 ring-offset-black'
            )}
            style={getImageStyle()}
          >
            {shouldLoadImage(index) ? (
              <>
                <img
                  src={getImageUrl(page)}
                  alt={`Page ${page.index + 1}`}
                  onLoad={() => handleImageLoad(index)}
                  onError={() => handleImageError(index, page)}
                  className={cn(
                    'w-full h-auto select-none',
                    settings.readingDirection === 'rtl' && 'scale-x-[-1]'
                  )}
                  draggable={false}
                  loading="lazy"
                />

                {/* Page number overlay */}
                {settings.showPageNumbers && (
                  <div className="absolute top-4 right-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
                    {page.index + 1} / {pages.length}
                  </div>
                )}

                {/* Loading indicator */}
                {!page.loaded && !page.error && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 min-h-[400px]">
                    <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full" />
                  </div>
                )}

                {/* Error indicator */}
                {page.error && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 min-h-[400px]">
                    <div className="text-center text-white">
                      <div className="text-red-400 mb-2">Failed to load page</div>
                      <div className="text-sm opacity-60">{page.error}</div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              // Placeholder for unloaded pages
              <div className="bg-gray-900 min-h-[600px] flex items-center justify-center">
                <div className="text-gray-600">
                  <div className="text-sm">Page {page.index + 1}</div>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Chapter end indicator */}
        <div className="text-center py-8 text-gray-500">
          <div className="text-lg mb-2">End of Chapter</div>
          <div className="text-sm">Scroll up to continue reading</div>
        </div>
      </div>
    </div>
  )
}