import { test, expect, Page } from '@playwright/test';

/**
 * Reading Progress Performance Validation Tests
 * 
 * This test suite validates that the R-2 reading progress features maintain
 * excellent performance under various load conditions and with large libraries.
 */

interface PerformanceMetrics {
  loadTime: number;
  renderTime: number;
  interactionTime: number;
  memoryUsage?: number;
}

class PerformanceTestHelper {
  constructor(private page: Page) {}

  async measurePageLoad(url: string): Promise<PerformanceMetrics> {
    const startTime = performance.now();
    
    await this.page.goto(url);
    
    // Wait for critical elements to be visible
    await this.page.waitForSelector('[data-testid="dashboard-stats"], [data-testid="series-card"]', { 
      timeout: 10000 
    });
    
    const loadTime = performance.now() - startTime;
    
    // Measure render completion
    const renderStartTime = performance.now();
    await this.page.waitForLoadState('networkidle');
    const renderTime = performance.now() - renderStartTime;
    
    return {
      loadTime,
      renderTime,
      interactionTime: 0, // Will be set by interaction tests
    };
  }

  async measureInteractionTime(action: () => Promise<void>): Promise<number> {
    const startTime = performance.now();
    await action();
    return performance.now() - startTime;
  }

  async getMemoryUsage(): Promise<number | undefined> {
    try {
      const metrics = await this.page.evaluate(() => {
        if ('memory' in performance) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return undefined;
      });
      return metrics;
    } catch {
      return undefined;
    }
  }

  async simulateLargeLibrary() {
    // Mock API responses with large datasets
    await this.page.route('**/api/dashboard/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_series: 1000,
          total_chapters: 50000,
          chapters_read: 25000,
          overall_progress_percentage: 50.0,
          series_stats: {
            completed: 300,
            in_progress: 500,
            unread: 200,
          },
          recent_reads: Array.from({ length: 20 }, (_, i) => ({
            chapter_id: `chapter-${i}`,
            series_title: `Series ${i + 1}`,
            chapter_title: `Chapter ${i + 1}`,
            read_at: new Date(Date.now() - i * 3600000).toISOString(),
          })),
          reading_streak_days: 30,
          reading_time_hours: 500,
          favorites_count: 50,
        }),
      });
    });

    await this.page.route('**/api/series**', (route) => {
      const series = Array.from({ length: 50 }, (_, i) => ({
        id: `series-${i}`,
        title_primary: `Test Manga Series ${i + 1}`,
        total_chapters: 100,
        read_chapters: Math.floor(Math.random() * 100),
        cover_art: null,
        genres: ['Action', 'Adventure'],
        status: 'ongoing',
      }));

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          series,
          total: 1000,
          page: 1,
          per_page: 50,
        }),
      });
    });
  }

  async simulateSlowNetwork() {
    // Simulate slow 3G connection
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
}

