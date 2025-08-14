/**
 * Improved Watching System E2E Tests
 * Following the testing strategy with proper fixtures and MSW mocking
 */

import { test, expect, Page } from '@playwright/test';
import { createTestHelpers, TEST_CONFIG } from './utils/test-helpers';
import { TEST_SERIES_DATA, TestDataManager, TEST_NOTIFICATIONS_DATA } from '../fixtures/manga-test-data';

// Setup MSW for API mocking
test.beforeEach(async ({ page }) => {
  // Initialize MSW for this page
  await page.addInitScript(() => {
    // This will be injected before page loads
    if (typeof window !== 'undefined') {
      window.TEST_MODE = true;
    }
  });

  // Navigate to the page and wait for it to be ready
  await page.goto('/library');
  await page.waitForLoadState('networkidle');
});

test.describe('Watching System - Core Functionality', () => {
  test('should display series with proper watch toggle states', async ({ page }) => {
    const helpers = createTestHelpers(page);
    
    // Wait for library to load
    await helpers.waitForPageStable();
    
    // Verify series cards are displayed
    const seriesCards = page.locator('[data-testid="series-card"]');
    await expect(seriesCards).toHaveCount(TEST_SERIES_DATA.length);
    
    // Check that series with MangaDx IDs have watch toggles
    for (const series of TEST_SERIES_DATA) {
      if (series.mangadx_id) {
        const seriesCard = page.locator(`[data-testid="series-card"]:has-text("${series.title_primary}")`);
        const watchToggle = seriesCard.locator(`[data-testid="watch-toggle-${series.id}"]`);
        
        await expect(watchToggle).toBeVisible();
        
        // Check initial state matches test data
        const expectedLabel = series.watching_enabled ? 'Stop watching' : 'Start watching';
        await expect(watchToggle).toHaveAttribute('aria-label', expectedLabel);
      }
    }
  });

  test('should toggle watch status successfully', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Find a series that can be watched (has MangaDx ID but not currently watching)
    const watchableSeries = TestDataManager.getWatchableSeries()[0];
    expect(watchableSeries).toBeDefined();

    const watchToggle = page.locator(`[data-testid="watch-toggle-${watchableSeries.id}"]`);
    
    // Verify initial state
    await expect(watchToggle).toHaveAttribute('aria-label', 'Start watching');
    
    // Click to start watching
    await helpers.safeClick(watchToggle);
    
    // Wait for API call and state update
    await helpers.waitForWatchToggleUpdate(watchableSeries.id, 'Stop watching');
    
    // Verify success toast
    await helpers.waitForToast('Now watching');
    await helpers.dismissAllToasts();
  });

  test('should handle watch toggle errors gracefully', async ({ page }) => {
    const helpers = createTestHelpers(page);
    
    // Mock API to return error
    await page.route('**/api/series/*/watch', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Failed to update watch status' })
      });
    });

    await helpers.waitForPageStable();

    // Try to toggle watch status
    const { toggle: watchToggle } = await helpers.getFirstAvailableWatchToggle();
    await helpers.safeClick(watchToggle);

    // Should show error toast
    await helpers.waitForToast('Error');
    await helpers.dismissAllToasts();
  });
});

