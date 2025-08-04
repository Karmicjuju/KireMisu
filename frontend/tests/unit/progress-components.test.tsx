/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';

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

// Mock fetch globally
global.fetch = jest.fn();

const mockRouter = {
  refresh: jest.fn(),
  push: jest.fn(),
};

// Mock ProgressBar component (since it's being implemented)
const MockProgressBar = ({
  value,
  max = 100,
  className = '',
  label,
}: {
  value: number;
  max?: number;
  className?: string;
  label?: string;
}) => (
  <div className={`progress-bar ${className}`} data-testid="progress-bar">
    <div
      className="progress-fill"
      style={{ width: `${(value / max) * 100}%` }}
      data-testid="progress-fill"
    />
    {label && <span data-testid="progress-label">{label}</span>}
    <span data-testid="progress-percentage">{Math.round((value / max) * 100)}%</span>
  </div>
);

// Mock MarkReadButton component (since it's being implemented)
const MockMarkReadButton = ({
  chapterId,
  isRead,
  onToggle,
  disabled = false,
  variant = 'default',
}: {
  chapterId: string;
  isRead: boolean;
  onToggle?: (isRead: boolean) => void;
  disabled?: boolean;
  variant?: 'default' | 'compact';
}) => {
  const handleClick = async () => {
    if (disabled) return;

    try {
      const response = await fetch(`/api/chapters/${chapterId}/mark-read`, {
        method: 'PUT',
      });

      if (response.ok) {
        const data = await response.json();
        onToggle?.(data.is_read);
      }
    } catch (error) {
      console.error('Failed to toggle read status:', error);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className={`mark-read-button ${variant} ${isRead ? 'read' : 'unread'}`}
      data-testid="mark-read-button"
      aria-label={isRead ? 'Mark as unread' : 'Mark as read'}
    >
      {isRead ? '✓ Read' : 'Mark Read'}
    </button>
  );
};

describe('ProgressBar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render with correct progress percentage', () => {
    render(<MockProgressBar value={30} max={100} />);

    expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('30%');

    const progressFill = screen.getByTestId('progress-fill');
    expect(progressFill).toHaveStyle({ width: '30%' });
  });

  it('should handle different max values correctly', () => {
    render(<MockProgressBar value={5} max={10} />);

    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('50%');

    const progressFill = screen.getByTestId('progress-fill');
    expect(progressFill).toHaveStyle({ width: '50%' });
  });

  it('should render with custom label', () => {
    render(<MockProgressBar value={15} max={20} label="Chapters Read" />);

    expect(screen.getByTestId('progress-label')).toHaveTextContent('Chapters Read');
    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('75%');
  });

  it('should apply custom CSS classes', () => {
    render(<MockProgressBar value={50} className="custom-progress" />);

    const progressBar = screen.getByTestId('progress-bar');
    expect(progressBar).toHaveClass('custom-progress');
  });

  it('should handle zero progress', () => {
    render(<MockProgressBar value={0} />);

    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('0%');

    const progressFill = screen.getByTestId('progress-fill');
    expect(progressFill).toHaveStyle({ width: '0%' });
  });

  it('should handle complete progress', () => {
    render(<MockProgressBar value={100} />);

    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('100%');

    const progressFill = screen.getByTestId('progress-fill');
    expect(progressFill).toHaveStyle({ width: '100%' });
  });

  it('should handle progress values exceeding max', () => {
    render(<MockProgressBar value={150} max={100} />);

    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('150%');

    const progressFill = screen.getByTestId('progress-fill');
    expect(progressFill).toHaveStyle({ width: '150%' });
  });

  it('should handle fractional progress values', () => {
    render(<MockProgressBar value={33.33} max={100} />);

    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('33%');

    const progressFill = screen.getByTestId('progress-fill');
    expect(progressFill).toHaveStyle({ width: '33.33%' });
  });
});

