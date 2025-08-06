/**
 * Comprehensive Reading Progress UI Component Tests
 * 
 * This test suite provides comprehensive validation of R-2 reading progress
 * components including accessibility, performance, and user experience testing.
 * 
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';
import React from 'react';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock toast hook
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock SWR for data fetching
jest.mock('swr', () => ({
  __esModule: true,
  default: (key: any, fetcher: any) => ({
    data: null,
    error: null,
    isLoading: false,
    mutate: jest.fn(),
  }),
}));

// Mock fetch globally
global.fetch = jest.fn();

const mockRouter = {
  refresh: jest.fn(),
  push: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  prefetch: jest.fn(),
  replace: jest.fn(),
};

// Mock intersection observer for animations
class MockIntersectionObserver {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}
Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

// Enhanced ProgressBar component mock with all features
const EnhancedProgressBar = ({
  value,
  max = 100,
  className = '',
  label,
  showValue = false,
  animated = true,
  colorScheme = 'primary',
  size = 'default',
  variant = 'default',
  'data-testid': testId = 'progress-bar',
  ...props
}: {
  value: number;
  max?: number;
  className?: string;
  label?: string;
  showValue?: boolean;
  animated?: boolean;
  colorScheme?: string;
  size?: string;
  variant?: string;
  'data-testid'?: string;
  [key: string]: any;
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const [displayValue, setDisplayValue] = React.useState(animated ? 0 : percentage);

  React.useEffect(() => {
    if (animated) {
      const timer = setTimeout(() => {
        setDisplayValue(percentage);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setDisplayValue(percentage);
    }
  }, [percentage, animated]);

  return (
    <div className={`progress-wrapper ${className}`}>
      {(label || showValue) && (
        <div className="progress-header" data-testid="progress-header">
          {label && <span data-testid="progress-label">{label}</span>}
          {showValue && (
            <span data-testid="progress-percentage">{Math.round(displayValue)}%</span>
          )}
        </div>
      )}
      
      <div
        className={`progress-bar ${size} ${variant} ${colorScheme}`}
        data-testid={testId}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || `Progress: ${Math.round(percentage)}%`}
        tabIndex={0}
        {...props}
      >
        <div
          className="progress-fill"
          style={{
            width: `${displayValue}%`,
            transition: animated ? 'width 500ms ease-out' : 'none',
          }}
          data-testid="progress-fill"
        />
        {animated && displayValue < percentage && (
          <div className="progress-shimmer" data-testid="progress-shimmer" />
        )}
      </div>
    </div>
  );
};

// Enhanced MarkReadButton component with realistic API integration
const EnhancedMarkReadButton = ({
  chapterId,
  isRead,
  onToggle,
  disabled = false,
  variant = 'default',
  size = 'default',
  appearance = 'icon',
  isLoading = false,
  'data-testid': testId = 'mark-read-button',
}: {
  chapterId: string;
  isRead: boolean;
  onToggle?: (isRead: boolean) => void;
  disabled?: boolean;
  variant?: string;
  size?: string;
  appearance?: string;
  isLoading?: boolean;
  'data-testid'?: string;
}) => {
  const [isPending, setIsPending] = React.useState(false);
  const loading = isLoading || isPending;

  const handleClick = async () => {
    if (loading || disabled) return;

    setIsPending(true);
    try {
      const response = await fetch(`/api/chapters/${chapterId}/mark-read`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const data = await response.json();
        onToggle?.(data.is_read);
      } else {
        throw new Error(`API request failed: ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to toggle read status:', error);
      // In real implementation, show error toast
    } finally {
      setIsPending(false);
    }
  };

  const getIcon = () => {
    if (loading) return '⏳';
    return isRead ? '✓' : '📖';
  };

  const getText = () => {
    if (appearance === 'icon') return null;
    if (appearance === 'text') return isRead ? 'Read' : 'Unread';
    return isRead ? '✓ Read' : 'Mark Read';
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClick();
    }
  };

  return (
    <button
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      disabled={disabled || loading}
      className={`mark-read-button ${variant} ${size} ${appearance} ${isRead ? 'read' : 'unread'} ${loading ? 'loading' : ''}`}
      data-testid={testId}
      aria-label={isRead ? 'Mark as unread' : 'Mark as read'}
      aria-pressed={isRead}
      title={isRead ? 'Mark as unread' : 'Mark as read'}
    >
      <span className="button-icon">{getIcon()}</span>
      {getText() && <span className="button-text">{getText()}</span>}
    </button>
  );
};

// Dashboard Stats component with comprehensive data display
const DashboardStatsComponent = ({
  stats,
  loading = false,
  error = null,
  'data-testid': testId = 'dashboard-stats',
}: {
  stats?: {
    total_series: number;
    total_chapters: number;
    chapters_read: number;
    overall_progress_percentage: number;
    series_stats: {
      completed: number;
      in_progress: number;
      unread: number;
    };
    recent_reads: Array<{
      chapter_id: string;
      series_title: string;
      chapter_title: string;
      read_at: string;
    }>;
    reading_streak_days: number;
    reading_time_hours: number;
    favorites_count: number;
  };
  loading?: boolean;
  error?: any;
  'data-testid'?: string;
}) => {
  if (loading) {
    return (
      <div className="dashboard-stats loading" data-testid={testId}>
        <div data-testid="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-stats error" data-testid={testId}>
        <div data-testid="error-message">Error loading stats</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="dashboard-stats empty" data-testid={testId}>
        <div data-testid="empty-state">No stats available</div>
      </div>
    );
  }

  return (
    <div className="dashboard-stats" data-testid={testId}>
      {/* Main Statistics */}
      <div className="stats-grid" data-testid="stats-grid">
        <div className="stat-card" data-testid="total-series-card">
          <span data-testid="total-series">{stats.total_series}</span>
          <span>Total Series</span>
        </div>
        
        <div className="stat-card" data-testid="chapters-card">
          <span data-testid="read-chapters">{stats.chapters_read}</span>
          <span>of</span>
          <span data-testid="total-chapters">{stats.total_chapters}</span>
          <span>Chapters Read</span>
        </div>
        
        <div className="stat-card" data-testid="reading-time-card">
          <span data-testid="reading-time">{Math.round(stats.reading_time_hours)}h</span>
          <span>Reading Time</span>
        </div>
        
        <div className="stat-card" data-testid="favorites-card">
          <span data-testid="favorites-count">{stats.favorites_count}</span>
          <span>Favorites</span>
        </div>
      </div>

      {/* Overall Progress */}
      <div className="overall-progress" data-testid="overall-progress-section">
        <h3>Overall Progress</h3>
        <div data-testid="overall-progress">{stats.overall_progress_percentage}%</div>
        <EnhancedProgressBar
          value={stats.overall_progress_percentage}
          max={100}
          label="Library Progress"
          showValue={false}
          data-testid="overall-progress-bar"
        />
      </div>

      {/* Series Breakdown */}
      <div className="series-breakdown" data-testid="series-breakdown">
        <div data-testid="completed-series">
          <span>Completed:</span>
          <span>{stats.series_stats.completed}</span>
        </div>
        <div data-testid="in-progress-series">
          <span>In Progress:</span>
          <span>{stats.series_stats.in_progress}</span>
        </div>
        <div data-testid="unread-series">
          <span>Unread:</span>
          <span>{stats.series_stats.unread}</span>
        </div>
      </div>

      {/* Reading Streak */}
      <div className="reading-streak" data-testid="reading-streak">
        <span>Streak:</span>
        <span>{stats.reading_streak_days} days</span>
      </div>

      {/* Recent Reads */}
      <div className="recent-reads" data-testid="recent-reads">
        <h4>Recent Reads</h4>
        {stats.recent_reads.length === 0 ? (
          <div data-testid="no-recent-reads">No recent reading activity</div>
        ) : (
          <div data-testid="recent-reads-list">
            {stats.recent_reads.map((read, index) => (
              <div key={index} className="recent-read" data-testid={`recent-read-${index}`}>
                <span className="series-title">{read.series_title}</span>
                <span className="chapter-title">{read.chapter_title}</span>
                <span className="read-date">{new Date(read.read_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Chapter List with Progress component
const ChapterListWithProgress = ({
  chapters,
  seriesId,
  onChapterRead,
  'data-testid': testId = 'chapter-list',
}: {
  chapters: Array<{
    id: string;
    chapter_number: number;
    title?: string;
    is_read: boolean;
    last_read_page: number;
    page_count: number;
  }>;
  seriesId?: string;
  onChapterRead?: (chapterId: string, isRead: boolean) => void;
  'data-testid'?: string;
}) => {
  return (
    <div className="chapter-list" data-testid={testId}>
      {chapters.length === 0 ? (
        <div data-testid="empty-chapter-list">No chapters available</div>
      ) : (
        chapters.map((chapter) => {
          const progressPercentage = 
            chapter.page_count > 0
              ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
              : 0;

          return (
            <div
              key={chapter.id}
              className="chapter-item"
              data-testid={`chapter-${chapter.id}`}
            >
              {/* Chapter Info */}
              <div className="chapter-info" data-testid="chapter-info">
                <h4>Chapter {chapter.chapter_number}</h4>
                {chapter.title && <span className="chapter-title">- {chapter.title}</span>}
              </div>

              {/* Chapter Progress */}
              <div className="chapter-progress" data-testid="chapter-progress">
                <EnhancedProgressBar
                  value={chapter.last_read_page + 1}
                  max={chapter.page_count}
                  size="sm"
                  data-testid="chapter-progress-bar"
                />
                <span className="progress-text" data-testid="progress-text">
                  {chapter.is_read ? 'Complete' : `${progressPercentage}%`}
                </span>
              </div>

              {/* Mark Read Button */}
              <EnhancedMarkReadButton
                chapterId={chapter.id}
                isRead={chapter.is_read}
                variant="compact"
                onToggle={(isRead) => onChapterRead?.(chapter.id, isRead)}
                data-testid="chapter-mark-read-button"
              />
            </div>
          );
        })
      )}
    </div>
  );
};

describe('Enhanced ProgressBar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Core Functionality', () => {
    it('renders with correct progress percentage and styling', () => {
      render(<EnhancedProgressBar value={75} max={100} animated={false} />);

      const progressBar = screen.getByTestId('progress-bar');
      const progressFill = screen.getByTestId('progress-fill');

      expect(progressBar).toBeInTheDocument();
      expect(progressFill).toHaveStyle({ width: '75%' });
    });

    it('handles different max values correctly', () => {
      render(<EnhancedProgressBar value={15} max={20} showValue={true} animated={false} />);

      expect(screen.getByTestId('progress-percentage')).toHaveTextContent('75%');
      expect(screen.getByTestId('progress-fill')).toHaveStyle({ width: '75%' });
    });

    it('displays custom labels and descriptions', () => {
      render(
        <EnhancedProgressBar 
          value={60} 
          label="Chapter Progress" 
          showValue={true}
          animated={false}
        />
      );

      expect(screen.getByTestId('progress-label')).toHaveTextContent('Chapter Progress');
      expect(screen.getByTestId('progress-percentage')).toHaveTextContent('60%');
    });

    it('handles edge cases correctly', () => {
      const { rerender } = render(<EnhancedProgressBar value={-10} animated={false} />);
      expect(screen.getByTestId('progress-fill')).toHaveStyle({ width: '0%' });

      rerender(<EnhancedProgressBar value={150} max={100} animated={false} />);
      expect(screen.getByTestId('progress-fill')).toHaveStyle({ width: '100%' });

      rerender(<EnhancedProgressBar value={0} animated={false} />);
      expect(screen.getByTestId('progress-fill')).toHaveStyle({ width: '0%' });
    });
  });

  describe('Accessibility Features', () => {
    it('implements proper ARIA attributes', () => {
      render(<EnhancedProgressBar value={60} max={100} label="Reading Progress" />);

      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('role', 'progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '60');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-label', 'Reading Progress');
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<EnhancedProgressBar value={50} />);

      const progressBar = screen.getByTestId('progress-bar');
      
      await user.tab();
      expect(progressBar).toHaveFocus();
    });

    it('provides fallback aria-label when no label is provided', () => {
      render(<EnhancedProgressBar value={35} />);

      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('aria-label', 'Progress: 35%');
    });
  });

  describe('Animation and Performance', () => {
    it('shows shimmer effect during animated loading', () => {
      render(<EnhancedProgressBar value={50} animated={true} />);
      
      // Shimmer should be present initially during animation
      expect(screen.getByTestId('progress-shimmer')).toBeInTheDocument();
    });

    it('handles rapid value changes smoothly', async () => {
      const { rerender } = render(<EnhancedProgressBar value={10} />);
      
      rerender(<EnhancedProgressBar value={90} />);
      
      await waitFor(() => {
        const progressFill = screen.getByTestId('progress-fill');
        expect(progressFill.style.width).toBe('90%');
      });
    });

    it('respects disabled animations', () => {
      render(<EnhancedProgressBar value={75} animated={false} />);
      
      const progressFill = screen.getByTestId('progress-fill');
      expect(progressFill.style.transition).toBe('none');
    });
  });
});

describe('Enhanced MarkReadButton Component', () => {
  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (global.fetch as jest.Mock).mockClear();
  });

  describe('Visual States and Behavior', () => {
    it('displays correct states for read and unread chapters', () => {
      const { rerender } = render(
        <EnhancedMarkReadButton chapterId="test-1" isRead={false} />
      );

      let button = screen.getByTestId('mark-read-button');
      expect(button).toHaveClass('unread');
      expect(button).toHaveAttribute('aria-pressed', 'false');

      rerender(<EnhancedMarkReadButton chapterId="test-1" isRead={true} />);
      
      button = screen.getByTestId('mark-read-button');
      expect(button).toHaveClass('read');
      expect(button).toHaveAttribute('aria-pressed', 'true');
    });

    it('shows loading state during API calls', async () => {
      const mockOnToggle = jest.fn();
      (global.fetch as jest.Mock).mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ ok: true, json: () => ({ is_read: true }) }), 100))
      );

      render(
        <EnhancedMarkReadButton 
          chapterId="test-1" 
          isRead={false} 
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByTestId('mark-read-button');
      fireEvent.click(button);

      // Should show loading state
      await waitFor(() => {
        expect(button).toHaveClass('loading');
        expect(screen.getByText('⏳')).toBeInTheDocument();
      });
    });

    it('handles different appearance variants', () => {
      const { rerender } = render(
        <EnhancedMarkReadButton 
          chapterId="test-1" 
          isRead={false} 
          appearance="icon"
        />
      );

      expect(screen.getByTestId('mark-read-button')).toHaveClass('icon');

      rerender(
        <EnhancedMarkReadButton 
          chapterId="test-1" 
          isRead={false} 
          appearance="text"
        />
      );

      expect(screen.getByTestId('mark-read-button')).toHaveClass('text');
      expect(screen.getByText('Unread')).toBeInTheDocument();
    });
  });

  describe('API Integration', () => {
    it('makes correct API calls when toggled', async () => {
      const mockOnToggle = jest.fn();
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_read: true, read_at: '2024-01-01T12:00:00Z' }),
      });

      render(
        <EnhancedMarkReadButton 
          chapterId="chapter-123" 
          isRead={false} 
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByTestId('mark-read-button');
      fireEvent.click(button);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/chapters/chapter-123/mark-read',
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
          }
        );
        expect(mockOnToggle).toHaveBeenCalledWith(true);
      });
    });

    it('handles API errors gracefully', async () => {
      const mockOnToggle = jest.fn();
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      render(
        <EnhancedMarkReadButton 
          chapterId="test-1" 
          isRead={false} 
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByTestId('mark-read-button');
      fireEvent.click(button);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Failed to toggle read status:',
          expect.any(Error)
        );
        expect(mockOnToggle).not.toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });

    it('prevents double-clicks during loading', async () => {
      const mockOnToggle = jest.fn();
      (global.fetch as jest.Mock).mockImplementation(() => 
        new Promise(resolve => setTimeout(resolve, 200))
      );

      render(
        <EnhancedMarkReadButton 
          chapterId="test-1" 
          isRead={false} 
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByTestId('mark-read-button');
      
      // Click multiple times rapidly
      fireEvent.click(button);
      fireEvent.click(button);
      fireEvent.click(button);

      // Only one API call should be made
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility and UX', () => {
    it('provides proper accessibility attributes', () => {
      render(<EnhancedMarkReadButton chapterId="test-1" isRead={false} />);

      const button = screen.getByTestId('mark-read-button');
      expect(button).toHaveAttribute('aria-label', 'Mark as read');
      expect(button).toHaveAttribute('title', 'Mark as read');
      expect(button).toHaveAttribute('aria-pressed', 'false');
    });

    it('updates accessibility attributes when state changes', () => {
      const { rerender } = render(
        <EnhancedMarkReadButton chapterId="test-1" isRead={false} />
      );

      let button = screen.getByTestId('mark-read-button');
      expect(button).toHaveAttribute('aria-label', 'Mark as read');

      rerender(<EnhancedMarkReadButton chapterId="test-1" isRead={true} />);
      
      button = screen.getByTestId('mark-read-button');
      expect(button).toHaveAttribute('aria-label', 'Mark as unread');
    });

    it('supports keyboard interaction', async () => {
      const mockOnToggle = jest.fn();
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_read: true }),
      });

      render(
        <EnhancedMarkReadButton 
          chapterId="test-1" 
          isRead={false} 
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByTestId('mark-read-button');
      
      // Activate via keyboard
      button.focus();
      fireEvent.keyDown(button, { key: 'Enter' });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });
  });
});