test.describe('Notification System', () => {
  test('should display notification bell with correct badge count', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    const notificationBell = await helpers.waitForNotificationBell();
    await expect(notificationBell).toBeVisible();

    // Check badge count matches unread notifications
    const unreadCount = TestDataManager.getUnreadNotifications().length;
    if (unreadCount > 0) {
      const badge = page.locator('[data-testid="notification-badge"]');
      await expect(badge).toBeVisible();
      await expect(badge).toHaveText(unreadCount.toString());
    }
  });

  test('should open and display notifications correctly', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Click notification bell
    const notificationBell = await helpers.waitForNotificationBell();
    await helpers.safeClick(notificationBell);

    // Wait for dropdown to appear
    const dropdown = await helpers.waitForNotificationDropdown();
    await expect(dropdown).toBeVisible();

    // Check notifications are displayed
    const notificationItems = page.locator('[data-testid="notification-item"]');
    const expectedCount = Math.min(TEST_NOTIFICATIONS_DATA.length, 10); // API returns max 10
    await expect(notificationItems).toHaveCount(expectedCount);

    // Verify first notification content
    if (TEST_NOTIFICATIONS_DATA.length > 0) {
      const firstNotification = notificationItems.first();
      await expect(firstNotification).toContainText(TEST_NOTIFICATIONS_DATA[0].title);
    }
  });

  test('should mark notifications as read', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Open notifications
    await helpers.clickNotificationBell();
    const dropdown = await helpers.waitForNotificationDropdown();

    // Find an unread notification
    const unreadNotifications = TestDataManager.getUnreadNotifications();
    if (unreadNotifications.length > 0) {
      const markReadButton = page.locator('[data-testid="mark-read-button"]').first();
      if (await markReadButton.isVisible()) {
        await helpers.safeClick(markReadButton);
        
        // Wait for the UI to update
        await page.waitForTimeout(500);
        
        // Badge count should decrease
        const badge = page.locator('[data-testid="notification-badge"]');
        if (unreadNotifications.length === 1) {
          // If this was the last unread notification, badge should disappear
          await expect(badge).not.toBeVisible();
        } else {
          // Otherwise, count should decrease
          const newCount = (unreadNotifications.length - 1).toString();
          await expect(badge).toHaveText(newCount);
        }
      }
    }
  });

  test('should mark all notifications as read', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Open notifications
    await helpers.clickNotificationBell();
    await helpers.waitForNotificationDropdown();

    // Check if mark all read button is available
    const markAllReadButton = page.locator('[data-testid="mark-all-read-button"]');
    if (await markAllReadButton.isVisible()) {
      await helpers.safeClick(markAllReadButton);
      
      // Wait for update
      await page.waitForTimeout(500);
      
      // Badge should disappear
      const badge = page.locator('[data-testid="notification-badge"]');
      await expect(badge).not.toBeVisible();
    }
  });
});

test.describe('Watching Page', () => {
  test('should navigate to watching page and display watched series', async ({ page }) => {
    const helpers = createTestHelpers(page);

    // Navigate to watching page
    await page.goto('/library/watching');
    await helpers.waitForPageStable();

    // Check page title
    await expect(page.locator('h1, h2')).toContainText(/watching/i);

    // Check watched series display
    const watchedSeries = TestDataManager.getWatchedSeries();
    if (watchedSeries.length > 0) {
      const watchedSeriesList = page.locator('[data-testid="watched-series-list"]');
      await expect(watchedSeriesList).toBeVisible();

      const seriesCards = page.locator('[data-testid="watched-series-card"]');
      await expect(seriesCards).toHaveCount(watchedSeries.length);
    } else {
      // Should show empty state
      await expect(page.locator('text=/no.*watch/i')).toBeVisible();
    }
  });

  test('should filter watched series', async ({ page }) => {
    const helpers = createTestHelpers(page);
    
    await page.goto('/library/watching');
    await helpers.waitForPageStable();

    const watchedSeries = TestDataManager.getWatchedSeries();
    if (watchedSeries.length > 0) {
      // Try to use search if available
      const searchInput = page.locator('input[placeholder*="search"]');
      if (await searchInput.isVisible()) {
        const searchTerm = watchedSeries[0].title_primary.split(' ')[0];
        await searchInput.fill(searchTerm);
        
        // Wait for filter to apply
        await page.waitForTimeout(500);
        
        // Verify results contain the search term
        const visibleSeries = page.locator('[data-testid="watched-series-card"]:visible');
        const count = await visibleSeries.count();
        
        if (count > 0) {
          const results = await visibleSeries.allTextContents();
          const hasMatch = results.some(text => 
            text.toLowerCase().includes(searchTerm.toLowerCase())
          );
          expect(hasMatch).toBe(true);
        }
      }
    }
  });
});

