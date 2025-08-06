/**
 * Reading Progress Test Helpers and Utilities
 * 
 * This module provides helper functions, mocks, and utilities specifically
 * for testing the R-2 reading progress features in various scenarios.
 */

import { Page, expect, Locator } from '@playwright/test';
import { TestSeries, TestChapter, TestDashboardStats } from '../fixtures/progress-test-data';

// Mock setup helpers for Jest tests
export class ProgressMockHelpers {
  static setupBasicMocks() {
    // Mock Next.js router
    jest.mock('next/navigation', () => ({
      useRouter: () => ({
        push: jest.fn(),
        refresh: jest.fn(),
        back: jest.fn(),
        forward: jest.fn(),
        prefetch: jest.fn(),
        replace: jest.fn(),
      }),
    }));

    // Mock toast notifications
    jest.mock('@/hooks/use-toast', () => ({
      useToast: () => ({
        toast: jest.fn(),
      }),
    }));

    // Mock window.performance
    Object.defineProperty(window, 'performance', {
      value: {
        now: jest.fn(() => Date.now()),
        mark: jest.fn(),
        measure: jest.fn(),
        getEntriesByName: jest.fn(() => []),
        getEntriesByType: jest.fn(() => []),
      },
    });
  }

  static setupSWRMock(apiResponses: Record<string, any>) {
    jest.mock('swr', () => ({
      __esModule: true,
      default: jest.fn((key: string) => {
        // Match API endpoints to responses
        for (const [endpoint, response] of Object.entries(apiResponses)) {
          if (key?.includes(endpoint)) {
            return {
              data: response,
              error: null,
              isLoading: false,
              mutate: jest.fn(),
            };
          }
        }
        
        return {
          data: null,
          error: null,
          isLoading: false,
          mutate: jest.fn(),
        };
      }),
    }));
  }

  static setupFetchMock(responses: Array<{ url: string; response: any; status?: number }>) {
    const mockFetch = jest.fn();
    
    responses.forEach(({ url, response, status = 200 }) => {
      mockFetch.mockImplementationOnce((requestUrl: string) => {
        if (requestUrl.includes(url)) {
          return Promise.resolve({
            ok: status >= 200 && status < 300,
            status,
            json: async () => response,
          });
        }
        return Promise.reject(new Error(`Unexpected URL: ${requestUrl}`));
      });
    });

    global.fetch = mockFetch;
    return mockFetch;
  }

  static createProgressState(
    series: TestSeries[], 
    chapters: TestChapter[], 
    stats: TestDashboardStats
  ) {
    return {
      series,
      chapters,
      stats,
      // Helper methods for state management
      updateChapterReadStatus: (chapterId: string, isRead: boolean) => {
        const chapter = chapters.find(ch => ch.id === chapterId);
        if (chapter) {
          chapter.is_read = isRead;
          chapter.last_read_page = isRead ? chapter.page_count - 1 : 0;
          chapter.read_at = isRead ? new Date().toISOString() : undefined;
          
          // Update series stats
          const seriesChapters = chapters.filter(ch => ch.series_id === chapter.series_id);
          const readCount = seriesChapters.filter(ch => ch.is_read).length;
          const targetSeries = series.find(s => s.id === chapter.series_id);
          if (targetSeries) {
            targetSeries.read_chapters = readCount;
          }
          
          // Update overall stats
          const totalRead = chapters.filter(ch => ch.is_read).length;
          stats.chapters_read = totalRead;
          stats.overall_progress_percentage = (totalRead / chapters.length) * 100;
        }
      },
      getSeriesProgress: (seriesId: string) => {
        const targetSeries = series.find(s => s.id === seriesId);
        return targetSeries ? (targetSeries.read_chapters / targetSeries.total_chapters) * 100 : 0;
      },
    };
  }
}

// Playwright E2E test helpers
export class ProgressE2EHelpers {
  constructor(private page: Page) {}

  // Navigation helpers
  async navigateTo(path: string) {
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
  }

  async navigateToLibrary() {
    await this.page.goto('/library');
    await this.page.waitForSelector('[data-testid="series-card"]', { timeout: 10000 });
  }

  async navigateToDashboard() {
    await this.page.goto('/');
    await this.page.waitForSelector('[data-testid="dashboard-stats"]', { timeout: 10000 });
  }

  async navigateToSeries(seriesId: string) {
    await this.page.goto(`/series/${seriesId}`);
    await this.page.waitForSelector('[data-testid="chapter-list"]', { timeout: 10000 });
  }

  async navigateToReader(chapterId: string) {
    await this.page.goto(`/reader/${chapterId}`);
    await this.page.waitForSelector('[data-testid="manga-reader"]', { timeout: 10000 });
  }

