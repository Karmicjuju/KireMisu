/**
 * Minimal Smoke Test to Validate Framework
 * Basic connectivity and framework validation
 */

import { test, expect } from '@playwright/test';

test.describe('Framework Validation', () => {
  test('should connect to application', async ({ page }) => {
    // Basic connectivity test
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Should load without errors
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have working test selectors', async ({ page }) => {
    await page.goto('http://localhost:3000/library');
    await page.waitForLoadState('networkidle');
    
    // Check if our data-testid selectors are present
    const hasSeriesCards = await page.locator('[data-testid="series-card"]').count() > 0;
    const hasNotificationBell = await page.locator('[data-testid="notification-bell"]').isVisible();
    
    // At least one of these should be present in a working app
    expect(hasSeriesCards || hasNotificationBell).toBe(true);
  });
});