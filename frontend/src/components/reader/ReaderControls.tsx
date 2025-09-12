'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { 
  ChevronLeft, 
  ChevronRight, 
  SkipBack, 
  SkipForward,
  Maximize,
  Minimize,
  Settings,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Home,
  Menu,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ReaderSettings, ReadingProgress, ChapterNavigation } from '@/lib/reader-store'

interface ReaderControlsProps {
  chapterTitle?: string | null
  seriesTitle?: string | null
  currentPage: number
  totalPages: number
  progress?: ReadingProgress | null
  navigation?: ChapterNavigation | null
  settings: ReaderSettings
  isFullscreen: boolean
  onPreviousPage: () => void
  onNextPage: () => void
  onGoToPage: (page: number) => void
  onPreviousChapter: () => void
  onNextChapter: () => void
  onToggleFullscreen: () => void
  onSettingsChange: (settings: Partial<ReaderSettings>) => void
  className?: string
}

export function ReaderControls({
  chapterTitle,
  seriesTitle,
  currentPage,
  totalPages,
  progress,
  navigation,
  settings,
  isFullscreen,
  onPreviousPage,
  onNextPage,
  onGoToPage,
  onPreviousChapter,
  onNextChapter,
  onToggleFullscreen,
  onSettingsChange,
  className
}: ReaderControlsProps) {
  const [showPageSlider, setShowPageSlider] = useState(false)
  
  const progressPercent = totalPages > 0 ? (currentPage / totalPages) * 100 : 0
  
  const handlePageSliderChange = (value: number[]) => {
    onGoToPage(value[0] - 1) // Convert to 0-indexed
  }
  
  const handleZoomIn = () => {
    const newZoom = Math.min(settings.zoomLevel * 1.25, 5.0)
    onSettingsChange({ zoomLevel: newZoom })
  }
  
  const handleZoomOut = () => {
    const newZoom = Math.max(settings.zoomLevel * 0.8, 0.1)
    onSettingsChange({ zoomLevel: newZoom })
  }
  
  const handleResetZoom = () => {
    onSettingsChange({ zoomLevel: 1.0 })
  }
  
  return (
    <div className={cn('relative h-full', className)}>
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/80 to-transparent p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/20"
              onClick={() => window.history.back()}
            >
              <Home className="w-5 h-5" />
            </Button>
            
            <div className="text-white">
              <h1 className="text-lg font-semibold truncate max-w-xs">
                {chapterTitle || `Chapter ${navigation?.currentChapter.number}`}
              </h1>
              <p className="text-sm text-white/70 truncate max-w-xs">
                {seriesTitle}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Settings menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-white hover:bg-white/20"
                >
                  <Settings className="w-5 h-5" />
                </Button>
              </DropdownMenuTrigger>
              
              <DropdownMenuContent className="w-56">
                <DropdownMenuItem
                  onClick={() => setShowPageSlider(!showPageSlider)}
                >
                  <Menu className="w-4 h-4 mr-2" />
                  Go to Page
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                
                <DropdownMenuItem
                  onClick={() => {
                    const modes = ['single', 'double', 'vertical'] as const
                    const currentIndex = modes.indexOf(settings.readingMode)
                    const nextMode = modes[(currentIndex + 1) % modes.length]
                    onSettingsChange({ readingMode: nextMode })
                  }}
                >
                  Reading Mode: {settings.readingMode === 'single' ? 'Single Page' : 
                                settings.readingMode === 'double' ? 'Double Page' : 
                                'Vertical Scroll'}
                </DropdownMenuItem>
                
                <DropdownMenuItem
                  onClick={() => onSettingsChange({ 
                    autoDetectMode: !settings.autoDetectMode 
                  })}
                >
                  Auto-detect Mode: {settings.autoDetectMode ? 'On' : 'Off'}
                </DropdownMenuItem>
                
                <DropdownMenuItem
                  onClick={() => onSettingsChange({ 
                    readingDirection: settings.readingDirection === 'ltr' ? 'rtl' : 'ltr' 
                  })}
                >
                  Reading Direction: {settings.readingDirection.toUpperCase()}
                </DropdownMenuItem>
                
                {settings.readingMode === 'double' && (
                  <DropdownMenuItem
                    onClick={() => onSettingsChange({ 
                      doublePageOffset: !settings.doublePageOffset 
                    })}
                  >
                    Start on: {settings.doublePageOffset ? 'Even Page' : 'Odd Page'}
                  </DropdownMenuItem>
                )}
                
                <DropdownMenuItem
                  onClick={() => {
                    const modes = ['width', 'height', 'screen'] as const
                    const currentIndex = modes.indexOf(settings.pageFit)
                    const nextMode = modes[(currentIndex + 1) % modes.length]
                    onSettingsChange({ pageFit: nextMode })
                  }}
                >
                  Fit Mode: {settings.pageFit}
                </DropdownMenuItem>
                
                <DropdownMenuItem
                  onClick={() => onSettingsChange({ 
                    showPageNumbers: !settings.showPageNumbers 
                  })}
                >
                  {settings.showPageNumbers ? 'Hide' : 'Show'} Page Numbers
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            <Button
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/20"
              onClick={onToggleFullscreen}
            >
              {isFullscreen ? (
                <Minimize className="w-5 h-5" />
              ) : (
                <Maximize className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>
      </div>
      
      {/* Page slider overlay */}
      {showPageSlider && (
        <div className="absolute top-16 left-4 right-4 bg-black/90 rounded-lg p-4 z-10">
          <div className="flex items-center space-x-4">
            <span className="text-white text-sm min-w-[3rem]">
              Page {currentPage}
            </span>
            <Slider
              value={[currentPage]}
              min={1}
              max={totalPages}
              step={1}
              onValueChange={handlePageSliderChange}
              className="flex-1"
            />
            <span className="text-white text-sm min-w-[3rem]">
              of {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={() => setShowPageSlider(false)}
            >
              ✕
            </Button>
          </div>
        </div>
      )}
      
      {/* Bottom controls */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
        <div className="flex items-center justify-between">
          {/* Chapter navigation */}
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={onPreviousChapter}
              disabled={!navigation?.previousChapter}
            >
              <SkipBack className="w-4 h-4 mr-1" />
              Prev Chapter
            </Button>
          </div>
          
          {/* Page navigation */}
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/20"
              onClick={onPreviousPage}
            >
              <ChevronLeft className="w-5 h-5" />
            </Button>
            
            <div className="text-white text-center min-w-[6rem]">
              <div className="text-sm font-medium">
                {currentPage} / {totalPages}
              </div>
              <div className="w-24 h-1 bg-white/20 rounded-full mx-auto mt-1">
                <div 
                  className="h-full bg-white rounded-full transition-all duration-300"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/20"
              onClick={onNextPage}
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>
          
          {/* Chapter navigation */}
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={onNextChapter}
              disabled={!navigation?.nextChapter}
            >
              Next Chapter
              <SkipForward className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
        
        {/* Zoom controls */}
        <div className="flex items-center justify-center space-x-2 mt-2">
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
            onClick={handleZoomOut}
          >
            <ZoomOut className="w-4 h-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            className="text-white hover:bg-white/20 min-w-[4rem]"
            onClick={handleResetZoom}
          >
            {Math.round(settings.zoomLevel * 100)}%
          </Button>
          
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
            onClick={handleZoomIn}
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {/* Left side navigation zone */}
      <div 
        className="absolute left-0 top-0 w-16 h-full flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
        onClick={onPreviousPage}
      >
        <div className="bg-black/40 rounded-full p-2">
          <ChevronLeft className="w-6 h-6 text-white" />
        </div>
      </div>
      
      {/* Right side navigation zone */}
      <div 
        className="absolute right-0 top-0 w-16 h-full flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
        onClick={onNextPage}
      >
        <div className="bg-black/40 rounded-full p-2">
          <ChevronRight className="w-6 h-6 text-white" />
        </div>
      </div>
      
      {/* Progress indicator */}
      {progress && (
        <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-black/60 text-white px-2 py-1 rounded text-xs">
          {progress.isCompleted ? '✓ Complete' : `${Math.round(progressPercent)}%`}
        </div>
      )}
    </div>
  )
}