import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * Comprehensive Reading Progress E2E Tests
 * 
 * This test suite validates the complete R-2 reading progress user experience
 * including critical user journeys, cross-component integration, performance,
 * and accessibility compliance.
 */

interface TestData {
  seriesId: string;
  chapters: Array<{
    id: string;
    chapter_number: number;
    title: string;
    is_read: boolean;
    page_count: number;
  }>;
}

class ReadingProgressPage {
  constructor(private page: Page) {}

  // Navigation helpers
  async navigateToLibrary() {
    await this.page.goto('/library');
    await this.page.waitForSelector('[data-testid="series-card"]', { timeout: 10000 });
  }

  async navigateToDashboard() {
    await this.page.goto('/');
    await this.page.waitForSelector('[data-testid="dashboard-stats"]', { timeout: 10000 });
  }

  async navigateToReader(chapterId: string) {
    await this.page.goto(`/reader/${chapterId}`);
    await this.page.waitForSelector('[data-testid="manga-reader"]', { timeout: 10000 });
  }

  // Series and chapter interactions
  async getSeriesCard(index: number = 0) {
    const seriesCards = this.page.locator('[data-testid="series-card"]');
    return seriesCards.nth(index);
  }

  async getSeriesProgress(seriesCard: any) {
    const progressBar = seriesCard.locator('[data-testid="progress-bar"]');
    const progressText = seriesCard.locator('[data-testid="progress-percentage"]');
    
    return {
      bar: progressBar,
      percentage: await progressText.textContent(),
      isVisible: await progressBar.isVisible(),
    };
  }

  async clickSeriesCard(index: number = 0) {
    const seriesCard = await this.getSeriesCard(index);
    await seriesCard.click();
    await this.page.waitForSelector('[data-testid="chapter-list"]');
  }

  async getChapter(chapterNumber: number) {
    return this.page.locator(`[data-testid*="chapter-"]:has-text("Chapter ${chapterNumber}")`).first();
  }

  async getChapterProgress(chapter: any) {
    const progressBar = chapter.locator('[data-testid="chapter-progress-bar"]');
    const progressText = chapter.locator('[data-testid="progress-text"]');
    
    return {
      bar: progressBar,
      text: await progressText.textContent(),
      isVisible: await progressBar.isVisible(),
    };
  }

  async toggleChapterReadStatus(chapter: any) {
    const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
    await markReadButton.click();
    
    // Wait for API call to complete
    await this.page.waitForResponse(
      response => response.url().includes('mark-read') && response.ok(),
      { timeout: 5000 }
    );
  }

  // Dashboard interactions
  async getDashboardStats() {
    const statsContainer = this.page.locator('[data-testid="dashboard-stats"]');
    
    return {
      totalSeries: await statsContainer.locator('[data-testid="total-series"]').textContent(),
      totalChapters: await statsContainer.locator('[data-testid="total-chapters"]').textContent(),
      readChapters: await statsContainer.locator('[data-testid="read-chapters"]').textContent(),
      overallProgress: await statsContainer.locator('[data-testid="overall-progress"]').textContent(),
      readingStreak: await statsContainer.locator('[data-testid="reading-streak"]').textContent(),
    };
  }

  async getSeriesBreakdown() {
    const breakdown = this.page.locator('[data-testid="series-breakdown"]');
    
    return {
      completed: await breakdown.locator('[data-testid="completed-series"]').textContent(),
      inProgress: await breakdown.locator('[data-testid="in-progress-series"]').textContent(),
      unread: await breakdown.locator('[data-testid="unread-series"]').textContent(),
    };
  }

  async getRecentReads() {
    const recentReads = this.page.locator('[data-testid="recent-reads"]');
    const items = recentReads.locator('[data-testid^="recent-read-"]');
    
    const count = await items.count();
    const reads = [];
    
    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      reads.push({
        series: await item.locator('.series-title').textContent(),
        chapter: await item.locator('.chapter-title').textContent(),
        date: await item.locator('.read-date').textContent(),
      });
    }
    
