/**
 * MSW API Handlers for KireMisu E2E Tests
 * Following the testing strategy: MSW for API mocking in E2E tests
 */

import { http, HttpResponse } from 'msw';
import { 
  TEST_SERIES_DATA, 
  TEST_NOTIFICATIONS_DATA, 
  TEST_WATCHING_DATA,
  TestDataManager,
  mockApiResponses 
} from '../fixtures/manga-test-data';

/**
 * Base URL for API requests
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Mock handlers for KireMisu API endpoints
 */
export const apiHandlers = [
  // Library/Series endpoints
  http.get(`${API_BASE}/api/series`, () => {
    return HttpResponse.json(mockApiResponses.getSeriesList());
  }),

  http.get(`${API_BASE}/api/series/:id`, ({ params }) => {
    const { id } = params;
    const series = mockApiResponses.getSeriesById(id as string);
    
    if (!series) {
      return HttpResponse.json(
        { detail: 'Series not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json(series);
  }),

  // Watching system endpoints
  http.get(`${API_BASE}/api/watching`, () => {
    return HttpResponse.json(TEST_WATCHING_DATA);
  }),

  http.post(`${API_BASE}/api/series/:id/watch`, async ({ params, request }) => {
    const { id } = params;
    const body = await request.json() as { watching: boolean };
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Find series and update watching status
    const series = TestDataManager.getSeriesById(id as string);
    if (!series) {
      return HttpResponse.json(
        { detail: 'Series not found' },
        { status: 404 }
      );
    }

    // Check if series has MangaDx ID (required for watching)
    if (!series.mangadx_id) {
      return HttpResponse.json(
        { detail: 'Series cannot be watched without MangaDx integration' },
        { status: 400 }
      );
    }
    
    // Update series watching status in test data
    series.watching_enabled = body.watching;
    
    return HttpResponse.json(
      mockApiResponses.toggleWatch(id as string, body.watching)
    );
  }),

  http.delete(`${API_BASE}/api/series/:id/watch`, ({ params }) => {
    const { id } = params;
    const series = TestDataManager.getSeriesById(id as string);
    
    if (!series) {
      return HttpResponse.json(
        { detail: 'Series not found' },
        { status: 404 }
      );
    }
    
    // Update series watching status
    series.watching_enabled = false;
    
    return HttpResponse.json(
      mockApiResponses.toggleWatch(id as string, false)
    );
  }),

  // Notifications endpoints
  http.get(`${API_BASE}/api/notifications`, ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '50');
    const offset = parseInt(url.searchParams.get('offset') || '0');
    
    const notifications = TEST_NOTIFICATIONS_DATA.slice(offset, offset + limit);
    
    return HttpResponse.json({
      notifications,
      total: TEST_NOTIFICATIONS_DATA.length,
      unread_count: TestDataManager.getUnreadNotifications().length
    });
  }),

  http.put(`${API_BASE}/api/notifications/:id/read`, ({ params }) => {
    const { id } = params;
    
    // Find and update notification
    const notification = TEST_NOTIFICATIONS_DATA.find(n => n.id === id);
    if (!notification) {
      return HttpResponse.json(
        { detail: 'Notification not found' },
        { status: 404 }
      );
    }
    
    notification.is_read = true;
    
    return HttpResponse.json(
      mockApiResponses.markNotificationRead(id as string)
    );
  }),

  http.post(`${API_BASE}/api/notifications/mark-all-read`, () => {
    // Mark all notifications as read
    TEST_NOTIFICATIONS_DATA.forEach(notification => {
      notification.is_read = true;
    });
    
    return HttpResponse.json({
      message: 'All notifications marked as read',
      marked_count: TEST_NOTIFICATIONS_DATA.length
    });
  }),

  // Chapter endpoints (for reader functionality)
  http.get(`${API_BASE}/api/series/:seriesId/chapters`, ({ params }) => {
    const { seriesId } = params;
    const series = TestDataManager.getSeriesById(seriesId as string);
    
    if (!series) {
      return HttpResponse.json(
        { detail: 'Series not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json({
      chapters: series.chapters,
      total: series.chapters.length
    });
  }),

  http.get(`${API_BASE}/api/chapters/:id`, ({ params }) => {
    const { id } = params;
    
    // Find chapter across all series
    let chapter = null;
    for (const series of TEST_SERIES_DATA) {
      chapter = series.chapters.find(c => c.id === id);
      if (chapter) break;
    }
    
    if (!chapter) {
      return HttpResponse.json(
        { detail: 'Chapter not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json(chapter);
  }),

  // Progress tracking endpoints
  http.put(`${API_BASE}/api/chapters/:id/read`, ({ params }) => {
    const { id } = params;
    
    // Find and update chapter
    let chapter = null;
    for (const series of TEST_SERIES_DATA) {
      chapter = series.chapters.find(c => c.id === id);
      if (chapter) {
        chapter.is_read = true;
        // Update series read count
        series.read_chapters = series.chapters.filter(c => c.is_read).length;
        break;
      }
    }
    
    if (!chapter) {
      return HttpResponse.json(
        { detail: 'Chapter not found' },
        { status: 404 }
      );
    }
    
    return HttpResponse.json({
      id: chapter.id,
      is_read: true,
      updated_at: new Date().toISOString()
    });
  }),

  // Error simulation endpoints for testing error handling
  http.get(`${API_BASE}/api/test/error-500`, () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }),

  http.get(`${API_BASE}/api/test/timeout`, () => {
    // Simulate network timeout - never resolve
    return new Promise(() => {});
  }),

  http.get(`${API_BASE}/api/test/slow-response`, async () => {
    // Simulate slow API response
    await new Promise(resolve => setTimeout(resolve, 5000));
    return HttpResponse.json({ message: 'Slow response' });
  })
];

/**
 * Handlers for specific test scenarios
 */
export const scenarioHandlers = {
  /**
   * Empty library scenario - no series
   */
  emptyLibrary: [
    http.get(`${API_BASE}/api/series`, () => {
      return HttpResponse.json({
        series: [],
        total: 0,
        page: 1,
        limit: 50
      });
    }),
    
    http.get(`${API_BASE}/api/notifications`, () => {
      return HttpResponse.json({
        notifications: [],
        total: 0,
        unread_count: 0
      });
    }),
    
    http.get(`${API_BASE}/api/watching`, () => {
      return HttpResponse.json([]);
    })
  ],

  /**
   * Large library scenario - performance testing
   */
  largeLibrary: [
    http.get(`${API_BASE}/api/series`, () => {
      const largeSeries = TestDataManager.generatePerformanceTestSeries(100);
      return HttpResponse.json({
        series: largeSeries,
        total: largeSeries.length,
        page: 1,
        limit: 50
      });
    })
  ],

  /**
   * Network error scenario
   */
  networkErrors: [
    http.get(`${API_BASE}/api/series`, () => {
      return HttpResponse.json(
        { detail: 'Service temporarily unavailable' },
        { status: 503 }
      );
    }),
    
    http.post(`${API_BASE}/api/series/:id/watch`, () => {
      return HttpResponse.json(
        { detail: 'Failed to update watch status' },
        { status: 500 }
      );
    })
  ]
};

/**
 * Helper function to get handlers for specific test scenario
 */
export function getHandlersForScenario(scenario: keyof typeof scenarioHandlers) {
  return [...apiHandlers, ...scenarioHandlers[scenario]];
}

export default apiHandlers;