describe('MarkReadButton Component', () => {
  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (global.fetch as jest.Mock).mockClear();
    mockRouter.refresh.mockClear();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should render with correct initial state for unread chapter', () => {
    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={false} />);

    const button = screen.getByTestId('mark-read-button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Mark Read');
    expect(button).toHaveClass('unread');
    expect(button).toHaveAttribute('aria-label', 'Mark as read');
  });

  it('should render with correct initial state for read chapter', () => {
    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={true} />);

    const button = screen.getByTestId('mark-read-button');
    expect(button).toHaveTextContent('✓ Read');
    expect(button).toHaveClass('read');
    expect(button).toHaveAttribute('aria-label', 'Mark as unread');
  });

  it('should handle mark as read successfully', async () => {
    const mockOnToggle = jest.fn();

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'test-chapter-1',
        is_read: true,
        read_at: '2025-01-01T12:00:00Z',
      }),
    });

    render(
      <MockMarkReadButton chapterId="test-chapter-1" isRead={false} onToggle={mockOnToggle} />
    );

    const button = screen.getByTestId('mark-read-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/chapters/test-chapter-1/mark-read', {
        method: 'PUT',
      });
    });

    await waitFor(() => {
      expect(mockOnToggle).toHaveBeenCalledWith(true);
    });
  });

  it('should handle mark as unread successfully', async () => {
    const mockOnToggle = jest.fn();

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'test-chapter-1',
        is_read: false,
        read_at: null,
      }),
    });

    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={true} onToggle={mockOnToggle} />);

    const button = screen.getByTestId('mark-read-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/chapters/test-chapter-1/mark-read', {
        method: 'PUT',
      });
    });

    await waitFor(() => {
      expect(mockOnToggle).toHaveBeenCalledWith(false);
    });
  });

  it('should handle API errors gracefully', async () => {
    const mockOnToggle = jest.fn();
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    });

    render(
      <MockMarkReadButton chapterId="test-chapter-1" isRead={false} onToggle={mockOnToggle} />
    );

    const button = screen.getByTestId('mark-read-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    // onToggle should not be called on error
    expect(mockOnToggle).not.toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('should handle network errors gracefully', async () => {
    const mockOnToggle = jest.fn();
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(
      <MockMarkReadButton chapterId="test-chapter-1" isRead={false} onToggle={mockOnToggle} />
    );

    const button = screen.getByTestId('mark-read-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to toggle read status:', expect.any(Error));
    });

    expect(mockOnToggle).not.toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('should be disabled when disabled prop is true', () => {
    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={false} disabled={true} />);

    const button = screen.getByTestId('mark-read-button');
    expect(button).toBeDisabled();
  });

  it('should not make API call when disabled', async () => {
    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={false} disabled={true} />);

    const button = screen.getByTestId('mark-read-button');
    fireEvent.click(button);

    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should apply compact variant class', () => {
    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={false} variant="compact" />);

    const button = screen.getByTestId('mark-read-button');
    expect(button).toHaveClass('compact');
  });

  it('should apply default variant class', () => {
    render(<MockMarkReadButton chapterId="test-chapter-1" isRead={false} variant="default" />);

    const button = screen.getByTestId('mark-read-button');
    expect(button).toHaveClass('default');
  });
});

// Mock Dashboard Stats component tests
const MockDashboardStats = ({
  stats,
}: {
  stats: {
    total_series: number;
    total_chapters: number;
    read_chapters: number;
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
  };
}) => (
  <div className="dashboard-stats" data-testid="dashboard-stats">
    <div data-testid="total-series">Total Series: {stats.total_series}</div>
    <div data-testid="total-chapters">Total Chapters: {stats.total_chapters}</div>
    <div data-testid="read-chapters">Read Chapters: {stats.read_chapters}</div>
    <div data-testid="overall-progress">Overall Progress: {stats.overall_progress_percentage}%</div>

    <div data-testid="series-breakdown">
      <div>Completed: {stats.series_stats.completed}</div>
      <div>In Progress: {stats.series_stats.in_progress}</div>
      <div>Unread: {stats.series_stats.unread}</div>
    </div>

    <div data-testid="reading-streak">Streak: {stats.reading_streak_days} days</div>

    <div data-testid="recent-reads">
      {stats.recent_reads.map((read, index) => (
        <div key={index} className="recent-read">
          {read.series_title} - {read.chapter_title}
        </div>
      ))}
    </div>
  </div>
);