    return reads;
  }

  // Reader interactions
  async navigateReaderPage(direction: 'next' | 'prev') {
    if (direction === 'next') {
      await this.page.keyboard.press('ArrowRight');
    } else {
      await this.page.keyboard.press('ArrowLeft');
    }
    
    // Wait for page transition
    await this.page.waitForTimeout(100);
  }

  async getReaderProgress() {
    const progressText = this.page.locator('text=/\\d+ \\/ \\d+/');
    const progressPercentage = this.page.locator('text=/%/');
    
    return {
      pageInfo: await progressText.textContent(),
      percentage: await progressPercentage.textContent(),
    };
  }

  // Utility methods
  async waitForProgressUpdate() {
    // Wait a moment for progress calculations to complete
    await this.page.waitForTimeout(500);
  }

  async takeProgressScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/progress-${name}-${Date.now()}.png`,
      fullPage: true 
    });
  }

  // Accessibility helpers
  async checkProgressBarAccessibility(progressBar: any) {
    expect(await progressBar.getAttribute('role')).toBe('progressbar');
    expect(await progressBar.getAttribute('aria-valuenow')).toBeTruthy();
    expect(await progressBar.getAttribute('aria-valuemin')).toBe('0');
    expect(await progressBar.getAttribute('aria-valuemax')).toBeTruthy();
  }

  async checkMarkReadButtonAccessibility(button: any) {
    expect(await button.getAttribute('aria-label')).toMatch(/Mark as (read|unread)/);
    expect(await button.getAttribute('aria-pressed')).toMatch(/true|false/);
  }
}

test.describe('Reading Progress - Critical User Journeys', () => {
  let progressPage: ReadingProgressPage;

  test.beforeEach(async ({ page }) => {
    progressPage = new ReadingProgressPage(page);
    
    // Ensure we start with a clean state
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('KireMisu');
  });

  test.describe('Complete Reading Workflow', () => {
    test('user can complete entire reading workflow with progress tracking', async ({ page }) => {
      // Step 1: Navigate to library and verify initial state
      await progressPage.navigateToLibrary();
      
      const firstSeries = await progressPage.getSeriesCard(0);
      const initialProgress = await progressPage.getSeriesProgress(firstSeries);
      
      expect(initialProgress.isVisible).toBe(true);
      
      // Step 2: Enter series detail view
      await progressPage.clickSeriesCard(0);
      
      // Step 3: Find and mark an unread chapter
      const unreadChapter = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))').first();
      
      if (await unreadChapter.count() > 0) {
        const chapterProgress = await progressPage.getChapterProgress(unreadChapter);
        const initialText = chapterProgress.text;
        
        // Mark chapter as read
        await progressPage.toggleChapterReadStatus(unreadChapter);
        await progressPage.waitForProgressUpdate();
        
        // Verify chapter status updated
        const updatedChapterProgress = await progressPage.getChapterProgress(unreadChapter);
        expect(updatedChapterProgress.text).not.toBe(initialText);
        
        // Step 4: Return to library and verify series progress updated
        await progressPage.navigateToLibrary();
        
        const updatedSeries = await progressPage.getSeriesCard(0);
        const updatedProgress = await progressPage.getSeriesProgress(updatedSeries);
        
        expect(updatedProgress.percentage).not.toBe(initialProgress.percentage);
      }
    });

    test('user can read chapters in reader and see progress update', async ({ page }) => {
      await progressPage.navigateToLibrary();
      await progressPage.clickSeriesCard(0);
      
      // Find first chapter and open reader
      const firstChapter = await progressPage.getChapter(1);
      const readerLink = firstChapter.locator('a, button').first();
      await readerLink.click();
      
      // Wait for reader to load
      await page.waitForSelector('[data-testid="manga-reader"]');
      
      // Get initial progress
      const initialProgress = await progressPage.getReaderProgress();
      expect(initialProgress.pageInfo).toMatch(/\d+ \/ \d+/);
      
      // Navigate through several pages
      await progressPage.navigateReaderPage('next');
      await progressPage.navigateReaderPage('next');
      await progressPage.navigateReaderPage('next');
      
      // Verify progress updated
      const updatedProgress = await progressPage.getReaderProgress();
      expect(updatedProgress.pageInfo).not.toBe(initialProgress.pageInfo);
      
      // Return to series view and check chapter progress
      await page.goBack();
      await progressPage.waitForProgressUpdate();
      
      const chapterAfterReading = await progressPage.getChapter(1);
      const chapterProgress = await progressPage.getChapterProgress(chapterAfterReading);
      
      // Progress should be higher than 0%
      expect(chapterProgress.text).not.toBe('0%');
    });
  });

  test.describe('Dashboard Statistics Integration', () => {
    test('dashboard reflects accurate reading statistics', async ({ page }) => {
      // Get initial dashboard stats
      await progressPage.navigateToDashboard();
      const initialStats = await progressPage.getDashboardStats();
      const initialBreakdown = await progressPage.getSeriesBreakdown();
      
      // Mark some chapters as read
      await progressPage.navigateToLibrary();
      await progressPage.clickSeriesCard(0);
      
      // Toggle read status of first unread chapter
      const unreadChapter = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))').first();
      
      if (await unreadChapter.count() > 0) {
        await progressPage.toggleChapterReadStatus(unreadChapter);
        await progressPage.waitForProgressUpdate();
        
        // Return to dashboard and verify stats updated
        await progressPage.navigateToDashboard();
        const updatedStats = await progressPage.getDashboardStats();
        
        // Read chapters count should have increased
        const initialReadCount = parseInt(initialStats.readChapters || '0');
        const updatedReadCount = parseInt(updatedStats.readChapters || '0');
        
        expect(updatedReadCount).toBeGreaterThan(initialReadCount);
        
        // Overall progress should reflect the change
        const initialProgress = parseFloat(initialStats.overallProgress?.replace('%', '') || '0');
        const updatedProgress = parseFloat(updatedStats.overallProgress?.replace('%', '') || '0');
        
        expect(updatedProgress).toBeGreaterThanOrEqual(initialProgress);
      }
    });

    test('recent reading activity updates correctly', async ({ page }) => {
      await progressPage.navigateToDashboard();
      const initialRecentReads = await progressPage.getRecentReads();
      
      // Mark a chapter as read
      await progressPage.navigateToLibrary();
      await progressPage.clickSeriesCard(0);
      
      const unreadChapter = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))').first();
      
      if (await unreadChapter.count() > 0) {
        await progressPage.toggleChapterReadStatus(unreadChapter);
        await progressPage.waitForProgressUpdate();
        
        // Check recent activity updated
        await progressPage.navigateToDashboard();
        const updatedRecentReads = await progressPage.getRecentReads();
        
        // Should have new activity or updated timestamps
        expect(updatedRecentReads.length).toBeGreaterThanOrEqual(initialRecentReads.length);
      }
    });

    test('reading streak calculation works correctly', async ({ page }) => {
      await progressPage.navigateToDashboard();
      const stats = await progressPage.getDashboardStats();
      
      // Reading streak should be a valid number
      expect(stats.readingStreak).toMatch(/\d+ days?/);
      
      // Verify streak display is user-friendly
      const streakElement = page.locator('[data-testid="reading-streak"]');
      await expect(streakElement).toBeVisible();
    });
  });

  test.describe('Bulk Operations and Series Management', () => {
    test('mark all chapters in series as read', async ({ page }) => {
      await progressPage.navigateToLibrary();
      const initialSeries = await progressPage.getSeriesCard(0);
      const initialProgress = await progressPage.getSeriesProgress(initialSeries);
      
      await progressPage.clickSeriesCard(0);
      
      // Look for "Mark All Read" button if available
      const markAllButton = page.locator('text=/Mark all as read/i');
      
      if (await markAllButton.count() > 0) {
        await markAllButton.click();
        await progressPage.waitForProgressUpdate();
        
        // Verify all chapters show as read
        const chapters = page.locator('[data-testid*="chapter-"]');
        const chapterCount = await chapters.count();
        
        for (let i = 0; i < chapterCount; i++) {
          const chapter = chapters.nth(i);
          const progressText = await progressPage.getChapterProgress(chapter);
          expect(progressText.text).toContain('Complete');
        }
        
        // Return to library and verify series is 100%
        await progressPage.navigateToLibrary();
        const updatedSeries = await progressPage.getSeriesCard(0);
        const updatedProgress = await progressPage.getSeriesProgress(updatedSeries);
        
        expect(updatedProgress.percentage).toBe('100%');
      }
    });

    test('mark series as unread resets progress', async ({ page }) => {
      await progressPage.navigateToLibrary();
      await progressPage.clickSeriesCard(0);
      
      // Mark some chapters as read first
      const unreadChapters = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))');
      const chapterCount = Math.min(await unreadChapters.count(), 2);
      
      for (let i = 0; i < chapterCount; i++) {
        const chapter = unreadChapters.nth(i);
        await progressPage.toggleChapterReadStatus(chapter);
        await progressPage.waitForProgressUpdate();
      }
      
      // Now look for "Mark All Unread" or similar functionality
      const markAllUnreadButton = page.locator('text=/Mark all as unread/i');
      
      if (await markAllUnreadButton.count() > 0) {
        await markAllUnreadButton.click();
        await progressPage.waitForProgressUpdate();
        
        // Verify all chapters are unread
        const chapters = page.locator('[data-testid*="chapter-"]');
        const totalChapters = await chapters.count();
        
        for (let i = 0; i < totalChapters; i++) {
          const chapter = chapters.nth(i);
          const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
          expect(await markReadButton.textContent()).toMatch(/Mark Read/);
        }
      }
    });
  });
});

test.describe('Reading Progress - Performance and Reliability', () => {
  let progressPage: ReadingProgressPage;

  test.beforeEach(async ({ page }) => {
    progressPage = new ReadingProgressPage(page);
  });

  test('dashboard loads quickly with large library', async ({ page }) => {
    const startTime = Date.now();
    
    await progressPage.navigateToDashboard();
    
    // Dashboard should be interactive within 3 seconds
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000);
    
    // All key elements should be visible
    await expect(page.locator('[data-testid="dashboard-stats"]')).toBeVisible();
    await expect(page.locator('[data-testid="overall-progress"]')).toBeVisible();
    
    // No loading states should persist
    const loadingElements = page.locator('.loading, [data-testid*="loading"], .animate-spin');
    
    // Wait a moment for any async operations to complete
    await page.waitForTimeout(1000);
    
    const remainingLoading = await loadingElements.count();
    expect(remainingLoading).toBe(0);
  });

  test('progress updates are responsive and immediate', async ({ page }) => {
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    const chapter = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))').first();
    
    if (await chapter.count() > 0) {
      const startTime = Date.now();
      
      // Click mark read button
      const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
      await markReadButton.click();
      
      // Wait for visual feedback (button state change)
      await expect(markReadButton).not.toHaveText('Mark Read', { timeout: 2000 });
      
      const responseTime = Date.now() - startTime;
      
      // Should respond within 2 seconds
      expect(responseTime).toBeLessThan(2000);
    }
  });

  test('concurrent chapter marking works correctly', async ({ page, context }) => {
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    // Find multiple unread chapters
    const unreadChapters = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))');
    const chapterCount = Math.min(await unreadChapters.count(), 3);
    
    if (chapterCount > 1) {
      // Click multiple chapters rapidly
      const clicks = [];
      for (let i = 0; i < chapterCount; i++) {
        const chapter = unreadChapters.nth(i);
        const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
        clicks.push(markReadButton.click());
      }
      
      // Execute all clicks simultaneously
      await Promise.all(clicks);
      
      // Wait for all API calls to complete
      await progressPage.waitForProgressUpdate();
      
      // Verify all chapters were marked as read
      for (let i = 0; i < chapterCount; i++) {
        const chapter = unreadChapters.nth(i);
        const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
        await expect(markReadButton).not.toHaveText('Mark Read');
      }
    }
  });

  test('progress persists across browser sessions', async ({ page, context }) => {
    await progressPage.navigateToLibrary();
    const initialSeries = await progressPage.getSeriesCard(0);
    const initialProgress = await progressPage.getSeriesProgress(initialSeries);
    
    // Make a change
    await progressPage.clickSeriesCard(0);
    const unreadChapter = page.locator('[data-testid*="chapter-"]:has([data-testid="mark-read-button"]:has-text("Mark Read"))').first();
    
    if (await unreadChapter.count() > 0) {
      await progressPage.toggleChapterReadStatus(unreadChapter);
      await progressPage.waitForProgressUpdate();
      
      // Navigate back to library and note progress
      await progressPage.navigateToLibrary();
      const changedSeries = await progressPage.getSeriesCard(0);
      const changedProgress = await progressPage.getSeriesProgress(changedSeries);
      
      // Simulate browser refresh
      await page.reload();
      await page.waitForSelector('[data-testid="series-card"]');
      
      // Verify progress persisted
      const persistedSeries = await progressPage.getSeriesCard(0);
      const persistedProgress = await progressPage.getSeriesProgress(persistedSeries);
      
      expect(persistedProgress.percentage).toBe(changedProgress.percentage);
      expect(persistedProgress.percentage).not.toBe(initialProgress.percentage);
    }
  });
});

test.describe('Reading Progress - Accessibility Compliance', () => {
  let progressPage: ReadingProgressPage;

  test.beforeEach(async ({ page }) => {
    progressPage = new ReadingProgressPage(page);
  });

  test('progress bars have proper accessibility attributes', async ({ page }) => {
    await progressPage.navigateToLibrary();
    
    const seriesCard = await progressPage.getSeriesCard(0);
    const progressBar = seriesCard.locator('[data-testid="progress-bar"]');
    
    // Check ARIA attributes
    await progressPage.checkProgressBarAccessibility(progressBar);
  });

  test('mark read buttons are accessible', async ({ page }) => {
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    const markReadButton = page.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]').first();
    
    // Check accessibility attributes
    await progressPage.checkMarkReadButtonAccessibility(markReadButton);
  });

  test('keyboard navigation works throughout progress interface', async ({ page }) => {
    await progressPage.navigateToLibrary();
    
    // Tab through series cards
    await page.keyboard.press('Tab');
    const firstSeries = await progressPage.getSeriesCard(0);
    await expect(firstSeries).toBeFocused();
    
    // Enter series detail with keyboard
    await page.keyboard.press('Enter');
    await page.waitForSelector('[data-testid="chapter-list"]');
    
    // Tab to mark read button
    await page.keyboard.press('Tab');
    const markReadButton = page.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]').first();
    
    if (await markReadButton.isVisible()) {
      // Should be able to activate with Enter or Space
      await page.keyboard.press('Enter');
      
      // Wait for API response
      await progressPage.waitForProgressUpdate();
      
      // Verify interaction worked
      const buttonText = await markReadButton.textContent();
      expect(buttonText).not.toBe('Mark Read');
    }
  });

  test('screen reader announcements for progress changes', async ({ page }) => {
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    const chapter = page.locator('[data-testid*="chapter-"]').first();
    const progressBar = chapter.locator('[data-testid="progress-bar"], [data-testid="chapter-progress-bar"]');
    
    // Ensure progress bar has live region attributes for screen readers
    const ariaLive = await progressBar.getAttribute('aria-live');
    const ariaAtomic = await progressBar.getAttribute('aria-atomic');
    
    // Should have appropriate live region attributes or be contained within one
    if (!ariaLive) {
      const parentLiveRegion = await progressBar.locator('xpath=ancestor-or-self::*[@aria-live]').count();
      expect(parentLiveRegion).toBeGreaterThan(0);
    }
  });

  test('high contrast mode compatibility', async ({ page }) => {
    // Simulate high contrast mode by adding custom CSS
    await page.addStyleTag({
      content: `
        * {
          background-color: black !important;
          color: white !important;
          border-color: white !important;
        }
        [data-testid*="progress-bar"] {
          background-color: white !important;
          border: 2px solid white !important;
        }
      `
    });
    
    await progressPage.navigateToLibrary();
    
    const seriesCard = await progressPage.getSeriesCard(0);
    const progressBar = seriesCard.locator('[data-testid="progress-bar"]');
    
    // Verify progress bar is still visible in high contrast
    await expect(progressBar).toBeVisible();
    
    // Check that progress text is readable
    const progressText = seriesCard.locator('[data-testid="progress-percentage"]');
    if (await progressText.count() > 0) {
      await expect(progressText).toBeVisible();
    }
  });

  test('reduced motion preferences respected', async ({ page }) => {
    // Simulate reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    const chapter = page.locator('[data-testid*="chapter-"]').first();
    const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
    
    if (await markReadButton.count() > 0) {
      await markReadButton.click();
      await progressPage.waitForProgressUpdate();
      
      // Progress updates should still work, just without animations
      const progressText = await progressPage.getChapterProgress(chapter);
      expect(progressText.text).toBeTruthy();
    }
  });
});

test.describe('Reading Progress - Error Handling and Edge Cases', () => {
  let progressPage: ReadingProgressPage;

  test.beforeEach(async ({ page }) => {
    progressPage = new ReadingProgressPage(page);
  });

  test('handles API failures gracefully', async ({ page }) => {
    // Intercept and fail mark-read API calls
    await page.route('**/api/chapters/*/mark-read', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });
    
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    const chapter = page.locator('[data-testid*="chapter-"]').first();
    const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
    
    if (await markReadButton.count() > 0) {
      const originalText = await markReadButton.textContent();
      
      await markReadButton.click();
      await page.waitForTimeout(1000);
      
      // Button should return to original state on error
      const currentText = await markReadButton.textContent();
      expect(currentText).toBe(originalText);
    }
    
    // Clear the route intercept
    await page.unroute('**/api/chapters/*/mark-read');
  });

  test('handles empty library gracefully', async ({ page }) => {
    // Mock empty library response
    await page.route('**/api/series**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ series: [], total: 0 }),
      });
    });
    
    await progressPage.navigateToLibrary();
    
    // Should show appropriate empty state
    const emptyMessage = page.locator('text=/no series/i, text=/empty/i, text=/add some manga/i');
    await expect(emptyMessage).toBeVisible({ timeout: 5000 });
  });

  test('handles network disconnection during progress update', async ({ page, context }) => {
    await progressPage.navigateToLibrary();
    await progressPage.clickSeriesCard(0);
    
    const chapter = page.locator('[data-testid*="chapter-"]').first();
    const markReadButton = chapter.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
    
    if (await markReadButton.count() > 0) {
      // Simulate network disconnection
      await context.setOffline(true);
      
      await markReadButton.click();
      await page.waitForTimeout(2000);
      
      // Should show some indication of failure or retry
      const buttonText = await markReadButton.textContent();
      expect(buttonText).toBeTruthy();
      
      // Restore connection
      await context.setOffline(false);
    }
  });

  test('validates progress data consistency', async ({ page }) => {
    await progressPage.navigateToLibrary();
    const seriesCard = await progressPage.getSeriesCard(0);
    const seriesProgress = await progressPage.getSeriesProgress(seriesCard);
    
    await progressPage.clickSeriesCard(0);
    
    // Get all chapter progress values
    const chapters = page.locator('[data-testid*="chapter-"]');
    const chapterCount = await chapters.count();
    
    let totalProgress = 0;
    let readChapters = 0;
    
    for (let i = 0; i < chapterCount; i++) {
      const chapter = chapters.nth(i);
      const chapterProgress = await progressPage.getChapterProgress(chapter);
      
      if (chapterProgress.text === 'Complete') {
        readChapters++;
        totalProgress += 100;
      } else if (chapterProgress.text?.includes('%')) {
        const percentage = parseInt(chapterProgress.text.replace('%', ''));
        totalProgress += percentage;
        if (percentage > 0) {
          // Partially read chapters should contribute to in-progress count
        }
      }
    }
    
    // Series progress should roughly match individual chapter progress
    const expectedSeriesProgress = Math.round((readChapters / chapterCount) * 100);
    const actualSeriesProgress = parseInt(seriesProgress.percentage?.replace('%', '') || '0');
    
    // Allow some tolerance for different calculation methods
    const tolerance = 5; // 5% tolerance
    expect(Math.abs(actualSeriesProgress - expectedSeriesProgress)).toBeLessThanOrEqual(tolerance);
  });
});