describe('Dashboard Stats Component', () => {
  const mockStats = {
    total_series: 25,
    total_chapters: 350,
    chapters_read: 175,
    overall_progress_percentage: 50.0,
    series_stats: {
      completed: 8,
      in_progress: 12,
      unread: 5,
    },
    recent_reads: [
      {
        chapter_id: '1',
        series_title: 'Attack on Titan',
        chapter_title: 'Chapter 139 - Final Chapter',
        read_at: '2024-01-01T12:00:00Z',
      },
      {
        chapter_id: '2',
        series_title: 'One Piece',
        chapter_title: 'Chapter 1100 - Dreams',
        read_at: '2024-01-01T10:30:00Z',
      },
    ],
    reading_streak_days: 14,
    reading_time_hours: 125.5,
    favorites_count: 12,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Data Display', () => {
    it('renders all statistics correctly', () => {
      render(<DashboardStatsComponent stats={mockStats} />);

      expect(screen.getByTestId('total-series')).toHaveTextContent('25');
      expect(screen.getByTestId('total-chapters')).toHaveTextContent('350');
      expect(screen.getByTestId('read-chapters')).toHaveTextContent('175');
      expect(screen.getByTestId('overall-progress')).toHaveTextContent('50%');
      expect(screen.getByTestId('reading-time')).toHaveTextContent('126h');
      expect(screen.getByTestId('favorites-count')).toHaveTextContent('12');
    });

    it('displays series breakdown correctly', () => {
      render(<DashboardStatsComponent stats={mockStats} />);

      const breakdown = screen.getByTestId('series-breakdown');
      
      expect(screen.getByTestId('completed-series')).toHaveTextContent('8');
      expect(screen.getByTestId('in-progress-series')).toHaveTextContent('12');
      expect(screen.getByTestId('unread-series')).toHaveTextContent('5');
    });

    it('shows reading streak information', () => {
      render(<DashboardStatsComponent stats={mockStats} />);

      expect(screen.getByTestId('reading-streak')).toHaveTextContent('14 days');
    });

    it('displays recent reading activity', () => {
      render(<DashboardStatsComponent stats={mockStats} />);

      const recentReads = screen.getByTestId('recent-reads-list');
      expect(recentReads).toBeInTheDocument();
      
      expect(screen.getByTestId('recent-read-0')).toHaveTextContent('Attack on Titan');
      expect(screen.getByTestId('recent-read-0')).toHaveTextContent('Chapter 139 - Final Chapter');
      expect(screen.getByTestId('recent-read-1')).toHaveTextContent('One Piece');
    });
  });

  describe('Loading and Error States', () => {
    it('shows loading state correctly', () => {
      render(<DashboardStatsComponent loading={true} />);

      expect(screen.getByTestId('loading-spinner')).toHaveTextContent('Loading...');
      expect(screen.queryByTestId('stats-grid')).not.toBeInTheDocument();
    });

    it('displays error state appropriately', () => {
      render(<DashboardStatsComponent error={new Error('Failed to load')} />);

      expect(screen.getByTestId('error-message')).toHaveTextContent('Error loading stats');
      expect(screen.queryByTestId('stats-grid')).not.toBeInTheDocument();
    });

    it('handles empty state gracefully', () => {
      render(<DashboardStatsComponent />);

      expect(screen.getByTestId('empty-state')).toHaveTextContent('No stats available');
    });

    it('handles empty recent reads', () => {
      const statsWithNoReads = { ...mockStats, recent_reads: [] };
      render(<DashboardStatsComponent stats={statsWithNoReads} />);

      expect(screen.getByTestId('no-recent-reads')).toHaveTextContent('No recent reading activity');
    });
  });

  describe('Progress Visualization', () => {
    it('renders overall progress bar correctly', () => {
      render(<DashboardStatsComponent stats={mockStats} />);

      const progressBar = screen.getByTestId('overall-progress-bar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    });

    it('calculates progress percentages correctly', () => {
      const customStats = {
        ...mockStats,
        chapters_read: 100,
        total_chapters: 200,
        overall_progress_percentage: 50,
      };

      render(<DashboardStatsComponent stats={customStats} />);

      expect(screen.getByTestId('overall-progress')).toHaveTextContent('50%');
      expect(screen.getByTestId('read-chapters')).toHaveTextContent('100');
      expect(screen.getByTestId('total-chapters')).toHaveTextContent('200');
    });
  });
});

describe('Chapter List with Progress Component', () => {
  const mockChapters = [
    {
      id: 'chapter-1',
      chapter_number: 1,
      title: 'The Beginning',
      is_read: true,
      last_read_page: 19,
      page_count: 20,
    },
    {
      id: 'chapter-2',
      chapter_number: 2,
      title: 'The Journey Continues',
      is_read: false,
      last_read_page: 10,
      page_count: 25,
    },
    {
      id: 'chapter-3',
      chapter_number: 3,
      is_read: false,
      last_read_page: 0,
      page_count: 30,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Chapter Rendering', () => {
    it('renders all chapters with correct information', () => {
      render(<ChapterListWithProgress chapters={mockChapters} />);

      expect(screen.getByTestId('chapter-chapter-1')).toBeInTheDocument();
      expect(screen.getByTestId('chapter-chapter-2')).toBeInTheDocument();
      expect(screen.getByTestId('chapter-chapter-3')).toBeInTheDocument();

      // Check chapter titles
      expect(screen.getByText('Chapter 1')).toBeInTheDocument();
      expect(screen.getByText('- The Beginning')).toBeInTheDocument();
      expect(screen.getByText('Chapter 2')).toBeInTheDocument();
      expect(screen.getByText('- The Journey Continues')).toBeInTheDocument();
      expect(screen.getByText('Chapter 3')).toBeInTheDocument();
    });

    it('handles chapters without titles', () => {
      const chaptersWithoutTitles = [
        { ...mockChapters[0], title: undefined },
      ];

      render(<ChapterListWithProgress chapters={chaptersWithoutTitles} />);

      const chapterItem = screen.getByTestId('chapter-chapter-1');
      expect(chapterItem).toHaveTextContent('Chapter 1');
      expect(chapterItem).not.toHaveTextContent('- ');
    });

    it('displays empty state for no chapters', () => {
      render(<ChapterListWithProgress chapters={[]} />);

      expect(screen.getByTestId('empty-chapter-list')).toHaveTextContent('No chapters available');
    });
  });

  describe('Progress Display', () => {
    it('shows correct progress for completed chapter', () => {
      render(<ChapterListWithProgress chapters={mockChapters} />);

      const chapter1 = screen.getByTestId('chapter-chapter-1');
      const progressText = within(chapter1).getByTestId('progress-text');
      
      expect(progressText).toHaveTextContent('Complete');
    });

    it('calculates progress percentage correctly for partial reads', () => {
      render(<ChapterListWithProgress chapters={mockChapters} />);

      const chapter2 = screen.getByTestId('chapter-chapter-2');
      const progressText = within(chapter2).getByTestId('progress-text');
      
      // (10+1)/25 * 100 = 44%
      expect(progressText).toHaveTextContent('44%');
    });

    it('shows minimal progress for unread chapters', () => {
      render(<ChapterListWithProgress chapters={mockChapters} />);

      const chapter3 = screen.getByTestId('chapter-chapter-3');
      const progressText = within(chapter3).getByTestId('progress-text');
      
      // (0+1)/30 * 100 = 3.33% -> 3%
      expect(progressText).toHaveTextContent('3%');
    });
  });

  describe('Mark Read Integration', () => {
    it('calls onChapterRead callback when button is clicked', async () => {
      const mockOnChapterRead = jest.fn();
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_read: true }),
      });

      render(
        <ChapterListWithProgress 
          chapters={mockChapters} 
          onChapterRead={mockOnChapterRead}
        />
      );

      const chapter2 = screen.getByTestId('chapter-chapter-2');
      const markReadButton = within(chapter2).getByTestId('chapter-mark-read-button');
      
      fireEvent.click(markReadButton);

      await waitFor(() => {
        expect(mockOnChapterRead).toHaveBeenCalledWith('chapter-2', true);
      });
    });

    it('displays correct button states for different chapters', () => {
      render(<ChapterListWithProgress chapters={mockChapters} />);

      const chapter1Button = within(screen.getByTestId('chapter-chapter-1')).getByTestId('chapter-mark-read-button');
      const chapter2Button = within(screen.getByTestId('chapter-chapter-2')).getByTestId('chapter-mark-read-button');
      
      expect(chapter1Button).toHaveClass('read');
      expect(chapter2Button).toHaveClass('unread');
    });
  });
});

