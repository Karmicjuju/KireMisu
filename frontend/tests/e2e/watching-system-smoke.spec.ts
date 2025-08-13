/**
 * Watching System Smoke Tests
 * Following the testing strategy: Quick validation of core functionality
 */

import { test, expect } from '@playwright/test';
import { createTestHelpers } from './utils/test-helpers';
import { TestDataManager } from '../fixtures/manga-test-data';

test.describe('Watching System - Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/library');
    await page.waitForLoadState('networkidle');
  });

  test('should load library page with series cards', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    // Verify basic page elements
    await expect(page.locator('h1, h2')).toBeVisible();
    
    // Verify series cards are present
    const seriesCards = page.locator('[data-testid="series-card"]');
    await expect(seriesCards.first()).toBeVisible();
  });

  test('should display notification bell', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    const notificationBell = await helpers.waitForNotificationBell();
    await expect(notificationBell).toBeVisible();
  });

  test('should have functional watch toggles', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    const watchToggles = page.locator('[aria-label*="watching"]');
    const count = await watchToggles.count();
    
    if (count > 0) {
      const firstToggle = watchToggles.first();
      await expect(firstToggle).toBeVisible();
      await expect(firstToggle).toBeEnabled();
    }
  });

  test('should open notification dropdown', async ({ page }) => {
    const helpers = createTestHelpers(page);
    await helpers.waitForPageStable();

    await helpers.clickNotificationBell();
    const dropdown = await helpers.waitForNotificationDropdown();
    await expect(dropdown).toBeVisible();
  });

  test('should navigate to watching page', async ({ page }) => {
    const helpers = createTestHelpers(page);

    await page.goto('/library/watching');
    await helpers.waitForPageStable();

    await expect(page.locator('h1, h2')).toContainText(/watching/i);
  });
});