  // Element interaction helpers
  async getSeriesCard(index: number = 0): Promise<Locator> {
    const seriesCards = this.page.locator('[data-testid="series-card"]');
    await seriesCards.first().waitFor({ state: 'visible' });
    return seriesCards.nth(index);
  }

  async clickSeriesCard(index: number = 0) {
    const seriesCard = await this.getSeriesCard(index);
    await seriesCard.click();
    await this.page.waitForSelector('[data-testid="chapter-list"]');
  }

  async getChapterElement(chapterId: string): Promise<Locator> {
    return this.page.locator(`[data-testid="chapter-${chapterId}"]`);
  }

  async getMarkReadButton(chapterId: string): Promise<Locator> {
    const chapter = await this.getChapterElement(chapterId);
    return chapter.locator('[data-testid*="mark-read"]');
  }

  async toggleChapterReadStatus(chapterId: string) {
    const markReadButton = await this.getMarkReadButton(chapterId);
    await markReadButton.click();
    
    // Wait for API call to complete
    await this.page.waitForResponse(
      response => response.url().includes('mark-read') && response.ok(),
      { timeout: 5000 }
    );
  }

  // Progress verification helpers
  async getProgressBarValue(selector: string): Promise<number> {
    const progressBar = this.page.locator(selector);
    const ariaValueNow = await progressBar.getAttribute('aria-valuenow');
    return parseInt(ariaValueNow || '0');
  }

  async getProgressPercentageText(selector: string): Promise<string> {
    const progressElement = this.page.locator(selector);
    const text = await progressElement.textContent();
    return text || '0%';
  }

  async verifySeriesProgress(seriesId: string, expectedPercentage: number, tolerance: number = 2) {
    const seriesCard = this.page.locator(`[data-testid="series-card-${seriesId}"]`);
    const progressText = await seriesCard.locator('[data-testid="progress-percentage"]').textContent();
    const actualPercentage = parseInt(progressText?.replace('%', '') || '0');
    
    expect(Math.abs(actualPercentage - expectedPercentage)).toBeLessThanOrEqual(tolerance);
  }

  async verifyDashboardStats(expectedStats: Partial<TestDashboardStats>) {
    if (expectedStats.total_series !== undefined) {
      const totalSeries = await this.page.locator('[data-testid="total-series"]').textContent();
      expect(parseInt(totalSeries || '0')).toBe(expectedStats.total_series);
    }
    
    if (expectedStats.chapters_read !== undefined) {
      const readChapters = await this.page.locator('[data-testid="read-chapters"]').textContent();
      expect(parseInt(readChapters || '0')).toBe(expectedStats.chapters_read);
    }
    
    if (expectedStats.overall_progress_percentage !== undefined) {
      const overallProgress = await this.page.locator('[data-testid="overall-progress"]').textContent();
      const percentage = parseInt(overallProgress?.replace('%', '') || '0');
      expect(Math.abs(percentage - expectedStats.overall_progress_percentage)).toBeLessThanOrEqual(2);
    }
  }

  // Performance measurement helpers
  async measurePageLoadTime(url: string): Promise<number> {
    const startTime = Date.now();
    await this.navigateTo(url);
    return Date.now() - startTime;
  }

  async measureInteractionTime(action: () => Promise<void>): Promise<number> {
    const startTime = Date.now();
    await action();
    return Date.now() - startTime;
  }

  async checkProgressBarAccessibility(selector: string) {
    const progressBar = this.page.locator(selector);
    
    // Check ARIA attributes
    expect(await progressBar.getAttribute('role')).toBe('progressbar');
    expect(await progressBar.getAttribute('aria-valuenow')).toBeTruthy();
    expect(await progressBar.getAttribute('aria-valuemin')).toBe('0');
    expect(await progressBar.getAttribute('aria-valuemax')).toBeTruthy();
    expect(await progressBar.getAttribute('aria-label')).toBeTruthy();
  }

  async checkMarkReadButtonAccessibility(selector: string) {
    const button = this.page.locator(selector);
    
    const ariaLabel = await button.getAttribute('aria-label');
    const ariaPressed = await button.getAttribute('aria-pressed');
    
    expect(ariaLabel).toMatch(/Mark as (read|unread)/);
    expect(ariaPressed).toMatch(/true|false/);
  }

