/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';
import { MangaReader } from '@/components/reader/manga-reader';
import useSWR from 'swr';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock toast hook
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
  toast: jest.fn(),
}));

// Mock SWR
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(),
  mutate: jest.fn(),
}));

// Mock the keyboard navigation hook specifically for this test
jest.mock('@/components/reader/use-keyboard-navigation', () => ({
  useKeyboardNavigation: jest.fn(() => ({
    shortcuts: {
      'ArrowLeft': jest.fn(),
      'ArrowRight': jest.fn(),
      'Home': jest.fn(),
      'End': jest.fn(),
      'Escape': jest.fn()
    },
    isActive: true
  })),
}));

jest.mock('@/components/reader/use-touch-navigation', () => ({
  useTouchNavigation: jest.fn(() => ({ setContainer: jest.fn() })),
}));

// Mock the page navigation component
jest.mock('@/components/reader/page-navigation', () => ({
  PageNavigation: ({ show, onClose }: any) => 
    show ? (
      <div data-testid="page-navigation">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

// Mock the manga page component
jest.mock('@/components/reader/manga-page', () => ({
  MangaPage: ({ alt, pageNumber, onLoad }: any) => {
    // Simulate image load
    if (onLoad) setTimeout(onLoad, 0);
    return <img alt={alt} data-testid={`page-${pageNumber}`} />;
  },
}));

// Mock the API module
jest.mock('@/lib/api', () => ({
  chaptersApi: {
    getChapter: jest.fn(),
    getChapterPages: jest.fn(),
    getChapterPageUrl: jest.fn().mockReturnValue('/api/test.jpg'),
    updateChapterProgress: jest.fn(),
  },
  annotationsApi: {
    getPageAnnotations: jest.fn().mockImplementation(() => {
      // Prevent async calls that cause act() warnings
      const promise = Promise.resolve([]);
      // Don't actually make the call during tests
      return promise;
    }),
    createAnnotation: jest.fn(),
    updateAnnotation: jest.fn(),
    deleteAnnotation: jest.fn(),
  },
}));

// Mock the annotation components
jest.mock('@/components/annotations', () => ({
  AnnotationMarker: ({ annotation, onClick }: any) => (
    <div data-testid={`annotation-${annotation.id}`} onClick={onClick}>
      {annotation.content}
    </div>
  ),
  AnnotationDrawer: ({ isOpen, children }: any) => 
    isOpen ? <div data-testid="annotation-drawer">{children}</div> : null,
  AnnotationForm: ({ onSubmit, onCancel }: any) => (
    <div data-testid="annotation-form">
      <button onClick={() => onSubmit({ content: 'test', type: 'note' })}>Submit</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

const mockRouter = {
  back: jest.fn(),
  push: jest.fn(),
};

const mockChapterInfo = {
  id: 'test-chapter-1',
  series_id: 'test-series-1',
  series_title: 'Test Manga Series',
  series: {
    id: 'test-series-1',
    title: 'Test Manga Series',
  },
  chapter_number: 1,
  volume_number: 1,
  title: 'First Chapter',
  page_count: 5,
  is_read: false,
  last_read_page: 0,
  read_at: null,
  file_size: 1024000,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const mockPagesInfo = {
  total_pages: 5,
  current_page: 1,
};

describe('MangaReader', () => {
  const setupLoadedState = () => {
    let callCount = 0;
    (useSWR as jest.Mock).mockImplementation((key) => {
      callCount++;
      if (callCount === 1) {
        // First call - chapter data
        return {
          data: mockChapterInfo,
          error: undefined,
          isLoading: false,
        };
      } else {
        // Second call - pages data
        return {
          data: mockPagesInfo,
          error: undefined,
          isLoading: false,
        };
      }
    });
  };

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    mockRouter.back.mockClear();
    mockRouter.push.mockClear();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should render loading state initially', () => {
    // Mock SWR to return loading state
    (useSWR as jest.Mock).mockReturnValue({
      data: undefined,
      error: undefined,
      isLoading: true,
    });

    render(<MangaReader chapterId="test-chapter-1" />);

    expect(screen.getByText('Loading chapter...')).toBeInTheDocument();
  });

  it('should render error state when chapter loading fails', () => {
    // Mock SWR to return error state
    (useSWR as jest.Mock).mockReturnValue({
      data: undefined,
      error: new Error('Failed to load'),
      isLoading: false,
    });

    render(<MangaReader chapterId="test-chapter-1" />);

    expect(screen.getByText('Failed to load chapter')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
  });

  it('should render chapter info when loaded successfully', () => {
    setupLoadedState();

    render(<MangaReader chapterId="test-chapter-1" />);

    // Check that chapter info is displayed in header
    expect(screen.getByText('Test Manga Series')).toBeInTheDocument();
    expect(screen.getByText('Chapter 1 - First Chapter')).toBeInTheDocument();
    
    // Check that page is rendered (use alt text to avoid duplicate testid)
    expect(screen.getByAltText('Page 1 of Test Manga Series Chapter 1')).toBeInTheDocument();
  });

  it('should navigate back when exit button is clicked', () => {
    setupLoadedState();

    render(<MangaReader chapterId="test-chapter-1" />);

    const exitButton = screen.getByRole('button', { name: 'Back' });
    fireEvent.click(exitButton);

    expect(mockRouter.push).toHaveBeenCalledWith('/library/series/test-series-1');
  });

  it('should toggle fullscreen when fullscreen button is clicked', () => {
    setupLoadedState();

    // Mock fullscreen API
    Object.defineProperty(document, 'fullscreenElement', {
      value: null,
      writable: true,
    });
    
    const mockRequestFullscreen = jest.fn();
    Object.defineProperty(document.documentElement, 'requestFullscreen', {
      value: mockRequestFullscreen,
      writable: true,
    });

    render(<MangaReader chapterId="test-chapter-1" />);

    const fullscreenButton = screen.getByRole('button', { name: 'Enter fullscreen' });
    fireEvent.click(fullscreenButton);

    expect(mockRequestFullscreen).toHaveBeenCalled();
  });

  it('should show annotation mode when annotation button is clicked', () => {
    setupLoadedState();

    render(<MangaReader chapterId="test-chapter-1" />);

    const annotationButton = screen.getByRole('button', { name: 'Toggle annotation mode' });
    fireEvent.click(annotationButton);

    // Should show annotation mode overlay
    expect(screen.getByText('Click anywhere to add an annotation')).toBeInTheDocument();
  });

  it('should render with custom initial page', () => {
    setupLoadedState();

    render(<MangaReader chapterId="test-chapter-1" initialPage={3} />);

    // Should render the specified initial page (main page, not preload)
    const mainPageImage = screen.getByAltText('Page 3 of Test Manga Series Chapter 1');
    expect(mainPageImage).toBeInTheDocument();
    expect(mainPageImage).toHaveAttribute('data-testid', 'page-3');
  });
});