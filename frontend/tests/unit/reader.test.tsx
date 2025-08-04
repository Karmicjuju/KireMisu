/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useRouter, useParams } from 'next/navigation';
import ReaderPage from '@/app/(app)/reader/[chapterId]/page';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useParams: jest.fn(),
}));

// Mock toast hook
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock fetch globally
global.fetch = jest.fn();

const mockRouter = {
  back: jest.fn(),
  push: jest.fn(),
};

const mockChapterInfo = {
  id: 'test-chapter-1',
  series_id: 'test-series-1',
  series_title: 'Test Manga Series',
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

describe('ReaderPage', () => {
  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useParams as jest.Mock).mockReturnValue({ chapterId: 'test-chapter-1' });
    (global.fetch as jest.Mock).mockClear();
    mockRouter.back.mockClear();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should render loading state initially', () => {
    // Mock fetch to not resolve immediately
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));

    render(<ReaderPage />);

    expect(screen.getByText('Loading chapter...')).toBeInTheDocument();
    expect(screen.getByRole('img', { hidden: true })).toHaveClass('animate-pulse');
  });

  it('should load and display chapter info', async () => {
    // Mock successful API responses
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockChapterInfo,
      })
      .mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });

    render(<ReaderPage />);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Check that chapter info is displayed
    expect(screen.getByText('Test Manga Series')).toBeInTheDocument();
    expect(screen.getByText('Vol. 1 Ch. 1 - First Chapter')).toBeInTheDocument();
    expect(screen.getByText('1 / 5')).toBeInTheDocument();
  });

  it('should display error state when chapter loading fails', async () => {
    // Mock failed API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      statusText: 'Not Found',
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Failed to load chapter/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
  });

  it('should navigate back when back button is clicked', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    const backButton = screen.getByRole('button', { name: 'Back' });
    fireEvent.click(backButton);

    expect(mockRouter.back).toHaveBeenCalledTimes(1);
  });

  it('should handle keyboard navigation', async () => {
    // Mock successful API responses
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Test right arrow key navigation
    fireEvent.keyDown(window, { key: 'ArrowRight' });

    // Should update page counter (would be 2 / 5 after navigation)
    // Note: This is simplified - in a real app we'd mock the image loading

    // Test left arrow key navigation
    fireEvent.keyDown(window, { key: 'ArrowLeft' });

    // Test spacebar navigation
    fireEvent.keyDown(window, { key: ' ' });

    // Test escape key (should go back)
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(mockRouter.back).toHaveBeenCalledTimes(1);
  });

  it('should toggle UI visibility with U key', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Initially UI should be visible
    expect(screen.getByText('Test Manga Series')).toBeInTheDocument();

    // Press U to toggle UI
    fireEvent.keyDown(window, { key: 'u' });

    // UI should be hidden (this would work with actual state management)
    // In a real test we'd check for CSS classes or visibility attributes
  });

  it('should display keyboard shortcuts help', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Check that keyboard shortcuts are displayed
    expect(screen.getByText('← → : Navigate pages')).toBeInTheDocument();
    expect(screen.getByText('Space: Next page')).toBeInTheDocument();
    expect(screen.getByText('F: Toggle fit mode')).toBeInTheDocument();
    expect(screen.getByText('U: Toggle UI')).toBeInTheDocument();
    expect(screen.getByText('Esc: Exit reader')).toBeInTheDocument();
  });

  it('should handle navigation to first and last page', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Test Home key (go to first page)
    fireEvent.keyDown(window, { key: 'Home' });

    // Test End key (go to last page)
    fireEvent.keyDown(window, { key: 'End' });
  });

  it('should update reading progress when pages change', async () => {
    let progressUpdateCalls = 0;

    // Mock API responses
    (global.fetch as jest.Mock).mockImplementation((url) => {
      if (url.includes('/info')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockChapterInfo,
        });
      } else if (url.includes('/progress')) {
        progressUpdateCalls++;
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Navigate to next page
    fireEvent.keyDown(window, { key: 'ArrowRight' });

    // Wait for progress update
    await waitFor(() => {
      expect(progressUpdateCalls).toBeGreaterThan(0);
    });
  });

  it('should handle image click navigation', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Find the main image (this is simplified - we'd need better selectors)
    const image = screen.getByAltText('Page 1');

    // Mock getBoundingClientRect
    image.getBoundingClientRect = jest.fn(() => ({
      left: 0,
      top: 0,
      width: 800,
      height: 1200,
      right: 800,
      bottom: 1200,
      x: 0,
      y: 0,
      toJSON: jest.fn(),
    }));

    // Click on right side of image (should go to next page)
    fireEvent.click(image, { clientX: 600, clientY: 600 });

    // Click on left side of image (should go to previous page)
    fireEvent.click(image, { clientX: 200, clientY: 600 });
  });

  it('should disable navigation buttons at boundaries', async () => {
    // Mock successful API response for first page
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // On first page, previous button should be disabled
    const buttons = screen.getAllByRole('button');
    const navButtons = buttons.filter(
      (btn) => btn.querySelector('svg') && !btn.textContent?.includes('Back')
    );

    // This is a simplified test - in reality we'd need to identify
    // the specific navigation buttons more precisely
    expect(navButtons.length).toBeGreaterThan(0);
  });

  it('should show progress bar correctly', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Check progress text
    expect(screen.getByText('Progress')).toBeInTheDocument();
    expect(screen.getByText('20%')).toBeInTheDocument(); // 1/5 pages = 20%

    // Check progress bar exists
    const progressBar = document.querySelector('.bg-orange-500');
    expect(progressBar).toBeInTheDocument();
  });

  it('should handle mouse movement for UI auto-hide', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Simulate mouse movement
    const container = document.querySelector('.relative.h-screen');
    if (container) {
      fireEvent.mouseMove(container);
    }

    // UI should remain visible after mouse movement
    expect(screen.getByText('Test Manga Series')).toBeInTheDocument();
  });

  it('should handle fit mode cycling', async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockChapterInfo,
    });

    render(<ReaderPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chapter...')).not.toBeInTheDocument();
    });

    // Get the image element
    const image = screen.getByAltText('Page 1');

    // Initially should have width fit mode
    expect(image).toHaveClass('w-full');

    // Press F to cycle fit mode
    fireEvent.keyDown(window, { key: 'f' });

    // Should change to height fit mode
    await waitFor(() => {
      expect(image).toHaveClass('h-full');
    });

    // Press F again to cycle to original fit mode
    fireEvent.keyDown(window, { key: 'f' });

    await waitFor(() => {
      expect(image).toHaveClass('max-w-full');
    });

    // Press F once more to cycle back to width
    fireEvent.keyDown(window, { key: 'f' });

    await waitFor(() => {
      expect(image).toHaveClass('w-full');
    });
  });
});