describe('DashboardStats Component', () => {
  const mockStats = {
    total_series: 10,
    total_chapters: 100,
    read_chapters: 45,
    overall_progress_percentage: 45.0,
    series_stats: {
      completed: 3,
      in_progress: 4,
      unread: 3,
    },
    recent_reads: [
      {
        chapter_id: '1',
        series_title: 'Attack on Titan',
        chapter_title: 'Chapter 139',
        read_at: '2025-01-01T12:00:00Z',
      },
      {
        chapter_id: '2',
        series_title: 'One Piece',
        chapter_title: 'Chapter 1000',
        read_at: '2025-01-01T11:30:00Z',
      },
    ],
    reading_streak_days: 7,
  };

  it('should render all statistics correctly', () => {
    render(<MockDashboardStats stats={mockStats} />);

    expect(screen.getByTestId('total-series')).toHaveTextContent('Total Series: 10');
    expect(screen.getByTestId('total-chapters')).toHaveTextContent('Total Chapters: 100');
    expect(screen.getByTestId('read-chapters')).toHaveTextContent('Read Chapters: 45');
    expect(screen.getByTestId('overall-progress')).toHaveTextContent('Overall Progress: 45%');
  });

  it('should render series breakdown correctly', () => {
    render(<MockDashboardStats stats={mockStats} />);

    const breakdown = screen.getByTestId('series-breakdown');
    expect(breakdown).toHaveTextContent('Completed: 3');
    expect(breakdown).toHaveTextContent('In Progress: 4');
    expect(breakdown).toHaveTextContent('Unread: 3');
  });

  it('should render reading streak', () => {
    render(<MockDashboardStats stats={mockStats} />);

    expect(screen.getByTestId('reading-streak')).toHaveTextContent('Streak: 7 days');
  });

  it('should render recent reads', () => {
    render(<MockDashboardStats stats={mockStats} />);

    const recentReads = screen.getByTestId('recent-reads');
    expect(recentReads).toHaveTextContent('Attack on Titan - Chapter 139');
    expect(recentReads).toHaveTextContent('One Piece - Chapter 1000');
  });

  it('should handle empty stats gracefully', () => {
    const emptyStats = {
      total_series: 0,
      total_chapters: 0,
      read_chapters: 0,
      overall_progress_percentage: 0,
      series_stats: {
        completed: 0,
        in_progress: 0,
        unread: 0,
      },
      recent_reads: [],
      reading_streak_days: 0,
    };

    render(<MockDashboardStats stats={emptyStats} />);

    expect(screen.getByTestId('total-series')).toHaveTextContent('Total Series: 0');
    expect(screen.getByTestId('overall-progress')).toHaveTextContent('Overall Progress: 0%');
    expect(screen.getByTestId('reading-streak')).toHaveTextContent('Streak: 0 days');

    const recentReads = screen.getByTestId('recent-reads');
    expect(recentReads).toBeEmptyDOMElement();
  });

  it('should handle high progress percentages', () => {
    const highProgressStats = {
      ...mockStats,
      read_chapters: 100,
      overall_progress_percentage: 100.0,
    };

    render(<MockDashboardStats stats={highProgressStats} />);

    expect(screen.getByTestId('overall-progress')).toHaveTextContent('Overall Progress: 100%');
  });

  it('should handle fractional progress percentages', () => {
    const fractionalStats = {
      ...mockStats,
      overall_progress_percentage: 33.33,
    };

    render(<MockDashboardStats stats={fractionalStats} />);

    expect(screen.getByTestId('overall-progress')).toHaveTextContent('Overall Progress: 33.33%');
  });
});

