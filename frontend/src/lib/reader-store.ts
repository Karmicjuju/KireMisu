import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

export type ReadingMode = 'single' | 'double' | 'vertical'

export interface ReaderSettings {
  readingMode: ReadingMode
  readingDirection: 'ltr' | 'rtl'
  pageFit: 'width' | 'height' | 'screen'
  zoomLevel: number
  preloadPages: number
  showPageNumbers: boolean
  fullscreenMode: boolean
  autoDetectMode: boolean
  doublePageOffset: boolean // For starting double page on even/odd pages
}

export interface ReadingProgress {
  chapterId: number
  currentPage: number
  totalPages: number
  isCompleted: boolean
  lastRead: string
}

export interface ChapterNavigation {
  currentChapter: {
    id: number
    number: string
    title?: string
  }
  previousChapter?: {
    id: number
    number: string
    title?: string
  }
  nextChapter?: {
    id: number
    number: string
    title?: string
  }
  totalChapters: number
  currentPosition: number
}

export interface PageInfo {
  filename: string
  index: number
  loaded: boolean
  error?: string
}

interface ReaderState {
  // Current reading session
  chapterId: number | null
  chapterTitle: string | null
  seriesTitle: string | null
  pages: PageInfo[]
  currentPageIndex: number
  
  // Settings
  settings: ReaderSettings
  
  // Progress tracking
  progress: ReadingProgress | null
  
  // Navigation
  navigation: ChapterNavigation | null
  
  // UI state
  isLoading: boolean
  error: string | null
  showControls: boolean
  isFullscreen: boolean
  
  // Page preloading
  preloadedPages: Set<string>
  
  // Actions
  setChapter: (chapterId: number, chapterData: any) => void
  setCurrentPage: (pageIndex: number) => void
  setSettings: (settings: Partial<ReaderSettings>) => void
  setProgress: (progress: ReadingProgress) => void
  setNavigation: (navigation: ChapterNavigation) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  toggleControls: () => void
  toggleFullscreen: () => void
  markPageLoaded: (filename: string) => void
  markPageError: (filename: string, error: string) => void
  addPreloadedPage: (filename: string) => void
  reset: () => void
  
  // Navigation actions
  nextPage: () => boolean
  previousPage: () => boolean
  goToPage: (pageIndex: number) => void
  firstPage: () => void
  lastPage: () => void
}

const defaultSettings: ReaderSettings = {
  readingMode: 'single',
  readingDirection: 'ltr',
  pageFit: 'width',
  zoomLevel: 1.0,
  preloadPages: 3,
  showPageNumbers: true,
  fullscreenMode: false,
  autoDetectMode: true,
  doublePageOffset: false,
}

export const useReaderStore = create<ReaderState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        chapterId: null,
        chapterTitle: null,
        seriesTitle: null,
        pages: [],
        currentPageIndex: 0,
        
        settings: defaultSettings,
        progress: null,
        navigation: null,
        
        isLoading: false,
        error: null,
        showControls: true,
        isFullscreen: false,
        
        preloadedPages: new Set(),
        
        // Actions
        setChapter: (chapterId: number, chapterData: any) => {
          const pages: PageInfo[] = chapterData.pages.map((filename: string, index: number) => ({
            filename,
            index,
            loaded: false,
          }))
          
          // Apply suggested reading mode if auto-detect is enabled
          const state = get()
          const settings = { ...state.settings }
          
          if (settings.autoDetectMode && chapterData.suggested_reading_mode) {
            settings.readingMode = chapterData.suggested_reading_mode
          }
          
          set({
            chapterId,
            chapterTitle: chapterData.chapter_title,
            seriesTitle: chapterData.series_title,
            pages,
            currentPageIndex: chapterData.current_page || 0,
            settings,
            progress: chapterData.reading_progress ? {
              chapterId: chapterData.chapter_id,
              currentPage: chapterData.reading_progress.current_page,
              totalPages: chapterData.reading_progress.total_pages,
              isCompleted: chapterData.reading_progress.is_completed,
              lastRead: chapterData.reading_progress.last_read,
            } : null,
            error: null,
          })
        },
        
        setCurrentPage: (pageIndex: number) => {
          const state = get()
          if (pageIndex >= 0 && pageIndex < state.pages.length) {
            set({ currentPageIndex: pageIndex })
          }
        },
        
        setSettings: (newSettings: Partial<ReaderSettings>) => {
          set(state => ({
            settings: { ...state.settings, ...newSettings }
          }))
        },
        
        setProgress: (progress: ReadingProgress) => {
          set({ progress })
        },
        
        setNavigation: (navigation: ChapterNavigation) => {
          set({ navigation })
        },
        
        setLoading: (loading: boolean) => {
          set({ isLoading: loading })
        },
        
        setError: (error: string | null) => {
          set({ error })
        },
        
        toggleControls: () => {
          set(state => ({ showControls: !state.showControls }))
        },
        
        toggleFullscreen: () => {
          const state = get()
          const newFullscreen = !state.isFullscreen
          
          if (typeof document !== 'undefined') {
            if (newFullscreen) {
              document.documentElement.requestFullscreen?.()
            } else {
              document.exitFullscreen?.()
            }
          }
          
          set({ isFullscreen: newFullscreen })
        },
        
        markPageLoaded: (filename: string) => {
          set(state => ({
            pages: state.pages.map(page => 
              page.filename === filename 
                ? { ...page, loaded: true, error: undefined }
                : page
            )
          }))
        },
        
        markPageError: (filename: string, error: string) => {
          set(state => ({
            pages: state.pages.map(page => 
              page.filename === filename 
                ? { ...page, loaded: false, error }
                : page
            )
          }))
        },
        
        addPreloadedPage: (filename: string) => {
          set(state => ({
            preloadedPages: new Set([...state.preloadedPages, filename])
          }))
        },
        
        reset: () => {
          set({
            chapterId: null,
            chapterTitle: null,
            seriesTitle: null,
            pages: [],
            currentPageIndex: 0,
            progress: null,
            navigation: null,
            isLoading: false,
            error: null,
            showControls: true,
            isFullscreen: false,
            preloadedPages: new Set(),
          })
        },
        
        // Navigation actions
        nextPage: () => {
          const state = get()
          const nextIndex = state.currentPageIndex + 1
          
          if (nextIndex < state.pages.length) {
            set({ currentPageIndex: nextIndex })
            return true
          }
          
          return false // End of chapter
        },
        
        previousPage: () => {
          const state = get()
          const prevIndex = state.currentPageIndex - 1
          
          if (prevIndex >= 0) {
            set({ currentPageIndex: prevIndex })
            return true
          }
          
          return false // Beginning of chapter
        },
        
        goToPage: (pageIndex: number) => {
          const state = get()
          if (pageIndex >= 0 && pageIndex < state.pages.length) {
            set({ currentPageIndex: pageIndex })
          }
        },
        
        firstPage: () => {
          set({ currentPageIndex: 0 })
        },
        
        lastPage: () => {
          const state = get()
          if (state.pages.length > 0) {
            set({ currentPageIndex: state.pages.length - 1 })
          }
        },
      }),
      {
        name: 'reader-settings',
        partialize: (state) => ({ 
          settings: state.settings,
          // Don't persist reading session data, only settings
        }),
      }
    ),
    {
      name: 'reader-store',
    }
  )
)