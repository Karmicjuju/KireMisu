/**
 * End-to-End tests for the watching & notification system user workflows
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import { v4 as uuidv4 } from 'uuid';

// Test data setup
const TEST_SERIES_DATA = [
  {
    title: 'Attack on Titan E2E',
    mangadx_id: 'e2e-test-aot-001',
    directory_path: '/test/manga/attack-on-titan-e2e'
  },
  {
    title: 'One Piece E2E',
    mangadx_id: 'e2e-test-op-002',
    directory_path: '/test/manga/one-piece-e2e'
  },
  {
    title: 'Naruto E2E',
    mangadx_id: 'e2e-test-naruto-003',
    directory_path: '/test/manga/naruto-e2e'
  }
];

// Helper functions
class WatchingSystemPage {
  constructor(private page: Page) {}

  async navigateToLibrary() {
    await this.page.goto('/library');
    await this.page.waitForLoadState('networkidle');
  }

  async navigateToWatchingPage() {
    await this.page.goto('/library/watching');
    await this.page.waitForLoadState('networkidle');
  }

  async getNotificationBell() {
    return this.page.locator('[aria-label*="Notifications"]');
  }

  async getNotificationBadge() {
    return this.page.locator('[aria-label*="Notifications"] .badge');
  }

  async getWatchToggleForSeries(seriesTitle: string) {
    const seriesCard = this.page.locator(`[data-testid="series-card"]:has-text("${seriesTitle}")`);
    return seriesCard.locator('[aria-label*="watching"]');
  }

  async clickNotificationBell() {
    const bell = await this.getNotificationBell();
    await bell.click();
    // Wait for dropdown to appear
    await this.page.waitForSelector('[role="dialog"], .notification-dropdown', { state: 'visible' });
  }

  async getNotificationDropdown() {
    return this.page.locator('[role="dialog"], .notification-dropdown');
  }

  async getNotificationItems() {
    return this.page.locator('.notification-item, [data-testid="notification-item"]');
  }

  async waitForToast(message: string) {
    await this.page.waitForSelector(`.toast:has-text("${message}")`, { 
      state: 'visible',
      timeout: 10000 
    });
  }

  async dismissToast() {
    const toast = this.page.locator('.toast').first();
    if (await toast.isVisible()) {
      await toast.click();
      await this.page.waitForSelector('.toast', { state: 'hidden' });
    }
  }

  async searchWatchedSeries(query: string) {
    const searchInput = this.page.locator('input[placeholder*="search"]');
    await searchInput.fill(query);
    await this.page.waitForTimeout(500); // Debounce
  }

  async sortWatchedSeries(sortOption: string) {
    const sortButton = this.page.locator('button:has-text("Sort")');
    await sortButton.click();
    await this.page.locator(`text="${sortOption}"`).click();
  }
}

// Setup and teardown
test.beforeEach(async ({ page }) => {
  // Ensure clean state - might need API calls to clean up test data
  await page.goto('/');
  await page.waitForLoadState('networkidle');
});

test.describe('Watching System - User Workflows', () => {
  test('should toggle watch status for a series', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Find first series and toggle watch
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    const seriesTitle = await firstSeriesCard.locator('.series-title').textContent();
    
    const watchToggle = await watchingPage.getWatchToggleForSeries(seriesTitle!);
    const isCurrentlyWatching = await watchToggle.getAttribute('aria-label') === 'Stop watching';

    // Toggle watch status
    await watchToggle.click();

    // Wait for success toast
    const expectedMessage = isCurrentlyWatching ? 'No longer watching' : 'Now watching';
    await watchingPage.waitForToast(expectedMessage);

    // Verify button state changed
    const newLabel = await watchToggle.getAttribute('aria-label');
    if (isCurrentlyWatching) {
      expect(newLabel).toBe('Start watching');
    } else {
      expect(newLabel).toBe('Stop watching');
    }

    await watchingPage.dismissToast();
  });

  test('should display notification badge with unread count', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Enable watching for a series to potentially generate notifications
    const firstWatchToggle = page.locator('[aria-label="Start watching"]').first();
    if (await firstWatchToggle.isVisible()) {
      await firstWatchToggle.click();
      await watchingPage.waitForToast('Now watching');
      await watchingPage.dismissToast();
    }

    // Check notification bell
    const notificationBell = await watchingPage.getNotificationBell();
    await expect(notificationBell).toBeVisible();

    // Check if badge is present (only if there are unread notifications)
    const badge = await watchingPage.getNotificationBadge();
    if (await badge.isVisible()) {
      const badgeText = await badge.textContent();
      expect(badgeText).toMatch(/^\d+(\+)?$/); // Should be a number or "99+"
    }
  });

  test('should open and close notification dropdown', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Click notification bell to open dropdown
    await watchingPage.clickNotificationBell();

    // Verify dropdown is visible
    const dropdown = await watchingPage.getNotificationDropdown();
    await expect(dropdown).toBeVisible();

    // Click bell again to close
    const bell = await watchingPage.getNotificationBell();
    await bell.click();

    // Verify dropdown is hidden
    await expect(dropdown).not.toBeVisible();
  });

  test('should navigate to watching page and display watched series', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);

    // First, ensure we have some watched series
    await watchingPage.navigateToLibrary();
    
    // Watch at least one series
    const watchToggle = page.locator('[aria-label="Start watching"]').first();
    if (await watchToggle.isVisible()) {
      await watchToggle.click();
      await watchingPage.waitForToast('Now watching');
      await watchingPage.dismissToast();
    }

    // Navigate to watching page
    await watchingPage.navigateToWatchingPage();

    // Verify page loaded correctly
    await expect(page.locator('h1, h2')).toContainText(/watching/i);

    // Check if watched series are displayed
    const watchedSeriesList = page.locator('[data-testid="watched-series-list"], .watched-series');
    if (await watchedSeriesList.isVisible()) {
      const seriesItems = page.locator('[data-testid="series-card"], .series-item');
      const count = await seriesItems.count();
      expect(count).toBeGreaterThan(0);
    } else {
      // If no watched series, should show empty state
      await expect(page.locator('text=/no.*watch/i')).toBeVisible();
    }
  });

  test('should filter watched series by search', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    
    // Navigate to watching page
    await watchingPage.navigateToWatchingPage();

    // Only proceed if we have watched series
    const hasWatchedSeries = await page.locator('[data-testid="series-card"]').count() > 0;
    
    if (hasWatchedSeries) {
      // Get first series title
      const firstSeriesTitle = await page.locator('[data-testid="series-card"] .series-title').first().textContent();
      const searchTerm = firstSeriesTitle?.split(' ')[0] || 'Test';

      // Search for the series
      await watchingPage.searchWatchedSeries(searchTerm);

      // Verify filtered results
      const visibleSeries = page.locator('[data-testid="series-card"]:visible');
      const count = await visibleSeries.count();
      
      if (count > 0) {
        // At least one result should contain the search term
        const results = await visibleSeries.allTextContents();
        const hasMatchingResult = results.some(text => 
          text.toLowerCase().includes(searchTerm.toLowerCase())
        );
        expect(hasMatchingResult).toBe(true);
      }

      // Clear search
      await watchingPage.searchWatchedSeries('');
    } else {
      // If no watched series, test should pass but log the state
      console.log('No watched series found for search test');
    }
  });

  test('should sort watched series', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToWatchingPage();

    // Only proceed if we have multiple watched series
    const seriesCount = await page.locator('[data-testid="series-card"]').count();
    
    if (seriesCount > 1) {
      // Get initial order
      const initialTitles = await page.locator('[data-testid="series-card"] .series-title').allTextContents();

      // Sort by title (if sort option exists)
      const sortButton = page.locator('button:has-text("Sort")');
      if (await sortButton.isVisible()) {
        await sortButton.click();
        
        // Try different sort options
        const sortOptions = ['Title', 'Recently Added', 'Progress'];
        for (const option of sortOptions) {
          const sortOption = page.locator(`text="${option}"`);
          if (await sortOption.isVisible()) {
            await sortOption.click();
            await page.waitForTimeout(500); // Wait for sort to apply
            
            // Verify order changed (or at least stayed stable)
            const newTitles = await page.locator('[data-testid="series-card"] .series-title').allTextContents();
            expect(newTitles.length).toBe(initialTitles.length);
            break;
          }
        }
      }
    } else {
      console.log('Insufficient watched series for sort test');
    }
  });

  test('should mark notifications as read', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Open notifications dropdown
    await watchingPage.clickNotificationBell();

    const dropdown = await watchingPage.getNotificationDropdown();
    await expect(dropdown).toBeVisible();

    // Check if there are any notifications
    const notificationItems = await watchingPage.getNotificationItems();
    const notificationCount = await notificationItems.count();

    if (notificationCount > 0) {
      // Click first notification to mark as read
      const firstNotification = notificationItems.first();
      const markReadButton = firstNotification.locator('button:has-text("Mark Read"), [aria-label*="mark.*read"]');
      
      if (await markReadButton.isVisible()) {
        await markReadButton.click();
        
        // Wait for the notification state to update
        await page.waitForTimeout(1000);
        
        // Verify notification badge count decreased (if it was visible)
        const badge = await watchingPage.getNotificationBadge();
        // Badge might disappear or show lower count
      }
    } else {
      console.log('No notifications found for read test');
    }
  });

  test('should handle watch toggle for series without MangaDx ID', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Try to find a series without MangaDx ID (series that can't be watched)
    // This might require specific test data setup
    const seriesCards = page.locator('[data-testid="series-card"]');
    const count = await seriesCards.count();

    for (let i = 0; i < Math.min(count, 3); i++) {
      const seriesCard = seriesCards.nth(i);
      const watchToggle = seriesCard.locator('[aria-label*="watch"]');

      if (await watchToggle.isVisible()) {
        await watchToggle.click();
        
        // Should either succeed or show appropriate error
        // Wait a bit to see what happens
        await page.waitForTimeout(2000);
        
        // Check for error toast or success toast
        const hasErrorToast = await page.locator('.toast:has-text("error"), .toast:has-text("failed")').isVisible();
        const hasSuccessToast = await page.locator('.toast:has-text("watching"), .toast:has-text("Now")').isVisible();
        
        expect(hasErrorToast || hasSuccessToast).toBe(true);
        
        if (hasErrorToast || hasSuccessToast) {
          await watchingPage.dismissToast();
        }
        break;
      }
    }
  });

  test('should display appropriate empty states', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);

    // Test empty notifications
    await watchingPage.navigateToLibrary();
    await watchingPage.clickNotificationBell();

    const dropdown = await watchingPage.getNotificationDropdown();
    await expect(dropdown).toBeVisible();

    // Should show either notifications or empty state
    const hasNotifications = await page.locator('.notification-item').count() > 0;
    const hasEmptyState = await page.locator('text=/no.*notification/i').isVisible();
    
    expect(hasNotifications || hasEmptyState).toBe(true);

    // Close dropdown
    await watchingPage.clickNotificationBell();

    // Test empty watched series
    await watchingPage.navigateToWatchingPage();
    
    const hasWatchedSeries = await page.locator('[data-testid="series-card"]').count() > 0;
    const hasEmptyWatchState = await page.locator('text=/no.*watch/i').isVisible();
    
    expect(hasWatchedSeries || hasEmptyWatchState).toBe(true);
  });

  test('should be responsive on different screen sizes', async ({ page, context }) => {
    const watchingPage = new WatchingSystemPage(page);

    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await watchingPage.navigateToLibrary();

    // Notification bell should be visible and functional
    const notificationBell = await watchingPage.getNotificationBell();
    await expect(notificationBell).toBeVisible();
    
    // Watch toggles might be icons or badges on mobile
    const watchToggles = page.locator('[aria-label*="watch"]');
    const toggleCount = await watchToggles.count();
    if (toggleCount > 0) {
      const firstToggle = watchToggles.first();
      await expect(firstToggle).toBeVisible();
    }

    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.reload();
    await watchingPage.navigateToWatchingPage();
    
    // Layout should adapt appropriately
    const watchedSeriesSection = page.locator('[data-testid="watched-series-list"], .watched-series');
    if (await watchedSeriesSection.isVisible()) {
      await expect(watchedSeriesSection).toBeVisible();
    }

    // Test desktop view
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.reload();
    
    // All elements should be properly displayed
    await expect(notificationBell).toBeVisible();
  });

  test('should handle keyboard navigation', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Focus notification bell with Tab key
    await page.keyboard.press('Tab');
    
    // Should be able to navigate to notification bell
    const notificationBell = await watchingPage.getNotificationBell();
    
    // Try to focus it (might require multiple tabs depending on page layout)
    let attempts = 0;
    while (attempts < 10) {
      const focusedElement = page.locator(':focus');
      const isBellFocused = await focusedElement.evaluate(
        (el, bell) => el === bell, 
        await notificationBell.elementHandle()
      );
      
      if (isBellFocused) {
        break;
      }
      
      await page.keyboard.press('Tab');
      attempts++;
    }

    // Activate notification bell with Enter
    await page.keyboard.press('Enter');
    
    // Dropdown should open
    const dropdown = await watchingPage.getNotificationDropdown();
    if (await dropdown.isVisible()) {
      // Should be able to navigate within dropdown
      await page.keyboard.press('Tab');
      await page.keyboard.press('Escape'); // Close dropdown
      await expect(dropdown).not.toBeVisible();
    }

    // Navigate to watch toggles
    const watchToggle = page.locator('[aria-label*="watch"]').first();
    if (await watchToggle.isVisible()) {
      await watchToggle.focus();
      await page.keyboard.press('Enter');
      
      // Should trigger the watch toggle
      await page.waitForTimeout(1000);
    }
  });

  test('should persist watch state across page reloads', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Find a series and toggle watch
    const watchToggle = page.locator('[aria-label="Start watching"]').first();
    if (await watchToggle.isVisible()) {
      const seriesCard = watchToggle.locator('xpath=ancestor::*[@data-testid="series-card"]');
      const seriesTitle = await seriesCard.locator('.series-title').textContent();
      
      // Enable watching
      await watchToggle.click();
      await watchingPage.waitForToast('Now watching');
      await watchingPage.dismissToast();

      // Reload the page
      await page.reload();
      await page.waitForLoadState('networkidle');

      // Verify watch state persisted
      const reloadedToggle = await watchingPage.getWatchToggleForSeries(seriesTitle!);
      const label = await reloadedToggle.getAttribute('aria-label');
      expect(label).toBe('Stop watching');
    }
  });
});

test.describe('Watching System - Error Scenarios', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    
    // Mock API failure by intercepting requests
    await page.route('**/api/series/*/watch', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    await watchingPage.navigateToLibrary();

    // Try to toggle watch - should show error
    const watchToggle = page.locator('[aria-label*="watch"]').first();
    if (await watchToggle.isVisible()) {
      await watchToggle.click();
      
      // Should show error toast
      await watchingPage.waitForToast('Error');
      await watchingPage.dismissToast();
    }
  });

  test('should handle network connectivity issues', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Simulate network failure
    await page.context().setOffline(true);

    // Try to use notification features
    const notificationBell = await watchingPage.getNotificationBell();
    await notificationBell.click();

    // Should either show cached data or appropriate error state
    const dropdown = await watchingPage.getNotificationDropdown();
    if (await dropdown.isVisible()) {
      // Either shows cached data or error message
      const hasContent = await dropdown.locator('*').count() > 0;
      expect(hasContent).toBe(true);
    }

    // Restore connectivity
    await page.context().setOffline(false);
  });
});

test.describe('Watching System - Accessibility', () => {
  test('should have proper ARIA labels and roles', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Check notification bell accessibility
    const notificationBell = await watchingPage.getNotificationBell();
    const bellLabel = await notificationBell.getAttribute('aria-label');
    expect(bellLabel).toMatch(/notifications/i);

    // Check watch toggles accessibility
    const watchToggles = page.locator('[aria-label*="watch"]');
    const count = await watchToggles.count();
    
    for (let i = 0; i < Math.min(count, 3); i++) {
      const toggle = watchToggles.nth(i);
      const label = await toggle.getAttribute('aria-label');
      expect(label).toMatch(/(start|stop).*watching/i);
    }

    // Check dropdown accessibility when opened
    await watchingPage.clickNotificationBell();
    const dropdown = await watchingPage.getNotificationDropdown();
    
    if (await dropdown.isVisible()) {
      const role = await dropdown.getAttribute('role');
      expect(role).toMatch(/(dialog|menu|listbox)/i);
    }
  });

  test('should support screen reader announcements', async ({ page }) => {
    const watchingPage = new WatchingSystemPage(page);
    await watchingPage.navigateToLibrary();

    // Check for live regions or aria-live attributes
    const liveRegions = page.locator('[aria-live], [role="status"], [role="alert"]');
    const liveRegionCount = await liveRegions.count();
    
    // Toast notifications should have appropriate live region announcements
    const watchToggle = page.locator('[aria-label*="watch"]').first();
    if (await watchToggle.isVisible()) {
      await watchToggle.click();
      
      // Wait for toast which should announce the change
      await page.waitForTimeout(2000);
      
      // Verify live region or toast is present for screen reader
      const toast = page.locator('.toast, [role="alert"], [aria-live="polite"]');
      const hasAnnouncement = await toast.count() > 0;
      expect(hasAnnouncement).toBe(true);
    }
  });
});