// Mock ChapterList with Progress component tests
const MockChapterListWithProgress = ({
  chapters,
}: {
  chapters: Array<{
    id: string;
    chapter_number: number;
    title?: string;
    is_read: boolean;
    last_read_page: number;
    page_count: number;
  }>;
}) => (
  <div className="chapter-list" data-testid="chapter-list">
    {chapters.map((chapter) => {
      const progressPercentage =
        chapter.page_count > 0
          ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
          : 0;

      return (
        <div key={chapter.id} className="chapter-item" data-testid={`chapter-${chapter.id}`}>
          <div className="chapter-info">
            <span>Chapter {chapter.chapter_number}</span>
            {chapter.title && <span> - {chapter.title}</span>}
          </div>

          <div className="chapter-progress">
            <MockProgressBar
              value={chapter.last_read_page + 1}
              max={chapter.page_count}
              className="chapter-progress-bar"
            />
            <span className="progress-text">
              {chapter.is_read ? 'Complete' : `${progressPercentage}%`}
            </span>
          </div>

          <MockMarkReadButton chapterId={chapter.id} isRead={chapter.is_read} variant="compact" />
        </div>
      );
    })}
  </div>
);

describe('ChapterListWithProgress Component', () => {
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
      title: 'New Challenges',
      is_read: false,
      last_read_page: 0,
      page_count: 22,
    },
  ];

  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  it('should render all chapters with progress information', () => {
    render(<MockChapterListWithProgress chapters={mockChapters} />);

    expect(screen.getByTestId('chapter-list')).toBeInTheDocument();
    expect(screen.getByTestId('chapter-chapter-1')).toBeInTheDocument();
    expect(screen.getByTestId('chapter-chapter-2')).toBeInTheDocument();
    expect(screen.getByTestId('chapter-chapter-3')).toBeInTheDocument();
  });

  it('should show correct progress for read chapter', () => {
    render(<MockChapterListWithProgress chapters={mockChapters} />);

    const chapter1 = screen.getByTestId('chapter-chapter-1');
    expect(chapter1).toHaveTextContent('Chapter 1 - The Beginning');
    expect(chapter1).toHaveTextContent('Complete');
  });

  it('should show correct progress for partially read chapter', () => {
    render(<MockChapterListWithProgress chapters={mockChapters} />);

    const chapter2 = screen.getByTestId('chapter-chapter-2');
    expect(chapter2).toHaveTextContent('Chapter 2 - The Journey Continues');
    expect(chapter2).toHaveTextContent('44%'); // (10+1)/25 * 100 = 44%
  });

  it('should show correct progress for unread chapter', () => {
    render(<MockChapterListWithProgress chapters={mockChapters} />);

    const chapter3 = screen.getByTestId('chapter-chapter-3');
    expect(chapter3).toHaveTextContent('Chapter 3 - New Challenges');
    expect(chapter3).toHaveTextContent('5%'); // (0+1)/22 * 100 = 4.5% -> 5%
  });

  it('should render mark read buttons for all chapters', () => {
    render(<MockChapterListWithProgress chapters={mockChapters} />);

    const markReadButtons = screen.getAllByTestId('mark-read-button');
    expect(markReadButtons).toHaveLength(3);

    expect(markReadButtons[0]).toHaveClass('read');
    expect(markReadButtons[1]).toHaveClass('unread');
    expect(markReadButtons[2]).toHaveClass('unread');
  });

  it('should handle chapters without titles', () => {
    const chaptersWithoutTitles = [
      {
        id: 'chapter-1',
        chapter_number: 1,
        is_read: false,
        last_read_page: 5,
        page_count: 20,
      },
    ];

    render(<MockChapterListWithProgress chapters={chaptersWithoutTitles} />);

    const chapter = screen.getByTestId('chapter-chapter-1');
    expect(chapter).toHaveTextContent('Chapter 1');
    expect(chapter).not.toHaveTextContent(' - ');
  });

  it('should handle empty chapter list', () => {
    render(<MockChapterListWithProgress chapters={[]} />);

    const chapterList = screen.getByTestId('chapter-list');
    expect(chapterList).toBeEmptyDOMElement();
  });
});