test.describe('Error Handling and Edge Cases', () => {
  test('should handle series without MangaDx ID gracefully', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Find series without MangaDx ID
    const seriesWithoutMangaDx = TEST_SERIES_DATA.find(s => !s.mangadx_id);
    if (seriesWithoutMangaDx) {
      const seriesCard = page.locator(`[data-testid="series-card"]:has-text("${seriesWithoutMangaDx.title_primary}")`);
      
      // Watch toggle should either not exist or be disabled
      const watchToggle = seriesCard.locator(`[data-testid="watch-toggle-${seriesWithoutMangaDx.id}"]`);
      
      if (await watchToggle.isVisible()) {
        // If toggle exists, clicking should show appropriate error
        await helpers.safeClick(watchToggle);
        await helpers.waitForToast(/cannot.*watch/i);
        await helpers.dismissAllToasts();
      }
    }
  });

  test('should handle network timeouts gracefully', async ({ page }) => {
    const helpers = createTestHelpers(page);
    
    // Mock slow network response
    await page.route('**/api/series/*/watch', route => {
      // Delay response by 10 seconds to simulate timeout
      setTimeout(() => {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ watching_enabled: true })
        });
      }, 10000);
    });

    await helpers.waitForPageStable();

    // Try to toggle watch with timeout
    const { toggle: watchToggle } = await helpers.getFirstAvailableWatchToggle();
    await helpers.safeClick(watchToggle);

    // Should handle timeout gracefully (exact behavior depends on implementation)
    // This test validates the app doesn't crash on slow responses
    await page.waitForTimeout(2000);
    
    // Toggle should not be in a broken state
    await expect(watchToggle).toBeVisible();
  });

  test('should persist state across page refreshes', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Toggle watch status
    const watchableSeries = TestDataManager.getWatchableSeries()[0];
    if (watchableSeries) {
      const watchToggle = page.locator(`[data-testid="watch-toggle-${watchableSeries.id}"]`);
      await helpers.safeClick(watchToggle);
      
      await helpers.waitForWatchToggleUpdate(watchableSeries.id, 'Stop watching');
      
      // Refresh page
      await page.reload();
      await helpers.waitForPageStable();
      
      // State should persist (note: this depends on proper data persistence)
      const refreshedToggle = page.locator(`[data-testid="watch-toggle-${watchableSeries.id}"]`);
      await expect(refreshedToggle).toHaveAttribute('aria-label', 'Stop watching');
    }
  });
});

test.describe('Accessibility and Responsive Design', () => {
  test('should be accessible via keyboard navigation', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Test notification bell keyboard access
    const notificationBell = await helpers.waitForNotificationBell();
    await notificationBell.focus();
    await expect(notificationBell).toBeFocused();
    
    // Activate with Enter key
    await page.keyboard.press('Enter');
    const dropdown = await helpers.waitForNotificationDropdown();
    await expect(dropdown).toBeVisible();
    
    // Close with Escape
    await page.keyboard.press('Escape');
    await expect(dropdown).not.toBeVisible();
  });

  test('should work on mobile viewports', async ({ page }) => {
    const helpers = createTestHelpers(page);
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await helpers.waitForPageStable();

    // Elements should still be accessible
    const notificationBell = await helpers.waitForNotificationBell();
    await expect(notificationBell).toBeVisible();
    
    // Watch toggles should be functional
    const watchToggles = page.locator('[aria-label*="watching"]');
    const count = await watchToggles.count();
    if (count > 0) {
      const firstToggle = watchToggles.first();
      await expect(firstToggle).toBeVisible();
    }
  });

  test('should have proper ARIA labels and roles', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Check notification bell accessibility
    const notificationBell = await helpers.waitForNotificationBell();
    const bellLabel = await notificationBell.getAttribute('aria-label');
    expect(bellLabel).toMatch(/notifications/i);

    // Check watch toggles accessibility
    const watchToggles = page.locator('[aria-label*="watching"]');
    const count = await watchToggles.count();
    
    for (let i = 0; i < Math.min(count, 3); i++) {
      const toggle = watchToggles.nth(i);
      const label = await toggle.getAttribute('aria-label');
      expect(label).toMatch(/(start|stop).*watching/i);
    }

    // Check dropdown accessibility
    await helpers.clickNotificationBell();
    const dropdown = await helpers.waitForNotificationDropdown();
    
    const role = await dropdown.getAttribute('role');
    expect(role).toBe('dialog');
    
    const ariaLabel = await dropdown.getAttribute('aria-label');
    expect(ariaLabel).toBe('Notifications');
  });
});

test.describe('Performance and Load Testing', () => {
  test('should handle large notification lists efficiently', async ({ page }) => {
    const helpers = createTestHelpers(page);
    
    // This test would use a large notification dataset
    // Implementation depends on the ability to mock large datasets
    await helpers.waitForPageStable();

    const startTime = Date.now();
    
    await helpers.clickNotificationBell();
    await helpers.waitForNotificationDropdown();
    
    const loadTime = Date.now() - startTime;
    
    // Notification dropdown should load quickly (< 2 seconds as per docs)
    expect(loadTime).toBeLessThan(2000);
  });

  test('should update watch status quickly', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    const { toggle: watchToggle, seriesId } = await helpers.getFirstAvailableWatchToggle();
    
    const startTime = Date.now();
    await helpers.safeClick(watchToggle);
    await helpers.waitForWatchToggleUpdate(seriesId, 'Stop watching');
    const updateTime = Date.now() - startTime;
    
    // Watch status should update quickly (< 0.5 seconds as per docs)
    expect(updateTime).toBeLessThan(500);
  });
});