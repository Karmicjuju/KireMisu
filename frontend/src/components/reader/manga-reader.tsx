/**
 * Main manga reader component
 */

'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import useSWR, { mutate } from 'swr';
import { cn } from '@/lib/utils';
import { 
  chaptersApi, 
  annotationsApi,
  type ChapterResponse, 
  type ChapterPagesInfo,
  type AnnotationResponse,
  type AnnotationCreate,
  type AnnotationUpdate
} from '@/lib/api';
import { useKeyboardNavigation } from './use-keyboard-navigation';
import { useTouchNavigation } from './use-touch-navigation';
import { PageNavigation } from './page-navigation';
import { MangaPage } from './manga-page';
import { AnnotationMarker, AnnotationDrawer, AnnotationForm } from '@/components/annotations';
import { Button } from '@/components/ui/button';
import { toast } from '@/hooks/use-toast';
import { ArrowLeft, Maximize, Minimize, Loader2, AlertCircle, MessageSquare } from 'lucide-react';

export interface MangaReaderProps {
  chapterId: string;
  initialPage?: number;
  className?: string;
}

export function MangaReader({ chapterId, initialPage = 1, className }: MangaReaderProps) {
  const router = useRouter();

  // State management
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [showControls, setShowControls] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [preloadedPages, setPreloadedPages] = useState<Set<number>>(new Set());

  // Auto-hide controls timer
  const [controlsTimer, setControlsTimer] = useState<NodeJS.Timeout | null>(null);

  // Annotation state
  const [showAnnotationDrawer, setShowAnnotationDrawer] = useState(false);
  const [pageAnnotations, setPageAnnotations] = useState<Record<number, AnnotationResponse[]>>({});
  const [selectedAnnotation, setSelectedAnnotation] = useState<AnnotationResponse | null>(null);
  const [showAnnotationForm, setShowAnnotationForm] = useState(false);
  const [annotationFormPosition, setAnnotationFormPosition] = useState<{ x: number; y: number } | null>(null);
  const [annotationMode, setAnnotationMode] = useState(false);

  // API queries with SWR
  const {
    data: chapter,
    error: chapterError,
    isLoading: chapterLoading,
  } = useSWR<ChapterResponse>(`chapter-${chapterId}`, () => chaptersApi.getChapter(chapterId), {
    revalidateOnFocus: false,
    dedupingInterval: 5 * 60 * 1000, // 5 minutes
  });

  const {
    data: pagesInfo,
    error: pagesError,
    isLoading: pagesLoading,
  } = useSWR<ChapterPagesInfo>(
    chapter ? `chapter-pages-${chapterId}` : null,
    () => chaptersApi.getChapterPages(chapterId),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5 * 60 * 1000,
    }
  );

  // Update reading progress function
  const updateProgress = useCallback(
    async (data: { page: number; isRead?: boolean }) => {
      try {
        await chaptersApi.updateChapterProgress(chapterId, {
          last_read_page: data.page - 1, // Convert to 0-based
          is_read: data.isRead,
        });

        // Revalidate chapter data
        mutate(`chapter-${chapterId}`);
      } catch (error) {
        console.error('Failed to update reading progress:', error);
        toast({
          title: 'Error',
          description: 'Failed to save reading progress',
          variant: 'destructive',
        });
      }
    },
    [chapterId]
  );

  // Auto-hide controls
  const resetControlsTimer = useCallback(() => {
    if (controlsTimer) {
      clearTimeout(controlsTimer);
    }

    setShowControls(true);
    const timer = setTimeout(() => {
      setShowControls(false);
    }, 3000);

    setControlsTimer(timer);
  }, [controlsTimer]);

  // Page navigation functions
  const goToPage = useCallback(
    (page: number) => {
      if (!pagesInfo || page < 1 || page > pagesInfo.total_pages) return;

      setCurrentPage(page);
      updateProgress({ page });
      resetControlsTimer();
    },
    [pagesInfo, updateProgress, resetControlsTimer]
  );

  const nextPage = useCallback(() => {
    if (!pagesInfo || currentPage >= pagesInfo.total_pages) return;
    goToPage(currentPage + 1);
  }, [currentPage, pagesInfo, goToPage]);

  const prevPage = useCallback(() => {
    if (currentPage <= 1) return;
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  const firstPage = useCallback(() => {
    goToPage(1);
  }, [goToPage]);

  const lastPage = useCallback(() => {
    if (!pagesInfo) return;
    goToPage(pagesInfo.total_pages);
  }, [pagesInfo, goToPage]);

  // Fullscreen handling
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
    resetControlsTimer();
  }, [resetControlsTimer]);

  const exitReader = useCallback(() => {
    if (chapter?.series) {
      router.push(`/library/series/${chapter.series.id}`);
    } else {
      router.push('/library');
    }
  }, [router, chapter]);

  const toggleControls = useCallback(() => {
    setShowControls((prev) => !prev);
    resetControlsTimer();
  }, [resetControlsTimer]);

  // Keyboard navigation
  useKeyboardNavigation({
    onNextPage: nextPage,
    onPrevPage: prevPage,
    onFirstPage: firstPage,
    onLastPage: lastPage,
    onToggleFullscreen: toggleFullscreen,
    onExit: exitReader,
  });

  // Touch navigation
  const { setContainer } = useTouchNavigation({
    onNextPage: nextPage,
    onPrevPage: prevPage,
    onToggleControls: toggleControls,
  });

  // Page preloading
  const pagesToPreload = useMemo(() => {
    if (!pagesInfo) return [];

    const pages = [];
    const preloadRange = 2;

    // Preload current page and surrounding pages
    for (
      let i = Math.max(1, currentPage - preloadRange);
      i <= Math.min(pagesInfo.total_pages, currentPage + preloadRange);
      i++
    ) {
      if (!preloadedPages.has(i)) {
        pages.push(i);
      }
    }

    return pages;
  }, [currentPage, pagesInfo, preloadedPages]);

  // Current page URL
  const currentPageUrl = useMemo(() => {
    if (!pagesInfo) return '';
    return chaptersApi.getChapterPageUrl(chapterId, currentPage);
  }, [chapterId, currentPage, pagesInfo]);

  // Load annotations for current page
  const loadPageAnnotations = useCallback(async (pageNumber: number) => {
    try {
      const annotations = await annotationsApi.getPageAnnotations(chapterId, pageNumber);
      setPageAnnotations(prev => ({
        ...prev,
        [pageNumber]: annotations,
      }));
    } catch (error) {
      console.error('Failed to load page annotations:', error);
    }
  }, [chapterId]);

  // Annotation handlers
  const handlePageClick = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (!annotationMode) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;

    setAnnotationFormPosition({ x, y });
    setShowAnnotationForm(true);
    setAnnotationMode(false);
  }, [annotationMode]);

  const handleCreateAnnotation = useCallback(async (data: AnnotationCreate) => {
    try {
      await annotationsApi.createAnnotation(data);
      
      // Refresh page annotations
      if (data.page_number) {
        await loadPageAnnotations(data.page_number);
      }
      
      setShowAnnotationForm(false);
      setAnnotationFormPosition(null);
      
      toast({
        title: 'Success',
        description: 'Annotation created successfully',
      });
    } catch (error) {
      console.error('Failed to create annotation:', error);
      toast({
        title: 'Error',
        description: 'Failed to create annotation',
        variant: 'destructive',
      });
      throw error;
    }
  }, [loadPageAnnotations]);

  const handleUpdateAnnotation = useCallback(async (annotationId: string, data: AnnotationUpdate) => {
    try {
      await annotationsApi.updateAnnotation(annotationId, data);
      
      // Refresh page annotations
      await loadPageAnnotations(currentPage);
      
      toast({
        title: 'Success',
        description: 'Annotation updated successfully',
      });
    } catch (error) {
      console.error('Failed to update annotation:', error);
      toast({
        title: 'Error',
        description: 'Failed to update annotation',
        variant: 'destructive',
      });
      throw error;
    }
  }, [loadPageAnnotations, currentPage]);

  const handleDeleteAnnotation = useCallback(async (annotationId: string) => {
    try {
      await annotationsApi.deleteAnnotation(annotationId);
      
      // Refresh page annotations
      await loadPageAnnotations(currentPage);
      
      setSelectedAnnotation(null);
      
      toast({
        title: 'Success',
        description: 'Annotation deleted successfully',
      });
    } catch (error) {
      console.error('Failed to delete annotation:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete annotation',
        variant: 'destructive',
      });
    }
  }, [loadPageAnnotations, currentPage]);

  const handleAnnotationSelect = useCallback((annotation: AnnotationResponse) => {
    setSelectedAnnotation(annotation);
    
    // Jump to annotation page if different from current
    if (annotation.page_number && annotation.page_number !== currentPage) {
      goToPage(annotation.page_number);
    }
  }, [currentPage]);

  const toggleAnnotationMode = useCallback(() => {
    setAnnotationMode(prev => !prev);
    if (!annotationMode) {
      toast({
        title: 'Annotation Mode',
        description: 'Click anywhere on the page to add an annotation',
      });
    }
  }, [annotationMode]);

  // Load annotations when page changes
  useEffect(() => {
    if (currentPage && !pageAnnotations[currentPage]) {
      loadPageAnnotations(currentPage);
    }
  }, [currentPage, pageAnnotations, loadPageAnnotations]);

  // Mark chapter as read when reaching the last page
  useEffect(() => {
    if (pagesInfo && currentPage === pagesInfo.total_pages && !chapter?.is_read) {
      updateProgress({ page: currentPage, isRead: true });
    }
  }, [currentPage, pagesInfo, chapter?.is_read, updateProgress]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (controlsTimer) {
        clearTimeout(controlsTimer);
      }
    };
  }, [controlsTimer]);

  // Fullscreen change handler
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Loading state
  if (chapterLoading || pagesLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4 text-white">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p>Loading chapter...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (chapterError || pagesError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4 text-center text-white">
          <AlertCircle className="h-12 w-12 text-red-400" />
          <div>
            <h2 className="text-xl font-semibold">Failed to load chapter</h2>
            <p className="text-white/70">Please check your connection and try again</p>
          </div>
          <Button onClick={() => router.back()} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  if (!chapter || !pagesInfo) {
    return null;
  }

  return (
    <div
      ref={setContainer}
      className={cn(
        'relative min-h-screen bg-slate-950 text-white',
        'select-none overflow-hidden',
        className
      )}
      onMouseMove={resetControlsTimer}
      onTouchStart={resetControlsTimer}
      data-testid="manga-reader"
    >
      {/* Header controls */}
      <div
        className={cn(
          'fixed left-0 right-0 top-0 z-40 bg-gradient-to-b from-black/80 to-transparent p-4 transition-all duration-300',
          showControls ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={exitReader}
              className="hover:bg-white/20"
              aria-label="Exit reader"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="font-semibold">{chapter.series_title}</h1>
              <div className="space-y-1">
                <p className="text-sm text-white/70">
                  Chapter {chapter.chapter_number}
                  {chapter.title && ` - ${chapter.title}`}
                </p>
                <div className="flex items-center gap-2 text-xs text-white/60">
                  <span data-testid="page-counter">
                    {currentPage} / {pagesInfo.total_pages}
                  </span>
                  <span>•</span>
                  <span data-testid="progress-text">
                    Progress: {Math.round((currentPage / pagesInfo.total_pages) * 100)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleAnnotationMode}
              className={cn(
                "hover:bg-white/20",
                annotationMode && "bg-white/20 text-blue-400"
              )}
              aria-label="Toggle annotation mode"
              title="Add annotation"
            >
              <MessageSquare className="h-4 w-4" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowAnnotationDrawer(true)}
              className="hover:bg-white/20"
              aria-label="Show annotations"
              title="View annotations"
            >
              <MessageSquare className="h-4 w-4" />
              {pageAnnotations[currentPage]?.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {pageAnnotations[currentPage].length}
                </span>
              )}
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={toggleFullscreen}
              className="hover:bg-white/20"
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex min-h-screen items-center justify-center p-4">
        <div 
          className={cn(
            "relative max-w-full",
            annotationMode && "cursor-crosshair"
          )}
          onClick={handlePageClick}
        >
          <MangaPage
            src={currentPageUrl}
            alt={`Page ${currentPage} of ${chapter.series_title} Chapter ${chapter.chapter_number}`}
            pageNumber={currentPage}
            priority={true}
            className="max-h-[calc(100vh-2rem)]"
          />
          
          {/* Annotation markers */}
          {pageAnnotations[currentPage]?.map((annotation) => (
            <AnnotationMarker
              key={annotation.id}
              annotation={annotation}
              isSelected={selectedAnnotation?.id === annotation.id}
              onClick={() => setSelectedAnnotation(annotation)}
              onEdit={() => {
                // TODO: Implement edit functionality
                console.log('Edit annotation:', annotation);
              }}
              onDelete={() => handleDeleteAnnotation(annotation.id)}
            />
          ))}

          {/* Annotation mode overlay */}
          {annotationMode && (
            <div className={cn(
              "absolute inset-0 bg-blue-500/10 border-2 border-dashed border-blue-400",
              "flex items-center justify-center text-blue-400 font-medium",
              "pointer-events-none"
            )}>
              <div className="bg-blue-900/80 px-4 py-2 rounded-lg text-white">
                Click anywhere to add an annotation
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preload adjacent pages */}
      <div className="hidden">
        {pagesToPreload.map((pageNum) => (
          <MangaPage
            key={pageNum}
            src={chaptersApi.getChapterPageUrl(chapterId, pageNum)}
            alt={`Preload page ${pageNum}`}
            pageNumber={pageNum}
            onLoad={() => {
              setPreloadedPages((prev) => {
                const newSet = new Set(prev);
                newSet.add(pageNum);
                return newSet;
              });
            }}
          />
        ))}
      </div>

      {/* Page navigation controls */}
      <PageNavigation
        currentPage={currentPage}
        totalPages={pagesInfo.total_pages}
        onPageChange={goToPage}
        onPrevPage={prevPage}
        onNextPage={nextPage}
        onFirstPage={firstPage}
        onLastPage={lastPage}
        onClose={exitReader}
        show={showControls}
      />

      {/* Annotation Drawer */}
      <AnnotationDrawer
        chapterId={chapterId}
        isOpen={showAnnotationDrawer}
        onClose={() => setShowAnnotationDrawer(false)}
        onAnnotationSelect={handleAnnotationSelect}
        onAnnotationCreate={() => {
          // Refresh current page annotations
          loadPageAnnotations(currentPage);
        }}
      />

      {/* Annotation Form Modal */}
      {showAnnotationForm && annotationFormPosition && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-60 flex items-center justify-center p-4">
          <AnnotationForm
            chapterId={chapterId}
            pageNumber={currentPage}
            position={annotationFormPosition}
            onSubmit={handleCreateAnnotation}
            onCancel={() => {
              setShowAnnotationForm(false);
              setAnnotationFormPosition(null);
            }}
          />
        </div>
      )}
    </div>
  );
}
