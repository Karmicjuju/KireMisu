/**
 * Simple fetch mocking for integration tests
 * No external dependencies, just direct fetch interception
 */

interface MockResponse {
  status?: number;
  data?: any;
  delay?: number;
}

interface FetchMock {
  [url: string]: MockResponse | ((url: string, options?: any) => MockResponse);
}

let mockResponses: FetchMock = {};
let originalFetch: typeof global.fetch;

/**
 * Setup fetch interception for integration tests
 */
export function setupFetchMock() {
  if (!originalFetch) {
    originalFetch = global.fetch;
  }
  
  global.fetch = jest.fn((url: string, options?: any) => {
    const urlString = typeof url === 'string' ? url : url.toString();
    
    // Find matching mock response
    const exactMatch = mockResponses[urlString];
    if (exactMatch) {
      return createMockResponse(exactMatch, urlString, options);
    }
    
    // Try pattern matching for dynamic URLs
    for (const [pattern, response] of Object.entries(mockResponses)) {
      if (pattern.includes('*') && urlString.includes(pattern.replace('*', ''))) {
        return createMockResponse(response, urlString, options);
      }
    }
    
    // Default: return empty 200 response
    return createMockResponse({ status: 200, data: {} }, urlString, options);
  });
}

/**
 * Create a mock response
 */
function createMockResponse(
  response: MockResponse | ((url: string, options?: any) => MockResponse),
  url: string,
  options?: any
) {
  const resolved = typeof response === 'function' ? response(url, options) : response;
  const { status = 200, data = {}, delay = 0 } = resolved;
  
  const mockResponse = {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: async () => data,
    text: async () => JSON.stringify(data),
    clone: () => mockResponse
  };
  
  if (delay > 0) {
    return new Promise(resolve => setTimeout(() => resolve(mockResponse), delay));
  }
  
  return Promise.resolve(mockResponse);
}

/**
 * Add mock responses for API endpoints
 */
export function mockApi(pattern: string, response: MockResponse | ((url: string, options?: any) => MockResponse)) {
  mockResponses[pattern] = response;
}

/**
 * Setup common KireMisu API mocks
 */
export function setupKireMisuApiMocks() {
  const API_BASE = 'http://localhost:8000';
  
  // Series data
  const testSeries = [
    { id: 'series-1', title: 'Test Series 1', chapters: 25, read_chapters: 3 },
    { id: 'series-2', title: 'Test Series 2', chapters: 15, read_chapters: 15 }
  ];
  
  const testChapters = [
    { id: 'chapter-1', title: 'Chapter 1', pages: ['p1.jpg', 'p2.jpg'], is_read: false },
    { id: 'chapter-2', title: 'Chapter 2', pages: ['p1.jpg'], is_read: true }
  ];
  
  const testNotifications = [
    { id: 'notif-1', message: 'New chapter available', is_read: false },
    { id: 'notif-2', message: 'Series completed', is_read: true }
  ];
  
  // Series endpoints
  mockApi(`${API_BASE}/api/series`, { data: { series: testSeries, total: 2 } });
  mockApi(`${API_BASE}/api/series/*`, (url) => {
    const seriesId = url.split('/').pop();
    const series = testSeries.find(s => s.id === seriesId);
    return series ? { data: series } : { status: 404, data: { error: 'Not found' } };
  });
  
  // Chapter endpoints
  mockApi(`${API_BASE}/api/chapters/*`, (url) => {
    const chapterId = url.split('/').pop();
    const chapter = testChapters.find(c => c.id === chapterId);
    return chapter ? { data: chapter } : { status: 404, data: { error: 'Not found' } };
  });
  
  // Notifications
  mockApi(`${API_BASE}/api/notifications`, {
    data: { 
      notifications: testNotifications, 
      total: 2, 
      unread_count: 1 
    }
  });
  
  // Watch endpoints
  mockApi(`${API_BASE}/api/series/*/watch*`, (url, options) => {
    const method = options?.method || 'GET';
    const seriesId = url.split('/')[5];
    
    if (method === 'POST') {
      return { data: { id: seriesId, watching_enabled: true } };
    } else if (method === 'DELETE') {
      return { data: { id: seriesId, watching_enabled: false } };
    }
    
    return { data: [] };
  });
}

/**
 * Setup error scenarios
 */
export function setupErrorApiMocks() {
  mockApi('http://localhost:8000/api/series', { status: 500, data: { error: 'Server error' } });
  mockApi('http://localhost:8000/api/notifications', { status: 503, data: { error: 'Service unavailable' } });
}

/**
 * Setup timeout scenarios
 */
export function setupTimeoutApiMocks() {
  mockApi('http://localhost:8000/api/series', { delay: 10000, data: {} }); // 10s delay
}

/**
 * Clear all mocks and restore original fetch
 */
export function cleanupFetchMock() {
  mockResponses = {};
  if (originalFetch) {
    global.fetch = originalFetch;
  }
}

/**
 * Reset mocks but keep fetch interception
 */
export function resetFetchMock() {
  mockResponses = {};
}