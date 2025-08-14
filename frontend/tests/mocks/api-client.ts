/**
 * Jest mocks for API client - Unit Tests
 * Replaces MSW for component-level testing
 */

import { jest } from '@jest/globals';

// Mock data that matches our existing test fixtures
export const mockSeriesData = [
  {
    id: 'series-1',
    title: 'Test Manga Series 1',
    chapters: 25,
    read_chapters: 3,
    watching_enabled: true,
    mangadx_id: 'mangadx-1'
  },
  {
    id: 'series-2', 
    title: 'Test Manga Series 2',
    chapters: 15,
    read_chapters: 15,
    watching_enabled: false,
    mangadx_id: null
  }
];

export const mockChapterData = {
  id: 'chapter-1',
  title: 'Chapter 1',
  pages: ['page1.jpg', 'page2.jpg', 'page3.jpg'],
  is_read: false,
  series_id: 'series-1'
};

export const mockNotifications = [
  {
    id: 'notif-1',
    message: 'New chapter available for Test Series',
    is_read: false,
    created_at: '2025-01-13T10:00:00Z'
  }
];

// Default successful API client mocks
export const createApiClientMocks = () => ({
  // Series operations
  getSeries: jest.fn().mockResolvedValue({
    series: mockSeriesData,
    total: mockSeriesData.length
  }),
  
  getSeriesById: jest.fn().mockImplementation((id: string) => 
    Promise.resolve(mockSeriesData.find(s => s.id === id))
  ),
  
  // Chapter operations  
  getChapter: jest.fn().mockResolvedValue(mockChapterData),
  
  getChaptersBySeriesId: jest.fn().mockResolvedValue({
    chapters: [mockChapterData],
    total: 1
  }),
  
  markChapterRead: jest.fn().mockResolvedValue({
    id: 'chapter-1',
    is_read: true,
    updated_at: new Date().toISOString()
  }),
  
  // Watching operations
  toggleSeriesWatch: jest.fn().mockImplementation((seriesId: string, watching: boolean) =>
    Promise.resolve({ id: seriesId, watching_enabled: watching })
  ),
  
  getWatchingSeries: jest.fn().mockResolvedValue([
    mockSeriesData.filter(s => s.watching_enabled)
  ]),
  
  // Notification operations
  getNotifications: jest.fn().mockResolvedValue({
    notifications: mockNotifications,
    total: mockNotifications.length,
    unread_count: mockNotifications.filter(n => !n.is_read).length
  }),
  
  markNotificationRead: jest.fn().mockImplementation((id: string) =>
    Promise.resolve({ id, is_read: true })
  ),
  
  markAllNotificationsRead: jest.fn().mockResolvedValue({
    message: 'All notifications marked as read',
    marked_count: mockNotifications.length
  })
});

// Error scenario mocks
export const createErrorApiClientMocks = () => ({
  getSeries: jest.fn().mockRejectedValue(new Error('Failed to fetch series')),
  getSeriesById: jest.fn().mockRejectedValue(new Error('Series not found')),
  getChapter: jest.fn().mockRejectedValue(new Error('Chapter not found')),
  getChaptersBySeriesId: jest.fn().mockRejectedValue(new Error('Failed to fetch chapters')),
  markChapterRead: jest.fn().mockRejectedValue(new Error('Failed to mark chapter as read')),
  toggleSeriesWatch: jest.fn().mockRejectedValue(new Error('Failed to toggle watch status')),
  getWatchingSeries: jest.fn().mockRejectedValue(new Error('Failed to fetch watching series')),
  getNotifications: jest.fn().mockRejectedValue(new Error('Failed to fetch notifications')),
  markNotificationRead: jest.fn().mockRejectedValue(new Error('Failed to mark notification as read')),
  markAllNotificationsRead: jest.fn().mockRejectedValue(new Error('Failed to mark all notifications as read'))
});

// Helper to reset all mocks between tests
export const resetApiClientMocks = (mocks: ReturnType<typeof createApiClientMocks>) => {
  Object.values(mocks).forEach(mock => {
    if (jest.isMockFunction(mock)) {
      mock.mockClear();
    }
  });
};