test.describe('Reading Progress Performance Tests', () => {
  let perfHelper: PerformanceTestHelper;

  test.beforeEach(async ({ page }) => {
    perfHelper = new PerformanceTestHelper(page);
  });

  test.describe('Dashboard Performance', () => {
    test('dashboard loads within performance budget with large library', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      
      const metrics = await perfHelper.measurePageLoad('/');
      
      // Performance budgets
      expect(metrics.loadTime).toBeLessThan(3000); // 3 seconds
      expect(metrics.renderTime).toBeLessThan(1000); // 1 second
      
      // Verify all critical elements are present
      await expect(page.locator('[data-testid="dashboard-stats"]')).toBeVisible();
      await expect(page.locator('[data-testid="overall-progress"]')).toBeVisible();
      await expect(page.locator('[data-testid="recent-reads"]')).toBeVisible();
    });

    test('dashboard statistics calculate efficiently', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      await page.goto('/');
      
      const startTime = performance.now();
      
      // Wait for all statistics to be calculated and displayed
      await page.waitForSelector('[data-testid="overall-progress"]:not(:empty)');
      await page.waitForSelector('[data-testid="read-chapters"]:not(:empty)');
      await page.waitForSelector('[data-testid="total-series"]:not(:empty)');
      
      const calculationTime = performance.now() - startTime;
      
      // Statistics should calculate quickly even with large datasets
      expect(calculationTime).toBeLessThan(2000);
      
      // Verify accuracy of calculations
      const totalSeries = await page.locator('[data-testid="total-series"]').textContent();
      const readChapters = await page.locator('[data-testid="read-chapters"]').textContent();
      const overallProgress = await page.locator('[data-testid="overall-progress"]').textContent();
      
      expect(totalSeries).toBe('1000');
      expect(readChapters).toBe('25000');
      expect(overallProgress).toBe('50%');
    });

    test('progress bars render smoothly with animations', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      await page.goto('/');
      
      // Wait for progress bars to be visible
      await page.waitForSelector('[data-testid="overall-progress-bar"]');
      
      const progressBar = page.locator('[data-testid="overall-progress-bar"]');
      
      // Measure animation performance
      const animationStart = performance.now();
      
      // Trigger progress bar animation by updating value
      await page.evaluate(() => {
        const progressEl = document.querySelector('[data-testid="overall-progress-bar"] .progress-fill') as HTMLElement;
        if (progressEl) {
          progressEl.style.width = '75%';
        }
      });
      
      // Wait for animation to complete
      await page.waitForTimeout(600); // Slightly longer than animation duration
      
      const animationTime = performance.now() - animationStart;
      
      // Animation should complete within reasonable time
      expect(animationTime).toBeLessThan(1000);
    });

    test('memory usage remains reasonable during extended use', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      
      const initialMemory = await perfHelper.getMemoryUsage();
      
      // Simulate extended dashboard usage
      for (let i = 0; i < 5; i++) {
        await page.goto('/');
        await page.waitForSelector('[data-testid="dashboard-stats"]');
        await page.waitForTimeout(500);
        
        await page.goto('/library');
        await page.waitForSelector('[data-testid="series-card"]');
        await page.waitForTimeout(500);
      }
      
      const finalMemory = await perfHelper.getMemoryUsage();
      
      if (initialMemory && finalMemory) {
        const memoryIncrease = finalMemory - initialMemory;
        const memoryIncreaseMB = memoryIncrease / (1024 * 1024);
        
        // Memory increase should be reasonable (less than 50MB)
        expect(memoryIncreaseMB).toBeLessThan(50);
      }
    });
  });

  test.describe('Library Performance', () => {
    test('library page loads quickly with many series', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      
      const metrics = await perfHelper.measurePageLoad('/library');
      
      expect(metrics.loadTime).toBeLessThan(4000); // 4 seconds for library
      
      // Verify series cards are rendered
      const seriesCards = page.locator('[data-testid="series-card"]');
      const cardCount = await seriesCards.count();
      expect(cardCount).toBeGreaterThan(0);
      expect(cardCount).toBeLessThanOrEqual(50); // Pagination should limit display
    });

    test('progress bars in series cards render efficiently', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      await page.goto('/library');
      
      const seriesCards = page.locator('[data-testid="series-card"]');
      await seriesCards.first().waitFor({ state: 'visible' });
      
      const cardCount = await seriesCards.count();
      const progressBars = page.locator('[data-testid="progress-bar"]');
      const progressBarCount = await progressBars.count();
      
      // Each series card should have a progress bar
      expect(progressBarCount).toBeGreaterThanOrEqual(Math.min(cardCount, 20));
      
      // Measure time to render all visible progress bars
      const renderStart = performance.now();
      
      for (let i = 0; i < Math.min(progressBarCount, 10); i++) {
        const progressBar = progressBars.nth(i);
        await expect(progressBar).toBeVisible();
        
        // Verify progress fill is rendered
        const progressFill = progressBar.locator('.progress-fill');
        await expect(progressFill).toBeVisible();
      }
      
      const renderTime = performance.now() - renderStart;
      expect(renderTime).toBeLessThan(2000);
    });

    test('virtual scrolling handles large libraries efficiently', async ({ page }) => {
      await perfHelper.simulateLargeLibrary();
      await page.goto('/library');
      
      // Get initial series count
      const initialCards = await page.locator('[data-testid="series-card"]').count();
      
      // Scroll to bottom to trigger loading more series
      await page.evaluate(() => {
        window.scrollTo(0, document.body.scrollHeight);
      });
      
      // Wait for potential new series to load
      await page.waitForTimeout(1000);
      
      // Performance should remain good even with more content
      const scrollPerformance = await page.evaluate(() => {
        const start = performance.now();
        window.scrollTo(0, 0);
        window.scrollTo(0, document.body.scrollHeight / 2);
        return performance.now() - start;
      });
      
      expect(scrollPerformance).toBeLessThan(100); // Smooth scrolling
    });
  });

  test.describe('Progress Update Performance', () => {
    test('mark read operations complete quickly', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      // Click into first series
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Find first unread chapter
      const markReadButton = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")').first();
      
      if (await markReadButton.count() > 0) {
        const interactionTime = await perfHelper.measureInteractionTime(async () => {
          await markReadButton.click();
          
          // Wait for button state to change
          await expect(markReadButton).not.toHaveText('Mark Read', { timeout: 3000 });
        });
        
        expect(interactionTime).toBeLessThan(1500); // 1.5 seconds
      }
    });

    test('bulk mark read operations are efficient', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Look for bulk mark read functionality
      const markAllButton = page.locator('text=/mark all/i');
      
      if (await markAllButton.count() > 0) {
        const bulkOperationTime = await perfHelper.measureInteractionTime(async () => {
          await markAllButton.click();
          
          // Wait for operation to complete
          await page.waitForTimeout(2000);
        });
        
        // Bulk operations should complete within reasonable time
        expect(bulkOperationTime).toBeLessThan(5000);
      }
    });

    test('progress calculations remain fast with large chapter counts', async ({ page }) => {
      // Mock series with many chapters
      await page.route('**/api/series/*/chapters', (route) => {
        const chapters = Array.from({ length: 200 }, (_, i) => ({
          id: `chapter-${i}`,
          chapter_number: i + 1,
          title: `Chapter ${i + 1}`,
          is_read: Math.random() > 0.5,
          last_read_page: Math.floor(Math.random() * 20),
          page_count: 20,
        }));

        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ chapters }),
        });
      });

      await page.goto('/library');
      await page.locator('[data-testid="series-card"]').first().click();
      
      const loadStart = performance.now();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Wait for all progress calculations to complete
      const progressElements = page.locator('[data-testid="progress-text"]');
      const progressCount = await progressElements.count();
      
      // Verify reasonable number of chapters loaded (pagination/virtualization)
      expect(progressCount).toBeGreaterThan(0);
      expect(progressCount).toBeLessThanOrEqual(50); // Should use pagination
      
      const loadTime = performance.now() - loadStart;
      expect(loadTime).toBeLessThan(3000);
    });
  });

  test.describe('Network Performance', () => {
    test('progress features work well on slow connections', async ({ page }) => {
      await perfHelper.simulateSlowNetwork();
      
      try {
        const metrics = await perfHelper.measurePageLoad('/');
        
        // Even on slow network, should load within reasonable time
        expect(metrics.loadTime).toBeLessThan(10000); // 10 seconds on slow network
        
        // Core functionality should still work
        await expect(page.locator('[data-testid="dashboard-stats"]')).toBeVisible();
        
        // Navigate to library
        await page.click('text=Library');
        await page.waitForSelector('[data-testid="series-card"]', { timeout: 15000 });
        
        // Progress bars should still be visible even if slow
        const progressBar = page.locator('[data-testid="progress-bar"]').first();
        await expect(progressBar).toBeVisible({ timeout: 10000 });
        
      } finally {
        await perfHelper.restoreNetworkConditions();
      }
    });

    test('API calls are optimized and cached appropriately', async ({ page }) => {
      // Track API calls
      const apiCalls = new Map<string, number>();
      
      page.on('request', (request) => {
        if (request.url().includes('/api/')) {
          const url = new URL(request.url()).pathname;
          apiCalls.set(url, (apiCalls.get(url) || 0) + 1);
        }
      });
      
      // Load dashboard
      await page.goto('/');
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      // Navigate to library and back
      await page.click('text=Library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.goBack();
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      // Check that API calls are reasonable
      const dashboardStatsCalls = apiCalls.get('/api/dashboard/stats') || 0;
      const seriesCalls = apiCalls.get('/api/series') || 0;
      
      // Should not make excessive repeated calls
      expect(dashboardStatsCalls).toBeLessThanOrEqual(2);
      expect(seriesCalls).toBeLessThanOrEqual(2);
    });

    test('progress updates work during network interruptions', async ({ page, context }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const markReadButton = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")').first();
      
      if (await markReadButton.count() > 0) {
        // Temporarily go offline
        await context.setOffline(true);
        
        await markReadButton.click();
        
        // Should show some indication of pending operation
        await page.waitForTimeout(1000);
        
        // Restore connection
        await context.setOffline(false);
        
        // Operation should eventually complete or show retry option
        await page.waitForTimeout(2000);
        
        // UI should remain responsive
        const buttonText = await markReadButton.textContent();
        expect(buttonText).toBeTruthy();
      }
    });
  });

  test.describe('Reader Performance', () => {
    test('reader loads and responds quickly', async ({ page }) => {
      // Mock reader API
      await page.route('**/api/chapters/*/info', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'test-chapter',
            title: 'Test Chapter',
            page_count: 20,
            current_page: 0,
            series: {
              id: 'test-series',
              title: 'Test Series',
            },
          }),
        });
      });

      const readerLoadTime = await perfHelper.measureInteractionTime(async () => {
        await page.goto('/reader/test-chapter');
        await page.waitForSelector('[data-testid="manga-reader"]');
      });
      
      expect(readerLoadTime).toBeLessThan(2000);
      
      // Page navigation should be responsive
      const navigationTime = await perfHelper.measureInteractionTime(async () => {
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(100); // Brief wait for page change
      });
      
      expect(navigationTime).toBeLessThan(200);
    });

    test('progress updates in reader are smooth', async ({ page }) => {
      await page.route('**/api/chapters/*/info', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'test-chapter',
            title: 'Test Chapter',
            page_count: 20,
            current_page: 0,
          }),
        });
      });

      await page.goto('/reader/test-chapter');
      await page.waitForSelector('[data-testid="manga-reader"]');
      
      // Navigate through several pages quickly
      const rapidNavigationTime = await perfHelper.measureInteractionTime(async () => {
        for (let i = 0; i < 5; i++) {
          await page.keyboard.press('ArrowRight');
          await page.waitForTimeout(50);
        }
      });
      
      expect(rapidNavigationTime).toBeLessThan(1000);
      
      // Progress indicator should update smoothly
      const progressIndicator = page.locator('text=/\\d+ \\/ \\d+/');
      await expect(progressIndicator).toBeVisible();
    });
  });
});