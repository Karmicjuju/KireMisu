import { useEffect, useCallback, useRef } from 'react'
import { useReaderStore } from '@/lib/reader-store'
import {
  getChapterPages,
  updateReadingProgress,
  getChapterNavigation,
  navigatePages,
  getPageImageUrl
} from '@/lib/api'

export function useReader() {
  const store = useReaderStore()
  const progressTimeoutRef = useRef<NodeJS.Timeout>()
  
  // Load chapter data
  const loadChapter = useCallback(async (chapterId: number) => {
    store.setLoading(true)
    store.setError(null)
    
    try {
      // Load chapter pages and navigation in parallel
      const [chapterData, navigationData] = await Promise.all([
        getChapterPages(chapterId),
        getChapterNavigation(chapterId)
      ])
      
      store.setChapter(chapterId, chapterData)
      store.setNavigation(navigationData)
      
      // Start preloading first few pages
      preloadPages(chapterId, chapterData.current_page || 0, chapterData.pages)
      
    } catch (error: any) {
      console.error('Failed to load chapter:', error)
      store.setError(error.message || 'Failed to load chapter')
    } finally {
      store.setLoading(false)
    }
  }, [store])
  
  // Update reading progress with debouncing
  const updateProgress = useCallback(async (chapterId: number, pageNumber: number) => {
    // Clear existing timeout
    if (progressTimeoutRef.current) {
      clearTimeout(progressTimeoutRef.current)
    }
    
    // Debounce progress updates (save every 2 seconds of inactivity)
    progressTimeoutRef.current = setTimeout(async () => {
      try {
        const progressData = await updateReadingProgress(chapterId, pageNumber)
        store.setProgress(progressData)
      } catch (error) {
        console.error('Failed to update progress:', error)
      }
    }, 2000)
  }, [store])
  
  // Page navigation with automatic progress tracking
  const goToPage = useCallback((pageIndex: number) => {
    const { chapterId, pages } = store.getState()
    
    if (!chapterId || pageIndex < 0 || pageIndex >= pages.length) {
      return
    }
    
    store.setCurrentPage(pageIndex)
    updateProgress(chapterId, pageIndex)
    
    // Preload upcoming pages
    preloadPages(chapterId, pageIndex, pages.map(p => p.filename))
  }, [store, updateProgress])
  
  // Navigation actions
  const nextPage = useCallback(() => {
    const success = store.nextPage()
    if (success) {
      const { chapterId, currentPageIndex } = store.getState()
      if (chapterId) {
        updateProgress(chapterId, currentPageIndex)
      }
    }
    return success
  }, [store, updateProgress])
  
  const previousPage = useCallback(() => {
    const success = store.previousPage()
    if (success) {
      const { chapterId, currentPageIndex } = store.getState()
      if (chapterId) {
        updateProgress(chapterId, currentPageIndex)
      }
    }
    return success
  }, [store, updateProgress])
  
  // Chapter navigation
  const goToNextChapter = useCallback(async () => {
    const { navigation } = store.getState()
    if (navigation?.nextChapter) {
      await loadChapter(navigation.nextChapter.id)
    }
  }, [store, loadChapter])
  
  const goToPreviousChapter = useCallback(async () => {
    const { navigation } = store.getState()
    if (navigation?.previousChapter) {
      await loadChapter(navigation.previousChapter.id)
    }
  }, [store, loadChapter])
  
  // Preload pages for smooth reading
  const preloadPages = useCallback((chapterId: number, currentPage: number, pageFilenames: string[]) => {
    const { settings, preloadedPages } = store.getState()
    const { preloadPages: preloadCount } = settings
    
    // Preload next few pages
    for (let i = 1; i <= preloadCount && currentPage + i < pageFilenames.length; i++) {
      const nextPageFilename = pageFilenames[currentPage + i]
      
      // Skip if already preloaded
      if (preloadedPages.has(nextPageFilename)) {
        continue
      }
      
      // Create image element to trigger preload
      const img = new Image()
      img.onload = () => {
        store.addPreloadedPage(nextPageFilename)
        store.markPageLoaded(nextPageFilename)
      }
      img.onerror = () => {
        store.markPageError(nextPageFilename, 'Failed to load image')
      }
      
      // Start loading
      img.src = getPageImageUrl(chapterId, nextPageFilename)
    }
  }, [store])
  
  // Keyboard navigation
  const handleKeyPress = useCallback((event: KeyboardEvent) => {
    const { settings } = store.getState()
    const { readingDirection } = settings
    
    // Prevent handling if user is typing in an input
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
      return
    }
    
    switch (event.key) {
      case 'ArrowRight':
        event.preventDefault()
        if (readingDirection === 'ltr') {
          nextPage()
        } else {
          previousPage()
        }
        break
        
      case 'ArrowLeft':
        event.preventDefault()
        if (readingDirection === 'ltr') {
          previousPage()
        } else {
          nextPage()
        }
        break
        
      case 'ArrowDown':
      case ' ': // Spacebar
        event.preventDefault()
        nextPage()
        break
        
      case 'ArrowUp':
        event.preventDefault()
        previousPage()
        break
        
      case 'Home':
        event.preventDefault()
        store.firstPage()
        break
        
      case 'End':
        event.preventDefault()
        store.lastPage()
        break
        
      case 'f':
      case 'F11':
        event.preventDefault()
        store.toggleFullscreen()
        break
        
      case 'c':
        event.preventDefault()
        store.toggleControls()
        break
        
      case 'Escape':
        event.preventDefault()
        if (store.getState().isFullscreen) {
          store.toggleFullscreen()
        }
        break
    }
  }, [store, nextPage, previousPage])
  
  // Set up keyboard event listeners
  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress)
    
    return () => {
      document.removeEventListener('keydown', handleKeyPress)
    }
  }, [handleKeyPress])
  
  // Handle fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFullscreen = !!document.fullscreenElement
      if (isFullscreen !== store.getState().isFullscreen) {
        store.toggleFullscreen()
      }
    }
    
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }
  }, [store])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (progressTimeoutRef.current) {
        clearTimeout(progressTimeoutRef.current)
      }
    }
  }, [])
  
  // Zoom controls
  const zoomIn = useCallback(() => {
    const { settings } = store.getState()
    const newZoom = Math.min(settings.zoomLevel * 1.25, 5.0)
    store.setSettings({ zoomLevel: newZoom })
  }, [store])
  
  const zoomOut = useCallback(() => {
    const { settings } = store.getState()
    const newZoom = Math.max(settings.zoomLevel * 0.8, 0.1)
    store.setSettings({ zoomLevel: newZoom })
  }, [store])
  
  const resetZoom = useCallback(() => {
    store.setSettings({ zoomLevel: 1.0 })
  }, [store])
  
  // Touch/swipe gestures
  const handleTouchStart = useCallback((event: TouchEvent) => {
    const touch = event.touches[0]
    store.getState().touchStartX = touch.clientX
    store.getState().touchStartY = touch.clientY
  }, [store])
  
  const handleTouchEnd = useCallback((event: TouchEvent) => {
    const state = store.getState()
    const touch = event.changedTouches[0]
    const deltaX = touch.clientX - (state.touchStartX || 0)
    const deltaY = touch.changedTouches[0].clientY - (state.touchStartY || 0)
    
    // Minimum swipe distance
    const minSwipeDistance = 50
    
    // Horizontal swipe (page navigation)
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
      event.preventDefault()
      
      if (deltaX > 0) {
        // Swipe right
        if (state.settings.readingDirection === 'ltr') {
          previousPage()
        } else {
          nextPage()
        }
      } else {
        // Swipe left
        if (state.settings.readingDirection === 'ltr') {
          nextPage()
        } else {
          previousPage()
        }
      }
    }
    
    // Vertical swipe (could be used for other functions)
    else if (Math.abs(deltaY) > minSwipeDistance) {
      // Could implement chapter navigation or other features
    }
  }, [store, nextPage, previousPage])
  
  // Set up touch event listeners for mobile
  useEffect(() => {
    const handleTouchStartPassive = (e: TouchEvent) => handleTouchStart(e)
    const handleTouchEndPassive = (e: TouchEvent) => handleTouchEnd(e)
    
    document.addEventListener('touchstart', handleTouchStartPassive, { passive: false })
    document.addEventListener('touchend', handleTouchEndPassive, { passive: false })
    
    return () => {
      document.removeEventListener('touchstart', handleTouchStartPassive)
      document.removeEventListener('touchend', handleTouchEndPassive)
    }
  }, [handleTouchStart, handleTouchEnd])
  
  return {
    // State
    ...store,
    
    // Actions
    loadChapter,
    goToPage,
    nextPage,
    previousPage,
    goToNextChapter,
    goToPreviousChapter,
    
    // Zoom controls
    zoomIn,
    zoomOut,
    resetZoom,
  }
}