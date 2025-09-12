'use client'

import React, { useEffect, useRef, useState } from 'react'
import { useReaderStore } from '@/lib/reader-store'
import { ReaderPage } from './ReaderPage'
import { ReaderControls } from './ReaderControls'
import { SinglePageMode } from './modes/SinglePageMode'
import { DoublePageMode } from './modes/DoublePageMode'
import { VerticalScrollMode } from './modes/VerticalScrollMode'
import { cn } from '@/lib/utils'

interface MangaReaderProps {
  onChapterChange?: (chapterId: number) => void
}

export function MangaReader({ onChapterChange }: MangaReaderProps) {
  const {
    chapterId,
    chapterTitle,
    seriesTitle,
    pages,
    currentPageIndex,
    settings,
    showControls,
    isFullscreen,
    navigation,
    progress,
    nextPage,
    previousPage,
    goToPage,
    toggleControls,
    toggleFullscreen,
    setSettings,
  } = useReaderStore()
  
  const containerRef = useRef<HTMLDivElement>(null)
  const [controlsTimeout, setControlsTimeout] = useState<NodeJS.Timeout | null>(null)
  const [lastActivity, setLastActivity] = useState(Date.now())
  
  const currentPage = pages[currentPageIndex]
  const nextPageIndex = currentPageIndex + 1
  const nextPage = nextPageIndex < pages.length ? pages[nextPageIndex] : null
  
  // Auto-hide controls after inactivity
  useEffect(() => {
    const hideControlsDelay = 3000 // 3 seconds
    
    const resetControlsTimer = () => {
      if (controlsTimeout) {
        clearTimeout(controlsTimeout)
      }
      
      const timeout = setTimeout(() => {
        if (showControls && Date.now() - lastActivity > hideControlsDelay) {
          toggleControls()
        }
      }, hideControlsDelay)
      
      setControlsTimeout(timeout)
    }
    
    if (showControls && !isFullscreen) {
      resetControlsTimer()
    }
    
    return () => {
      if (controlsTimeout) {
        clearTimeout(controlsTimeout)
      }
    }
  }, [showControls, lastActivity, controlsTimeout, isFullscreen, toggleControls])
  
  // Handle mouse movement to show controls
  const handleMouseMove = () => {
    const now = Date.now()
    setLastActivity(now)
    
    if (!showControls) {
      toggleControls()
    }
  }
  
  // Handle click to toggle controls or navigate
  const handleClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    
    const clickX = event.clientX - rect.left
    const clickY = event.clientY - rect.top
    const width = rect.width
    const height = rect.height
    
    // Define click zones
    const leftZone = width * 0.3
    const rightZone = width * 0.7
    const topZone = height * 0.2
    const bottomZone = height * 0.8
    
    // Center zone toggles controls
    if (clickX > leftZone && clickX < rightZone && clickY > topZone && clickY < bottomZone) {
      toggleControls()
      return
    }
    
    // Navigation zones
    if (clickX < leftZone) {
      // Left click - previous page (or next in RTL)
      if (settings.readingDirection === 'ltr') {
        previousPage()
      } else {
        nextPage()
      }
    } else if (clickX > rightZone) {
      // Right click - next page (or previous in RTL)
      if (settings.readingDirection === 'ltr') {
        nextPage()
      } else {
        previousPage()
      }
    }
  }
  
  // Handle wheel zoom
  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault()
      
      const delta = event.deltaY
      const zoomFactor = 0.1
      const currentZoom = settings.zoomLevel
      
      if (delta < 0) {
        // Zoom in
        const newZoom = Math.min(currentZoom + zoomFactor, 5.0)
        setSettings({ zoomLevel: newZoom })
      } else {
        // Zoom out
        const newZoom = Math.max(currentZoom - zoomFactor, 0.1)
        setSettings({ zoomLevel: newZoom })
      }
    }
  }
  
  // Handle chapter navigation
  const handlePreviousChapter = () => {
    if (navigation?.previousChapter && onChapterChange) {
      onChapterChange(navigation.previousChapter.id)
    }
  }
  
  const handleNextChapter = () => {
    if (navigation?.nextChapter && onChapterChange) {
      onChapterChange(navigation.nextChapter.id)
    }
  }
  
  // Handle page navigation with chapter boundaries
  const handleNextPage = () => {
    // In double page mode, advance by 2 pages
    const increment = settings.readingMode === 'double' ? 2 : 1
    const nextIndex = currentPageIndex + increment
    
    if (nextIndex < pages.length) {
      goToPage(nextIndex)
      return true
    } else if (navigation?.nextChapter) {
      // End of chapter, ask user or auto-navigate
      if (confirm(`End of chapter. Go to next chapter: ${navigation.nextChapter.title || navigation.nextChapter.number}?`)) {
        handleNextChapter()
      }
    }
    return false
  }
  
  const handlePreviousPage = () => {
    // In double page mode, go back by 2 pages
    const decrement = settings.readingMode === 'double' ? 2 : 1
    const prevIndex = currentPageIndex - decrement
    
    if (prevIndex >= 0) {
      goToPage(prevIndex)
      return true
    } else if (navigation?.previousChapter) {
      // Beginning of chapter, ask user or auto-navigate
      if (confirm(`Beginning of chapter. Go to previous chapter: ${navigation.previousChapter.title || navigation.previousChapter.number}?`)) {
        handlePreviousChapter()
      }
    }
    return false
  }
  
  if (!chapterId || !currentPage) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-white">
        No chapter loaded
      </div>
    )
  }
  
  return (
    <div
      ref={containerRef}
      className={cn(
        'relative min-h-screen bg-black text-white overflow-hidden',
        isFullscreen && 'fixed inset-0 z-50',
        'cursor-pointer'
      )}
      onMouseMove={handleMouseMove}
      onClick={handleClick}
      onWheel={handleWheel}
    >
      {/* Main reader content */}
      <div className="relative h-screen flex items-center justify-center">
        {settings.readingMode === 'single' && (
          <SinglePageMode
            chapterId={chapterId}
            page={currentPage}
            settings={settings}
            onPageLoad={() => {
              // Handle page load if needed
            }}
            onPageError={(error) => {
              console.error('Page load error:', error)
            }}
          />
        )}
        
        {settings.readingMode === 'double' && (
          <DoublePageMode
            chapterId={chapterId}
            leftPage={settings.doublePageOffset && currentPageIndex === 0 ? null : currentPage}
            rightPage={settings.doublePageOffset && currentPageIndex === 0 ? currentPage : nextPage}
            settings={settings}
            onPageLoad={(pageIndex) => {
              // Handle page load if needed
            }}
            onPageError={(pageIndex, error) => {
              console.error(`Page ${pageIndex} load error:`, error)
            }}
          />
        )}
        
        {settings.readingMode === 'vertical' && (
          <VerticalScrollMode
            chapterId={chapterId}
            pages={pages}
            currentPageIndex={currentPageIndex}
            settings={settings}
            onPageChange={(pageIndex) => {
              goToPage(pageIndex)
            }}
            onPageLoad={(pageIndex) => {
              // Handle page load if needed
            }}
            onPageError={(pageIndex, error) => {
              console.error(`Page ${pageIndex} load error:`, error)
            }}
          />
        )}
      </div>
      
      {/* Reader controls overlay */}
      <div
        className={cn(
          'absolute inset-0 pointer-events-none transition-opacity duration-300',
          showControls ? 'opacity-100' : 'opacity-0'
        )}
      >
        <ReaderControls
          chapterTitle={chapterTitle}
          seriesTitle={seriesTitle}
          currentPage={currentPageIndex + 1}
          totalPages={pages.length}
          progress={progress}
          navigation={navigation}
          settings={settings}
          isFullscreen={isFullscreen}
          onPreviousPage={handlePreviousPage}
          onNextPage={handleNextPage}
          onGoToPage={goToPage}
          onPreviousChapter={handlePreviousChapter}
          onNextChapter={handleNextChapter}
          onToggleFullscreen={toggleFullscreen}
          onSettingsChange={setSettings}
          className="pointer-events-auto"
        />
      </div>
      
      {/* Navigation hints */}
      {!showControls && (
        <div className="absolute inset-0 pointer-events-none">
          {/* Left navigation zone */}
          <div className="absolute left-0 top-0 w-[30%] h-full flex items-center justify-start pl-4">
            <div className="bg-black/20 text-white/60 px-2 py-1 rounded text-sm opacity-0 hover:opacity-100 transition-opacity">
              {settings.readingDirection === 'ltr' ? '← Previous' : 'Next →'}
            </div>
          </div>
          
          {/* Right navigation zone */}
          <div className="absolute right-0 top-0 w-[30%] h-full flex items-center justify-end pr-4">
            <div className="bg-black/20 text-white/60 px-2 py-1 rounded text-sm opacity-0 hover:opacity-100 transition-opacity">
              {settings.readingDirection === 'ltr' ? 'Next →' : '← Previous'}
            </div>
          </div>
          
          {/* Center control zone */}
          <div className="absolute left-[30%] top-[20%] w-[40%] h-[60%] flex items-center justify-center">
            <div className="bg-black/20 text-white/60 px-2 py-1 rounded text-sm opacity-0 hover:opacity-100 transition-opacity">
              Tap to show controls
            </div>
          </div>
        </div>
      )}
      
      {/* Loading overlay */}
      {!currentPage.loaded && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <div className="text-white text-center">
            <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full mx-auto mb-2" />
            <p>Loading page...</p>
          </div>
        </div>
      )}
      
      {/* Error overlay */}
      {currentPage.error && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <div className="text-white text-center">
            <p className="text-red-400 mb-2">Failed to load page</p>
            <p className="text-sm text-white/60">{currentPage.error}</p>
          </div>
        </div>
      )}
    </div>
  )
}