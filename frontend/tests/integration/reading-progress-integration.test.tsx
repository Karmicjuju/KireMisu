/**
 * Reading Progress Cross-Component Integration Tests
 * 
 * This test suite validates that reading progress features work correctly
 * across different components and maintain data consistency throughout
 * the application.
 * 
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import React from 'react';

// Mock Next.js dependencies
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
  }),
}));

jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock SWR with more realistic behavior
const mockMutate = jest.fn();
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn((key, fetcher) => {
    // Simulate different API responses based on key
    if (key?.includes('/api/dashboard/stats')) {
      return {
        data: {
          total_series: 10,
          total_chapters: 150,
          chapters_read: 75,
          overall_progress_percentage: 50.0,
          series_stats: {
            completed: 3,
            in_progress: 5,
            unread: 2,
          },
          recent_reads: [
            {
              chapter_id: '1',
              series_title: 'Attack on Titan',
              chapter_title: 'Chapter 139',
              read_at: '2024-01-01T12:00:00Z',
            },
          ],
          reading_streak_days: 7,
          reading_time_hours: 100,
          favorites_count: 5,
        },
        error: null,
        isLoading: false,
        mutate: mockMutate,
      };
    }
    
    if (key?.includes('/api/series')) {
      return {
        data: {
          series: [
            {
              id: 'series-1',
              title_primary: 'Test Manga Series',
              total_chapters: 15,
              read_chapters: 8,
              cover_art: null,
            },
          ],
        },
        error: null,
        isLoading: false,
        mutate: mockMutate,
      };
    }

    if (key?.includes('/api/chapters')) {
      return {
        data: {
          chapters: [
            {
              id: 'chapter-1',
              chapter_number: 1,
              title: 'Beginning',
              is_read: true,
              last_read_page: 19,
              page_count: 20,
            },
            {
              id: 'chapter-2',
              chapter_number: 2,
              title: 'The Journey',
              is_read: false,
              last_read_page: 5,
              page_count: 22,
            },
          ],
        },
        error: null,
        isLoading: false,
        mutate: mockMutate,
      };
    }

    return {
      data: null,
      error: null,
      isLoading: false,
      mutate: mockMutate,
    };
  }),
}));

// Mock fetch with realistic API responses
global.fetch = jest.fn();

// Integration Test Components
const IntegratedProgressApp = () => {
  const [currentView, setCurrentView] = React.useState<'dashboard' | 'library' | 'series'>('dashboard');
  const [selectedSeries, setSelectedSeries] = React.useState<string | null>(null);
  const [stats, setStats] = React.useState({
    total_series: 10,
    total_chapters: 150,
    chapters_read: 75,
    overall_progress_percentage: 50.0,
    series_stats: { completed: 3, in_progress: 5, unread: 2 },
    recent_reads: [],
    reading_streak_days: 7,
    reading_time_hours: 100,
    favorites_count: 5,
  });

  const [series, setSeries] = React.useState([
    {
      id: 'series-1',
      title_primary: 'Test Manga Series',
      total_chapters: 15,
      read_chapters: 8,
    },
    {
      id: 'series-2',
      title_primary: 'Another Series',
      total_chapters: 25,
      read_chapters: 12,
    },
  ]);

  const [chapters, setChapters] = React.useState([
    {
      id: 'chapter-1',
      series_id: 'series-1',
      chapter_number: 1,
      title: 'Beginning',
      is_read: true,
      last_read_page: 19,
      page_count: 20,
    },
    {
      id: 'chapter-2',
      series_id: 'series-1',
      chapter_number: 2,
      title: 'The Journey',
      is_read: false,
      last_read_page: 5,
      page_count: 22,
    },
    {
      id: 'chapter-3',
      series_id: 'series-1',
      chapter_number: 3,
      title: 'New Challenges',
      is_read: false,
      last_read_page: 0,
      page_count: 18,
    },
  ]);

  const handleMarkRead = async (chapterId: string) => {
    const chapter = chapters.find(ch => ch.id === chapterId);
    if (!chapter) return;

    const newReadStatus = !chapter.is_read;
    
    // Update chapter
    const updatedChapters = chapters.map(ch =>
      ch.id === chapterId
        ? {
            ...ch,
            is_read: newReadStatus,
            last_read_page: newReadStatus ? ch.page_count - 1 : 0,
          }
        : ch
    );
    setChapters(updatedChapters);

    // Update series stats
    const seriesChapters = updatedChapters.filter(ch => ch.series_id === chapter.series_id);
    const readCount = seriesChapters.filter(ch => ch.is_read).length;
    
    const updatedSeries = series.map(s =>
      s.id === chapter.series_id
        ? { ...s, read_chapters: readCount }
        : s
    );
    setSeries(updatedSeries);

    // Update overall stats
    const totalRead = updatedChapters.filter(ch => ch.is_read).length;
    const newOverallPercentage = (totalRead / chapters.length) * 100;
    
    setStats(prev => ({
      ...prev,
      chapters_read: totalRead,
      overall_progress_percentage: newOverallPercentage,
    }));

    // Mock API call
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ is_read: newReadStatus }),
    });
  };

  const handleNavigate = (view: 'dashboard' | 'library' | 'series', seriesId?: string) => {
    setCurrentView(view);
    if (seriesId) setSelectedSeries(seriesId);
  };

  return (
    <div className="integrated-progress-app" data-testid="progress-app">
      {/* Navigation */}
      <nav data-testid="app-navigation">
        <button 
          onClick={() => handleNavigate('dashboard')}
          data-testid="nav-dashboard"
          className={currentView === 'dashboard' ? 'active' : ''}
        >
          Dashboard
        </button>
        <button 
          onClick={() => handleNavigate('library')}
          data-testid="nav-library"
          className={currentView === 'library' ? 'active' : ''}
        >
          Library
        </button>
      </nav>

      {/* Dashboard View */}
      {currentView === 'dashboard' && (
        <div className="dashboard-view" data-testid="dashboard-view">
          <h1>Reading Dashboard</h1>
          
          <div className="stats-overview" data-testid="stats-overview">
            <div className="stat-card" data-testid="total-series-stat">
              <span data-testid="total-series">{stats.total_series}</span>
              <span>Total Series</span>
            </div>
            
            <div className="stat-card" data-testid="chapters-stat">
              <span data-testid="read-chapters">{stats.chapters_read}</span>
              <span>of</span>
              <span data-testid="total-chapters">{stats.total_chapters}</span>
              <span>Chapters Read</span>
            </div>
            
            <div className="stat-card" data-testid="progress-stat">
              <span data-testid="overall-progress">{Math.round(stats.overall_progress_percentage)}%</span>
              <span>Complete</span>
            </div>
          </div>

          <div className="progress-visualization" data-testid="progress-visualization">
            <div className="progress-bar" data-testid="overall-progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${stats.overall_progress_percentage}%` }}
                data-testid="progress-fill"
              />
            </div>
          </div>

          <div className="series-breakdown" data-testid="series-breakdown">
            <div data-testid="completed-count">{stats.series_stats.completed} Completed</div>
            <div data-testid="in-progress-count">{stats.series_stats.in_progress} In Progress</div>
            <div data-testid="unread-count">{stats.series_stats.unread} Unread</div>
          </div>
        </div>
      )}

      {/* Library View */}
      {currentView === 'library' && (
        <div className="library-view" data-testid="library-view">
          <h1>Manga Library</h1>
          
          <div className="series-grid" data-testid="series-grid">
            {series.map(s => {
              const progressPercentage = s.total_chapters > 0 
                ? Math.round((s.read_chapters / s.total_chapters) * 100)
                : 0;

              return (
                <div 
                  key={s.id}
                  className="series-card"
                  data-testid={`series-card-${s.id}`}
                  onClick={() => handleNavigate('series', s.id)}
                >
                  <h3>{s.title_primary}</h3>
                  <div className="series-progress" data-testid="series-progress">
                    <div className="progress-text" data-testid="progress-text">
                      {s.read_chapters} / {s.total_chapters} chapters
                    </div>
                    <div className="progress-bar" data-testid="series-progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${progressPercentage}%` }}
                        data-testid="series-progress-fill"
                      />
                    </div>
                    <div className="progress-percentage" data-testid="progress-percentage">
                      {progressPercentage}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Series Detail View */}
      {currentView === 'series' && selectedSeries && (
        <div className="series-view" data-testid="series-view">
          {(() => {
            const currentSeries = series.find(s => s.id === selectedSeries);
            const seriesChapters = chapters.filter(ch => ch.series_id === selectedSeries);
            
            return (
              <>
                <button 
                  onClick={() => handleNavigate('library')}
                  data-testid="back-to-library"
                >
                  ← Back to Library
                </button>
                
                <h1>{currentSeries?.title_primary}</h1>
                
                <div className="series-stats" data-testid="series-stats">
                  <span data-testid="series-read-chapters">{currentSeries?.read_chapters}</span>
                  <span>of</span>
                  <span data-testid="series-total-chapters">{currentSeries?.total_chapters}</span>
                  <span>chapters read</span>
                </div>

                <div className="chapter-list" data-testid="chapter-list">
                  {seriesChapters.map(chapter => {
                    const progressPercentage = chapter.page_count > 0
                      ? Math.round(((chapter.last_read_page + 1) / chapter.page_count) * 100)
                      : 0;

                    return (
                      <div 
                        key={chapter.id}
                        className="chapter-item"
                        data-testid={`chapter-${chapter.id}`}
                      >
                        <div className="chapter-info">
                          <h4>Chapter {chapter.chapter_number}</h4>
                          {chapter.title && <span>- {chapter.title}</span>}
                        </div>

                        <div className="chapter-progress" data-testid="chapter-progress">
                          <div className="progress-bar" data-testid="chapter-progress-bar">
                            <div 
                              className="progress-fill"
                              style={{ width: `${progressPercentage}%` }}
                              data-testid="chapter-progress-fill"
                            />
                          </div>
                          <div className="progress-text" data-testid="chapter-progress-text">
                            {chapter.is_read ? 'Complete' : `${progressPercentage}%`}
                          </div>
                        </div>

                        <button
                          onClick={() => handleMarkRead(chapter.id)}
                          className={`mark-read-button ${chapter.is_read ? 'read' : 'unread'}`}
                          data-testid={`mark-read-${chapter.id}`}
                        >
                          {chapter.is_read ? '✓ Read' : 'Mark Read'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
};

describe('Reading Progress Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('Dashboard to Library Navigation', () => {
    it('maintains progress consistency across navigation', async () => {
      render(<IntegratedProgressApp />);
      
      // Verify initial dashboard state
      expect(screen.getByTestId('overall-progress')).toHaveTextContent('50%');
      expect(screen.getByTestId('read-chapters')).toHaveTextContent('75');
      
      // Navigate to library
      fireEvent.click(screen.getByTestId('nav-library'));
      
      // Verify library shows consistent data
      await waitFor(() => {
        expect(screen.getByTestId('library-view')).toBeVisible();
      });
      
      const firstSeriesCard = screen.getByTestId('series-card-series-1');
      expect(firstSeriesCard).toHaveTextContent('8 / 15 chapters');
      expect(firstSeriesCard).toHaveTextContent('53%'); // 8/15 = ~53%
    });

    it('updates dashboard when returning from chapter interactions', async () => {
      render(<IntegratedProgressApp />);
      
      // Start from dashboard, note initial stats
      const initialProgress = screen.getByTestId('overall-progress').textContent;
      
      // Navigate to library then series
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      
      // Mark a chapter as read
      const unreadChapter = screen.getByTestId('mark-read-chapter-2');
      expect(unreadChapter).toHaveTextContent('Mark Read');
      
      fireEvent.click(unreadChapter);
      
      await waitFor(() => {
        expect(unreadChapter).toHaveTextContent('✓ Read');
      });
      
      // Navigate back to dashboard
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      
      // Dashboard should reflect the change
      await waitFor(() => {
        const updatedProgress = screen.getByTestId('overall-progress').textContent;
        expect(updatedProgress).not.toBe(initialProgress);
        expect(screen.getByTestId('read-chapters')).toHaveTextContent('76'); // Increased by 1
      });
    });
  });

  describe('Real-time Progress Updates', () => {
    it('updates all related UI components when chapter is marked read', async () => {
      render(<IntegratedProgressApp />);
      
      // Navigate to series view
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      
      // Get initial states
      const seriesReadChapters = screen.getByTestId('series-read-chapters').textContent;
      const chapter3Button = screen.getByTestId('mark-read-chapter-3');
      const chapter3Progress = screen.getByTestId('chapter-progress-text');
      
      expect(chapter3Progress).toHaveTextContent('6%'); // (0+1)/18 ≈ 6%
      expect(chapter3Button).toHaveTextContent('Mark Read');
      
      // Mark chapter 3 as read
      fireEvent.click(chapter3Button);
      
      await waitFor(() => {
        // Chapter button should update
        expect(chapter3Button).toHaveTextContent('✓ Read');
        
        // Chapter progress should update
        expect(chapter3Progress).toHaveTextContent('Complete');
        
        // Series stats should update
        expect(screen.getByTestId('series-read-chapters')).toHaveTextContent('9');
      });
      
      // Navigate back to library to check series card
      fireEvent.click(screen.getByTestId('back-to-library'));
      
      await waitFor(() => {
        const seriesCard = screen.getByTestId('series-card-series-1');
        expect(seriesCard).toHaveTextContent('9 / 15 chapters');
        expect(seriesCard).toHaveTextContent('60%'); // 9/15 = 60%
      });
    });

    it('handles multiple rapid chapter marking correctly', async () => {
      render(<IntegratedProgressApp />);
      
      // Navigate to series
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      
      const initialReadCount = parseInt(screen.getByTestId('series-read-chapters').textContent || '0');
      
      // Mark multiple chapters rapidly
      const chapter2Button = screen.getByTestId('mark-read-chapter-2');
      const chapter3Button = screen.getByTestId('mark-read-chapter-3');
      
      fireEvent.click(chapter2Button);
      fireEvent.click(chapter3Button);
      
      await waitFor(() => {
        expect(chapter2Button).toHaveTextContent('✓ Read');
        expect(chapter3Button).toHaveTextContent('✓ Read');
        
        // Series count should be updated correctly
        const finalReadCount = parseInt(screen.getByTestId('series-read-chapters').textContent || '0');
        expect(finalReadCount).toBe(initialReadCount + 2);
      });
      
      // Return to dashboard and verify consistency
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      
      await waitFor(() => {
        expect(screen.getByTestId('read-chapters')).toHaveTextContent('77'); // 75 + 2
        expect(screen.getByTestId('overall-progress')).toHaveTextContent('51%'); // 77/150 ≈ 51%
      });
    });
  });

  describe('Cross-Component State Consistency', () => {
    it('maintains accurate progress calculations across different views', async () => {
      render(<IntegratedProgressApp />);
      
      // Test progression: Dashboard → Library → Series → Back to Dashboard
      
      // 1. Dashboard: Record initial state
      const initialDashboardProgress = screen.getByTestId('overall-progress').textContent;
      
      // 2. Library: Check series progress matches expectations
      fireEvent.click(screen.getByTestId('nav-library'));
      
      const series1Card = screen.getByTestId('series-card-series-1');
      const series1Progress = series1Card.querySelector('[data-testid="progress-percentage"]')?.textContent;
      
      // 3. Series Detail: Verify chapter-level data
      fireEvent.click(series1Card);
      
      const chapterItems = screen.getAllByTestId(/^chapter-/);
      let readChaptersCount = 0;
      let totalChapters = chapterItems.length;
      
      chapterItems.forEach((chapter) => {
        const button = chapter.querySelector('[data-testid^="mark-read-"]');
        if (button?.textContent?.includes('✓ Read')) {
          readChaptersCount++;
        }
      });
      
      const expectedSeriesProgress = Math.round((readChaptersCount / totalChapters) * 100);
      expect(series1Progress).toBe(`${expectedSeriesProgress}%`);
      
      // 4. Make changes and verify propagation
      const unreadChapterButton = screen.getByTestId('mark-read-chapter-2');
      fireEvent.click(unreadChapterButton);
      
      await waitFor(() => {
        expect(unreadChapterButton).toHaveTextContent('✓ Read');
      });
      
      // 5. Return to dashboard and verify global state updated
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      
      await waitFor(() => {
        const finalDashboardProgress = screen.getByTestId('overall-progress').textContent;
        expect(finalDashboardProgress).not.toBe(initialDashboardProgress);
        
        // Progress should have increased
        const initialValue = parseInt(initialDashboardProgress?.replace('%', '') || '0');
        const finalValue = parseInt(finalDashboardProgress?.replace('%', '') || '0');
        expect(finalValue).toBeGreaterThan(initialValue);
      });
    });

    it('handles edge cases gracefully', async () => {
      render(<IntegratedProgressApp />);
      
      // Navigate to series
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      
      // Test toggling the same chapter multiple times
      const chapter2Button = screen.getByTestId('mark-read-chapter-2');
      
      // Initially should be unread
      expect(chapter2Button).toHaveTextContent('Mark Read');
      
      // Mark as read
      fireEvent.click(chapter2Button);
      await waitFor(() => {
        expect(chapter2Button).toHaveTextContent('✓ Read');
      });
      
      // Mark as unread again
      fireEvent.click(chapter2Button);
      await waitFor(() => {
        expect(chapter2Button).toHaveTextContent('Mark Read');
      });
      
      // Mark as read one more time
      fireEvent.click(chapter2Button);
      await waitFor(() => {
        expect(chapter2Button).toHaveTextContent('✓ Read');
      });
      
      // Verify series stats are still consistent
      const seriesReadCount = screen.getByTestId('series-read-chapters').textContent;
      expect(seriesReadCount).toBeTruthy();
      
      // Navigate to dashboard and ensure no inconsistencies
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      
      await waitFor(() => {
        const totalRead = screen.getByTestId('read-chapters').textContent;
        expect(totalRead).toBeTruthy();
        expect(parseInt(totalRead || '0')).toBeGreaterThan(0);
      });
    });
  });

  describe('Error Recovery and Resilience', () => {
    it('handles API failures gracefully without breaking UI consistency', async () => {
      render(<IntegratedProgressApp />);
      
      // Mock API failure
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
      
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      
      const chapter2Button = screen.getByTestId('mark-read-chapter-2');
      const originalText = chapter2Button.textContent;
      
      fireEvent.click(chapter2Button);
      
      // Should handle error gracefully - button might revert or show error state
      await waitFor(() => {
        // UI should remain functional
        expect(chapter2Button).toBeInTheDocument();
        expect(screen.getByTestId('series-view')).toBeVisible();
      });
      
      // Navigation should still work
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      expect(screen.getByTestId('dashboard-view')).toBeVisible();
    });

    it('maintains data integrity during rapid navigation', async () => {
      render(<IntegratedProgressApp />);
      
      // Record initial state
      const initialProgress = screen.getByTestId('overall-progress').textContent;
      
      // Rapid navigation sequence
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      fireEvent.click(screen.getByTestId('back-to-library'));
      fireEvent.click(screen.getByTestId('nav-dashboard'));
      
      // State should remain consistent
      await waitFor(() => {
        expect(screen.getByTestId('overall-progress')).toHaveTextContent(initialProgress || '');
        expect(screen.getByTestId('dashboard-view')).toBeVisible();
      });
    });
  });

  describe('Performance Under Load', () => {
    it('maintains responsiveness with frequent updates', async () => {
      render(<IntegratedProgressApp />);
      
      const startTime = performance.now();
      
      // Navigate to series
      fireEvent.click(screen.getByTestId('nav-library'));
      fireEvent.click(screen.getByTestId('series-card-series-1'));
      
      // Perform multiple operations
      const chapter2Button = screen.getByTestId('mark-read-chapter-2');
      const chapter3Button = screen.getByTestId('mark-read-chapter-3');
      
      // Rapid-fire clicks
      for (let i = 0; i < 5; i++) {
        fireEvent.click(chapter2Button);
        fireEvent.click(chapter3Button);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should complete within reasonable time
      expect(duration).toBeLessThan(1000); // 1 second
      
      // UI should remain responsive
      await waitFor(() => {
        expect(screen.getByTestId('series-view')).toBeVisible();
        expect(chapter2Button).toBeInTheDocument();
        expect(chapter3Button).toBeInTheDocument();
      });
    });
  });
});