  // Data setup helpers for E2E tests
  async mockAPIResponses(testData: {
    series: TestSeries[];
    chapters: TestChapter[];
    stats: TestDashboardStats;
  }) {
    // Mock dashboard stats endpoint
    await this.page.route('**/api/dashboard/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(testData.stats),
      });
    });

    // Mock series list endpoint
    await this.page.route('**/api/series', (route) => {
      const url = new URL(route.request().url());
      const page = parseInt(url.searchParams.get('page') || '1');
      const perPage = parseInt(url.searchParams.get('per_page') || '20');
      
      const start = (page - 1) * perPage;
      const end = start + perPage;
      const paginatedSeries = testData.series.slice(start, end);
      
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          series: paginatedSeries,
          total: testData.series.length,
          page,
          per_page: perPage,
        }),
      });
    });

    // Mock series detail endpoint
    testData.series.forEach(series => {
      this.page.route(`**/api/series/${series.id}`, (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(series),
        });
      });

      // Mock series chapters endpoint
      this.page.route(`**/api/series/${series.id}/chapters`, (route) => {
        const seriesChapters = testData.chapters.filter(ch => ch.series_id === series.id);
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ chapters: seriesChapters }),
        });
      });
    });

    // Mock mark-read endpoint
    await this.page.route('**/api/chapters/*/mark-read', (route) => {
      const chapterId = route.request().url().match(/chapters\/([^/]+)\/mark-read/)?.[1];
      const chapter = testData.chapters.find(ch => ch.id === chapterId);
      
      if (chapter) {
        chapter.is_read = !chapter.is_read;
        chapter.last_read_page = chapter.is_read ? chapter.page_count - 1 : 0;
        chapter.read_at = chapter.is_read ? new Date().toISOString() : undefined;
        
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: chapter.id,
            is_read: chapter.is_read,
            read_at: chapter.read_at,
          }),
        });
      } else {
        route.fulfill({ status: 404 });
      }
    });
  }

  async simulateSlowNetwork() {
    const client = await this.page.context().newCDPSession(this.page);
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: 1500 * 1024 / 8, // 1.5 Mbps
      uploadThroughput: 750 * 1024 / 8,     // 750 Kbps
      latency: 300, // 300ms latency
    });
  }

  async restoreNetworkConditions() {
    const client = await this.page.context().newCDPSession(this.page);
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: -1,
      uploadThroughput: -1,
      latency: 0,
    });
  }

  // Utility methods
  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/progress-${name}-${Date.now()}.png`,
      fullPage: true 
    });
  }

  async waitForProgressUpdate(timeout: number = 1000) {
    await this.page.waitForTimeout(timeout);
  }

  async scrollToElement(selector: string) {
    const element = this.page.locator(selector);
    await element.scrollIntoViewIfNeeded();
  }

  async verifyElementVisibility(selector: string, shouldBeVisible: boolean = true) {
    const element = this.page.locator(selector);
    if (shouldBeVisible) {
      await expect(element).toBeVisible();
    } else {
      await expect(element).not.toBeVisible();
    }
  }
}

// Assertion helpers
export class ProgressAssertions {
  static expectProgressMatch(actual: number, expected: number, tolerance: number = 1) {
    expect(Math.abs(actual - expected)).toBeLessThanOrEqual(tolerance);
  }

  static expectProgressInRange(value: number, min: number, max: number) {
    expect(value).toBeGreaterThanOrEqual(min);
    expect(value).toBeLessThanOrEqual(max);
  }

  static expectValidProgressPercentage(value: number) {
    this.expectProgressInRange(value, 0, 100);
  }

  static expectStatsConsistency(
    series: TestSeries[],
    chapters: TestChapter[],
    stats: TestDashboardStats
  ) {
    // Verify total counts
    expect(stats.total_series).toBe(series.length);
    expect(stats.total_chapters).toBe(chapters.length);
    
    // Verify read chapters
    const actualReadChapters = chapters.filter(ch => ch.is_read).length;
    expect(stats.chapters_read).toBe(actualReadChapters);
    
    // Verify overall progress
    const expectedProgress = chapters.length > 0 ? (actualReadChapters / chapters.length) * 100 : 0;
    this.expectProgressMatch(stats.overall_progress_percentage, expectedProgress, 1);
    
    // Verify series breakdown
    const completedSeries = series.filter(s => s.read_chapters === s.total_chapters).length;
    const unreadSeries = series.filter(s => s.read_chapters === 0).length;
    const inProgressSeries = series.length - completedSeries - unreadSeries;
    
    expect(stats.series_stats.completed).toBe(completedSeries);
    expect(stats.series_stats.unread).toBe(unreadSeries);
    expect(stats.series_stats.in_progress).toBe(inProgressSeries);
  }
}

// Export everything
export default {
  ProgressMockHelpers,
  ProgressE2EHelpers,
  ProgressAssertions,
};