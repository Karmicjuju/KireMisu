'use client'

import React, { useState, useRef, useEffect } from 'react'
import Image from 'next/image'
import { getPageImageUrl } from '@/lib/api'
import { PageInfo, ReaderSettings } from '@/lib/reader-store'
import { cn } from '@/lib/utils'

interface ReaderPageProps {
  chapterId: number
  page: PageInfo
  settings: ReaderSettings
  onLoad?: () => void
  onError?: (error: string) => void
}

export function ReaderPage({ chapterId, page, settings, onLoad, onError }: ReaderPageProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null)
  const imageRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  const imageUrl = getPageImageUrl(chapterId, page.filename)
  
  // Calculate image display dimensions based on settings
  const getImageStyle = () => {
    if (!imageDimensions) return {}
    
    const { pageFit, zoomLevel } = settings
    
    const style: React.CSSProperties = {
      transformOrigin: 'center center',
      transition: 'transform 0.2s ease-in-out',
    }
    
    if (pageFit === 'width') {
      style.width = '100%'
      style.height = 'auto'
      style.maxHeight = '100vh'
      style.objectFit = 'contain'
    } else if (pageFit === 'height') {
      style.height = '100vh'
      style.width = 'auto'
      style.maxWidth = '100%'
      style.objectFit = 'contain'
    } else if (pageFit === 'screen') {
      style.width = '100vw'
      style.height = '100vh'
      style.objectFit = 'contain'
    }
    
    // Apply zoom
    if (zoomLevel !== 1.0) {
      style.transform = `scale(${zoomLevel})`
    }
    
    return style
  }
  
  // Handle image load
  const handleImageLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
    const img = event.currentTarget
    setImageDimensions({
      width: img.naturalWidth,
      height: img.naturalHeight
    })
    setIsLoading(false)
    setError(null)
    onLoad?.()
  }
  
  // Handle image error
  const handleImageError = (event: React.SyntheticEvent<HTMLImageElement>) => {
    const errorMsg = 'Failed to load page image'
    setError(errorMsg)
    setIsLoading(false)
    onError?.(errorMsg)
  }
  
  // Handle drag for panning when zoomed
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 })
  
  const handleMouseDown = (event: React.MouseEvent) => {
    if (settings.zoomLevel > 1.0) {
      setIsDragging(true)
      setDragStart({
        x: event.clientX - imagePosition.x,
        y: event.clientY - imagePosition.y
      })
      event.preventDefault()
    }
  }
  
  const handleMouseMove = (event: React.MouseEvent) => {
    if (isDragging && settings.zoomLevel > 1.0) {
      setImagePosition({
        x: event.clientX - dragStart.x,
        y: event.clientY - dragStart.y
      })
      event.preventDefault()
    }
  }
  
  const handleMouseUp = () => {
    setIsDragging(false)
  }
  
  // Reset image position when zoom changes or page changes
  useEffect(() => {
    if (settings.zoomLevel <= 1.0) {
      setImagePosition({ x: 0, y: 0 })
    }
  }, [settings.zoomLevel, page.filename])
  
  // Keyboard shortcuts for zoomed image panning
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (settings.zoomLevel > 1.0) {
        const panStep = 50
        let newPosition = { ...imagePosition }
        
        switch (event.key) {
          case 'ArrowUp':
            if (event.shiftKey) {
              newPosition.y += panStep
              event.preventDefault()
            }
            break
          case 'ArrowDown':
            if (event.shiftKey) {
              newPosition.y -= panStep
              event.preventDefault()
            }
            break
          case 'ArrowLeft':
            if (event.shiftKey) {
              newPosition.x += panStep
              event.preventDefault()
            }
            break
          case 'ArrowRight':
            if (event.shiftKey) {
              newPosition.x -= panStep
              event.preventDefault()
            }
            break
        }
        
        setImagePosition(newPosition)
      }
    }
    
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [imagePosition, settings.zoomLevel])
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-full min-h-[50vh] text-white">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">⚠️</div>
          <p className="text-red-400 mb-1">Failed to load page</p>
          <p className="text-sm text-white/60">{page.filename}</p>
          <p className="text-xs text-white/40 mt-2">{error}</p>
        </div>
      </div>
    )
  }
  
  return (
    <div
      ref={containerRef}
      className={cn(
        'relative flex items-center justify-center h-full min-h-screen',
        settings.zoomLevel > 1.0 && 'overflow-hidden',
        isDragging && 'cursor-grabbing',
        settings.zoomLevel > 1.0 && !isDragging && 'cursor-grab'
      )}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20">
          <div className="text-white text-center">
            <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-sm">Loading...</p>
          </div>
        </div>
      )}
      
      {/* Main page image */}
      <div
        className={cn(
          'relative transition-transform duration-200',
          settings.zoomLevel > 1.0 && 'absolute'
        )}
        style={
          settings.zoomLevel > 1.0
            ? {
                transform: `translate(${imagePosition.x}px, ${imagePosition.y}px)`,
              }
            : {}
        }
      >
        <img
          ref={imageRef}
          src={imageUrl}
          alt={`Page ${page.index + 1}`}
          style={getImageStyle()}
          onLoad={handleImageLoad}
          onError={handleImageError}
          className={cn(
            'select-none',
            isLoading && 'opacity-0',
            !isLoading && 'opacity-100 transition-opacity duration-300'
          )}
          draggable={false}
        />
      </div>
      
      {/* Page number indicator */}
      {settings.showPageNumbers && !isLoading && (
        <div className="absolute bottom-4 right-4 bg-black/60 text-white px-2 py-1 rounded text-sm">
          {page.index + 1}
        </div>
      )}
      
      {/* Zoom level indicator */}
      {settings.zoomLevel !== 1.0 && (
        <div className="absolute top-4 right-4 bg-black/60 text-white px-2 py-1 rounded text-sm">
          {Math.round(settings.zoomLevel * 100)}%
        </div>
      )}
      
      {/* Pan instructions for zoomed images */}
      {settings.zoomLevel > 1.0 && (
        <div className="absolute top-4 left-4 bg-black/60 text-white px-2 py-1 rounded text-xs max-w-48">
          <p>Shift + Arrow keys or drag to pan</p>
        </div>
      )}
    </div>
  )
}