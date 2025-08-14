/**
 * Unit Tests for WatchToggle Component
 * Following the testing strategy: Jest + React Testing Library
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { WatchToggle } from '@/components/library/watch-toggle';
import { TEST_SERIES_DATA } from '../fixtures/manga-test-data';

// Mock the hooks
jest.mock('@/hooks/use-watching', () => ({
  useWatching: jest.fn()
}));

jest.mock('@/hooks/use-toast', () => ({
  useToast: jest.fn()
}));

const mockToggleWatch = jest.fn();
const mockToast = jest.fn();

describe('WatchToggle Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    const { useWatching } = require('@/hooks/use-watching');
    const { useToast } = require('@/hooks/use-toast');
    
    useWatching.mockReturnValue({
      toggleWatch: mockToggleWatch,
      isLoading: false
    });
    
    useToast.mockReturnValue({
      toast: mockToast
    });
  });

  describe('Button Variant', () => {
    it('should render start watching button for unwatched series', () => {
      const testSeries = TEST_SERIES_DATA.find(s => !s.watching_enabled);
      expect(testSeries).toBeDefined();

      render(
        <WatchToggle 
          seriesId={testSeries!.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
      expect(button).toHaveAttribute('aria-label', 'Start watching');
      expect(button).toHaveTextContent('Watch');
    });

    it('should render stop watching button for watched series', () => {
      const testSeries = TEST_SERIES_DATA.find(s => s.watching_enabled);
      expect(testSeries).toBeDefined();

      render(
        <WatchToggle 
          seriesId={testSeries!.id}
          isWatching={true}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Stop watching');
      expect(button).toHaveTextContent('Watching');
    });

    it('should have correct data-testid', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByTestId(`watch-toggle-${testSeries.id}`);
      expect(button).toBeInTheDocument();
    });
  });

  describe('Badge Variant', () => {
    it('should render badge with correct styling for unwatched series', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="badge"
        />
      );

      const badge = screen.getByTestId(`watch-toggle-${testSeries.id}`);
      expect(badge).toHaveTextContent('Watch');
      expect(badge).toHaveAttribute('aria-label', 'Start watching');
    });

    it('should render badge with correct styling for watched series', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={true}
          variant="badge"
        />
      );

      const badge = screen.getByTestId(`watch-toggle-${testSeries.id}`);
      expect(badge).toHaveTextContent('Watching');
      expect(badge).toHaveAttribute('aria-label', 'Stop watching');
    });
  });

  describe('Icon Variant', () => {
    it('should render icon button with correct accessibility', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="icon"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Start watching');
    });
  });

  describe('User Interactions', () => {
    it('should call toggleWatch when clicked', async () => {
      const user = userEvent.setup();
      const testSeries = TEST_SERIES_DATA[0];
      
      mockToggleWatch.mockResolvedValue(true);

      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      await user.click(button);

      expect(mockToggleWatch).toHaveBeenCalledWith(testSeries.id, false);
    });

    it('should show success toast on successful toggle', async () => {
      const user = userEvent.setup();
      const testSeries = TEST_SERIES_DATA[0];
      
      mockToggleWatch.mockResolvedValue(true);

      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      await user.click(button);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Now watching',
          description: "You'll be notified about new chapters",
          variant: 'default'
        });
      });
    });

    it('should show error toast on failed toggle', async () => {
      const user = userEvent.setup();
      const testSeries = TEST_SERIES_DATA[0];
      
      mockToggleWatch.mockRejectedValue(new Error('API Error'));

      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      await user.click(button);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Error',
          description: 'Failed to update watch status. Please try again.',
          variant: 'destructive'
        });
      });
    });

    it('should update local state immediately for responsive UI', async () => {
      const user = userEvent.setup();
      const testSeries = TEST_SERIES_DATA[0];
      
      mockToggleWatch.mockResolvedValue(true);

      const { rerender } = render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveTextContent('Watch');

      await user.click(button);

      // Local state should update immediately
      await waitFor(() => {
        expect(button).toHaveTextContent('Watching');
        expect(button).toHaveAttribute('aria-label', 'Stop watching');
      });
    });
  });

  describe('Loading States', () => {
    it('should disable button when loading', () => {
      const { useWatching } = require('@/hooks/use-watching');
      useWatching.mockReturnValue({
        toggleWatch: mockToggleWatch,
        isLoading: true
      });

      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should show loading styles when loading', () => {
      const { useWatching } = require('@/hooks/use-watching');
      useWatching.mockReturnValue({
        toggleWatch: mockToggleWatch,
        isLoading: true
      });

      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="badge"
        />
      );

      const badge = screen.getByTestId(`watch-toggle-${testSeries.id}`);
      expect(badge).toHaveClass('opacity-50', 'cursor-not-allowed');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Start watching');
    });

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      const testSeries = TEST_SERIES_DATA[0];
      
      mockToggleWatch.mockResolvedValue(true);

      render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      button.focus();
      expect(button).toHaveFocus();

      await user.keyboard('{Enter}');
      expect(mockToggleWatch).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined isWatching prop', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      render(
        <WatchToggle 
          seriesId={testSeries.id}
          variant="button"
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Start watching');
      expect(button).toHaveTextContent('Watch');
    });

    it('should handle prop changes', () => {
      const testSeries = TEST_SERIES_DATA[0];
      
      const { rerender } = render(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={false}
          variant="button"
        />
      );

      let button = screen.getByRole('button');
      expect(button).toHaveTextContent('Watch');

      rerender(
        <WatchToggle 
          seriesId={testSeries.id}
          isWatching={true}
          variant="button"
        />
      );

      button = screen.getByRole('button');
      expect(button).toHaveTextContent('Watching');
    });
  });
});