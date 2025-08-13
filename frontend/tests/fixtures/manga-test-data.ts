/**
 * Test Data Fixtures for KireMisu E2E Tests
 * Following the testing strategy documented in docs/TESTING_READER.md
 */

import { SeriesResponse, ChapterResponse, NotificationResponse } from '@/lib/api';

export interface TestSeries extends SeriesResponse {
  chapters: TestChapter[];
}

export interface TestChapter extends ChapterResponse {
  pages: number;
}

/**
 * Comprehensive test data matching real manga library structure
 */
export const TEST_SERIES_DATA: TestSeries[] = [
  {
    id: 'test-series-1',
    title_primary: 'Attack on Titan E2E',
    title_english: 'Attack on Titan',
    title_romaji: 'Shingeki no Kyojin',
    author: 'Hajime Isayama',
    artist: 'Hajime Isayama',
    description: 'Test series for E2E watching system tests',
    status: 'completed',
    year: 2009,
    genres: ['Action', 'Drama', 'Fantasy', 'Military'],
    tags: ['test', 'e2e', 'watching'],
    total_chapters: 10,
    read_chapters: 5,
    last_read_at: '2024-01-15T10:30:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T10:30:00Z',
    directory_path: '/test/manga/attack-on-titan-e2e',
    mangadx_id: 'e2e-test-aot-001',
    watching_enabled: false,
    chapters: [
      {
        id: 'test-chapter-1-1',
        series_id: 'test-series-1',
        title: 'To You, 2,000 Years From Now',
        chapter_number: 1,
        volume_number: 1,
        pages: 45,
        file_path: '/test/manga/attack-on-titan-e2e/Chapter 1.cbz',
        file_size: 12345678,
        is_read: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T10:30:00Z'
      },
      {
        id: 'test-chapter-1-2',
        series_id: 'test-series-1',
        title: 'That Day',
        chapter_number: 2,
        volume_number: 1,
        pages: 42,
        file_path: '/test/manga/attack-on-titan-e2e/Chapter 2.cbz',
        file_size: 11234567,
        is_read: true,
        created_at: '2024-01-02T00:00:00Z',
        updated_at: '2024-01-15T10:30:00Z'
      },
      {
        id: 'test-chapter-1-3',
        series_id: 'test-series-1',
        title: 'Night of the Graduation Ceremony',
        chapter_number: 3,
        volume_number: 1,
        pages: 48,
        file_path: '/test/manga/attack-on-titan-e2e/Chapter 3.cbz',
        file_size: 13456789,
        is_read: false,
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-03T00:00:00Z'
      }
      // Additional chapters would be here...
    ]
  },
  {
    id: 'test-series-2',
    title_primary: 'One Piece E2E',
    title_english: 'One Piece',
    title_romaji: 'One Piece',
    author: 'Eiichiro Oda',
    artist: 'Eiichiro Oda',
    description: 'Test series for notification and watching features',
    status: 'ongoing',
    year: 1997,
    genres: ['Action', 'Adventure', 'Comedy', 'Shounen'],
    tags: ['test', 'e2e', 'notifications'],
    total_chapters: 15,
    read_chapters: 0,
    last_read_at: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    directory_path: '/test/manga/one-piece-e2e',
    mangadx_id: 'e2e-test-op-002',
    watching_enabled: true,
    chapters: [
      {
        id: 'test-chapter-2-1',
        series_id: 'test-series-2',
        title: 'Romance Dawn',
        chapter_number: 1,
        volume_number: 1,
        pages: 52,
        file_path: '/test/manga/one-piece-e2e/Chapter 1.cbz',
        file_size: 15678901,
        is_read: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
      // Additional chapters...
    ]
  },
  {
    id: 'test-series-3',
    title_primary: 'Naruto E2E',
    title_english: 'Naruto',
    title_romaji: 'Naruto',
    author: 'Masashi Kishimoto',
    artist: 'Masashi Kishimoto',
    description: 'Test series for comprehensive E2E testing',
    status: 'completed',
    year: 1999,
    genres: ['Action', 'Adventure', 'Martial Arts', 'Shounen'],
    tags: ['test', 'e2e', 'comprehensive'],
    total_chapters: 8,
    read_chapters: 8,
    last_read_at: '2024-01-20T15:45:00Z',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-20T15:45:00Z',
    directory_path: '/test/manga/naruto-e2e',
    mangadx_id: 'e2e-test-naruto-003',
    watching_enabled: false,
    chapters: [
      {
        id: 'test-chapter-3-1',
        series_id: 'test-series-3',
        title: 'Uzumaki Naruto',
        chapter_number: 1,
        volume_number: 1,
        pages: 40,
        file_path: '/test/manga/naruto-e2e/Chapter 1.cbz',
        file_size: 10987654,
        is_read: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-20T15:45:00Z'
      }
      // Additional chapters...
    ]
  }
];

/**
 * Test notification data for watching system tests
 */
export const TEST_NOTIFICATIONS_DATA: NotificationResponse[] = [
  {
    id: 'test-notification-1',
    type: 'new_chapter',
    title: 'New chapter available for One Piece E2E',
    message: 'Chapter 2: The Great Pirate Era Begins is now available',
    is_read: false,
    created_at: '2024-01-21T09:00:00Z',
    link: '/library/series/test-series-2/chapter/test-chapter-2-2'
  },
  {
    id: 'test-notification-2',
    type: 'series_complete',
    title: 'Series completed: Attack on Titan E2E',
    message: 'You have finished reading all available chapters',
    is_read: false,
    created_at: '2024-01-20T16:00:00Z',
    link: '/library/series/test-series-1'
  },
  {
    id: 'test-notification-3',
    type: 'library_update',
    title: 'Library scan completed',
    message: '3 new chapters found in your library',
    is_read: true,
    created_at: '2024-01-19T12:00:00Z',
    link: '/library'
  }
];

/**
 * Test watching data
 */
export const TEST_WATCHING_DATA = [
  {
    series_id: 'test-series-2',
    series_title: 'One Piece E2E',
    watching_enabled: true,
    last_watched_check: '2024-01-21T08:00:00Z',
    notifications_count: 1
  }
];

/**
 * Helper functions for test data manipulation
 */
export class TestDataManager {
  /**
   * Get series by ID
   */
  static getSeriesById(id: string): TestSeries | undefined {
    return TEST_SERIES_DATA.find(series => series.id === id);
  }

  /**
   * Get series with watching enabled
   */
  static getWatchedSeries(): TestSeries[] {
    return TEST_SERIES_DATA.filter(series => series.watching_enabled);
  }

  /**
   * Get series available for watching (has MangaDx ID)
   */
  static getWatchableSeries(): TestSeries[] {
    return TEST_SERIES_DATA.filter(series => series.mangadx_id && !series.watching_enabled);
  }

  /**
   * Get unread notifications
   */
  static getUnreadNotifications(): NotificationResponse[] {
    return TEST_NOTIFICATIONS_DATA.filter(notification => !notification.is_read);
  }

  /**
   * Generate series for performance testing
   */
  static generatePerformanceTestSeries(count: number): TestSeries[] {
    const series: TestSeries[] = [];
    
    for (let i = 1; i <= count; i++) {
      const chaptersCount = Math.floor(Math.random() * 50) + 10; // 10-60 chapters
      const readChapters = Math.floor(Math.random() * chaptersCount);
      
      series.push({
        id: `perf-test-series-${i}`,
        title_primary: `Performance Test Series ${i}`,
        title_english: `Performance Test Series ${i}`,
        title_romaji: `Performance Test Series ${i}`,
        author: 'Test Author',
        artist: 'Test Artist',
        description: `Generated series for performance testing`,
        status: 'ongoing',
        year: 2020 + (i % 5),
        genres: ['Action', 'Adventure'],
        tags: ['performance', 'test'],
        total_chapters: chaptersCount,
        read_chapters: readChapters,
        last_read_at: readChapters > 0 ? new Date().toISOString() : null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        directory_path: `/test/performance/series-${i}`,
        mangadx_id: Math.random() > 0.3 ? `perf-test-${i}` : null, // 70% have MangaDx ID
        watching_enabled: Math.random() > 0.7, // 30% are being watched
        chapters: [] // Chapters would be generated separately for performance tests
      });
    }
    
    return series;
  }

  /**
   * Create test scenario data sets
   */
  static getTestScenarios() {
    return {
      // Scenario 1: User with mixed reading progress
      mixedProgress: {
        series: TEST_SERIES_DATA,
        notifications: TEST_NOTIFICATIONS_DATA,
        description: 'Mixed reading progress across different series'
      },
      
      // Scenario 2: New user with no progress
      newUser: {
        series: TEST_SERIES_DATA.map(s => ({
          ...s,
          read_chapters: 0,
          last_read_at: null,
          watching_enabled: false,
          chapters: s.chapters.map(c => ({ ...c, is_read: false }))
        })),
        notifications: [],
        description: 'New user with no reading progress'
      },
      
      // Scenario 3: Active user with many notifications
      activeUser: {
        series: TEST_SERIES_DATA.map(s => ({ ...s, watching_enabled: true })),
        notifications: [
          ...TEST_NOTIFICATIONS_DATA,
          ...Array.from({ length: 10 }, (_, i) => ({
            id: `active-notification-${i}`,
            type: 'new_chapter',
            title: `New chapter available for Series ${i}`,
            message: `Chapter ${i + 10} is now available`,
            is_read: false,
            created_at: new Date(Date.now() - i * 3600000).toISOString(), // Staggered over hours
            link: `/library/series/test-series-${(i % 3) + 1}`
          }))
        ],
        description: 'Active user with many unread notifications'
      }
    };
  }
}

/**
 * Mock API responses for testing
 */
export const mockApiResponses = {
  // GET /api/series
  getSeriesList: () => ({
    series: TEST_SERIES_DATA,
    total: TEST_SERIES_DATA.length,
    page: 1,
    limit: 50
  }),

  // GET /api/series/:id
  getSeriesById: (id: string) => TestDataManager.getSeriesById(id),

  // GET /api/notifications
  getNotifications: () => TEST_NOTIFICATIONS_DATA,

  // GET /api/watching
  getWatchingSeries: () => TEST_WATCHING_DATA,

  // POST /api/series/:id/watch
  toggleWatch: (seriesId: string, watching: boolean) => ({
    series_id: seriesId,
    watching_enabled: watching,
    message: watching ? 'Now watching series' : 'No longer watching series'
  }),

  // PUT /api/notifications/:id/read
  markNotificationRead: (notificationId: string) => ({
    id: notificationId,
    is_read: true,
    updated_at: new Date().toISOString()
  })
};