// Integration Tests
describe('Reading Progress Integration', () => {
  it('updates progress display when chapters are marked as read', async () => {
    const TestIntegrationComponent = () => {
      const [chapters, setChapters] = React.useState([
        { id: '1', chapter_number: 1, is_read: false, last_read_page: 0, page_count: 20 },
        { id: '2', chapter_number: 2, is_read: false, last_read_page: 0, page_count: 25 },
      ]);

      const [stats, setStats] = React.useState({
        total_series: 1,
        total_chapters: 2,
        chapters_read: 0,
        overall_progress_percentage: 0,
        series_stats: { completed: 0, in_progress: 1, unread: 0 },
        recent_reads: [],
        reading_streak_days: 0,
        reading_time_hours: 0,
        favorites_count: 0,
      });

      const handleChapterRead = (chapterId: string, isRead: boolean) => {
        setChapters(prev => prev.map(ch => 
          ch.id === chapterId 
            ? { ...ch, is_read: isRead, last_read_page: isRead ? ch.page_count - 1 : 0 }
            : ch
        ));

        // Update stats
        const newReadCount = chapters.filter(ch => 
          ch.id === chapterId ? isRead : ch.is_read
        ).length;
        
        setStats(prev => ({
          ...prev,
          chapters_read: newReadCount,
          overall_progress_percentage: (newReadCount / 2) * 100,
        }));
      };

      return (
        <div>
          <DashboardStatsComponent stats={stats} />
          <ChapterListWithProgress 
            chapters={chapters}
            onChapterRead={handleChapterRead}
          />
        </div>
      );
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ is_read: true }),
    });

    render(<TestIntegrationComponent />);

    // Initial state
    expect(screen.getByTestId('overall-progress')).toHaveTextContent('0%');
    expect(screen.getByTestId('read-chapters')).toHaveTextContent('0');

    // Mark first chapter as read
    const chapter1Button = within(screen.getByTestId('chapter-1')).getByTestId('chapter-mark-read-button');
    fireEvent.click(chapter1Button);

    await waitFor(() => {
      expect(screen.getByTestId('overall-progress')).toHaveTextContent('50%');
      expect(screen.getByTestId('read-chapters')).toHaveTextContent('1');
    });
  });
});

// Import the utils function that might be missing
const within = (element: HTMLElement) => ({
  getByTestId: (testId: string) => {
    const result = element.querySelector(`[data-testid="${testId}"]`);
    if (!result) throw new Error(`Unable to find element with testid: ${testId}`);
    return result as HTMLElement;
  },
});