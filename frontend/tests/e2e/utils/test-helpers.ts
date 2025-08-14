/**
 * E2E Test Helper Utilities for KireMisu
 * Addresses timing and async operation issues in watching system tests
 */

import { Page, Locator, expect } from '@playwright/test';

export class TestHelpers {
  constructor(private page: Page) {}

  /**
   * Wait for notification dropdown to appear and be fully rendered
   */
  async waitForNotificationDropdown(timeout = 10000): Promise<Locator> {
    // Wait for the dropdown element to be present in DOM
    await this.page.waitForSelector('[data-testid="notification-dropdown"]', { 
      state: 'visible',
      timeout 
    });
    
    // Additional wait for portal mounting animation to complete
    await this.page.waitForTimeout(300);
    
    return this.page.locator('[data-testid="notification-dropdown"]');
  }

  /**
   * Wait for portal components to mount properly
   */
  async waitForPortalMount(selector: string, timeout = 5000): Promise<void> {
    await this.page.waitForSelector(selector, { state: 'visible', timeout });
    // Allow time for React portal to fully mount and style to apply
    await this.page.waitForTimeout(250);
  }

  /**
   * Wait for polling cycle to complete (useful for notification updates)
   */
  async waitForPollingCycle(cycles = 1): Promise<void> {
    // KireMisu polling interval is typically 30 seconds, but in tests we want shorter waits
    const pollInterval = 1000; // 1 second for tests
    await this.page.waitForTimeout(pollInterval * cycles);
  }

  /**
   * Wait for watch toggle state to update
   */
  async waitForWatchToggleUpdate(seriesId: string, expectedLabel: string, timeout = 10000): Promise<void> {
    const toggle = this.page.locator(`[data-testid="watch-toggle-${seriesId}"]`);
    await expect(toggle).toHaveAttribute('aria-label', expectedLabel, { timeout });
  }

  /**
   * Wait for toast notification to appear and be visible
   */
  async waitForToast(messagePattern: string | RegExp, timeout = 10000): Promise<Locator> {
    const toastSelector = typeof messagePattern === 'string' 
      ? `.toast:has-text("${messagePattern}")` 
      : `.toast`;
    
    await this.page.waitForSelector(toastSelector, { 
      state: 'visible',
      timeout 
    });

    const toast = this.page.locator(toastSelector).first();
    
    if (typeof messagePattern !== 'string') {
      const toastText = await toast.textContent();
      if (toastText && !messagePattern.test(toastText)) {
        throw new Error(`Toast text "${toastText}" does not match pattern ${messagePattern}`);
      }
    }
    
    return toast;
  }

  /**
   * Dismiss any visible toast notifications
   */
  async dismissAllToasts(): Promise<void> {
    const toasts = this.page.locator('.toast');
    const count = await toasts.count();
    
    for (let i = 0; i < count; i++) {
      const toast = toasts.nth(i);
      if (await toast.isVisible()) {
        // Try clicking the toast to dismiss
        await toast.click();
        await this.page.waitForTimeout(100);
      }
    }
    
    // Wait for all toasts to disappear
    await this.page.waitForSelector('.toast', { state: 'hidden', timeout: 5000 }).catch(() => {
      // Ignore timeout - toasts may have already disappeared
    });
  }

  /**
   * Wait for series card to be fully loaded and interactive
   */
  async waitForSeriesCard(seriesTitle: string): Promise<Locator> {
    const card = this.page.locator(`[data-testid="series-card"]:has-text("${seriesTitle}")`);
    await expect(card).toBeVisible();
    
    // Wait for any loading states to complete
    await this.page.waitForTimeout(200);
    
    return card;
  }

  /**
   * Wait for notification bell to be ready for interaction
   */
  async waitForNotificationBell(): Promise<Locator> {
    const bell = this.page.locator('[data-testid="notification-bell"]');
    await expect(bell).toBeVisible();
    
    // Ensure bell is not in a loading state
    await expect(bell).not.toHaveAttribute('disabled');
    
    return bell;
  }

  /**
   * Click the notification bell to open/close the dropdown
   */
  async clickNotificationBell(): Promise<void> {
    const bell = await this.waitForNotificationBell();
    await this.safeClick(bell);
    // Allow time for dropdown animation
    await this.page.waitForTimeout(300);
  }

  /**
   * Wait for API request to complete before proceeding
   */
  async waitForApiResponse(urlPattern: string | RegExp, timeout = 10000): Promise<void> {
    await this.page.waitForResponse(
      response => {
        const url = response.url();
        if (typeof urlPattern === 'string') {
          return url.includes(urlPattern);
        }
        return urlPattern.test(url);
      },
      { timeout }
    );
  }

  /**
   * Ensure page is in a stable state before testing
   */
  async waitForPageStable(): Promise<void> {
    // Wait for DOM content to be loaded instead of networkidle
    await this.page.waitForLoadState('domcontentloaded');
    
    // Try to wait for networkidle with shorter timeout, but don't fail if it doesn't reach it
    try {
      await this.page.waitForLoadState('networkidle', { timeout: 3000 });
    } catch (e) {
      console.log('Network not idle, continuing with test...');
    }
    
    // Wait for any animations to complete
    await this.page.waitForTimeout(500);
    
    // Ensure no loading spinners are present
    await this.page.waitForSelector('.animate-spin', { state: 'hidden', timeout: 5000 }).catch(() => {
      // Ignore timeout - loading spinners may not be present
    });
  }

  /**
   * Get the first available watch toggle (with retries for timing issues)
   */
  async getFirstAvailableWatchToggle(maxRetries = 3): Promise<{ toggle: Locator; seriesId: string }> {
    let lastError: Error | null = null;
    
    for (let retry = 0; retry < maxRetries; retry++) {
      try {
        await this.waitForPageStable();
        
        // Find all series cards
        const seriesCards = this.page.locator('[data-testid="series-card"]');
        const count = await seriesCards.count();
        
        if (count === 0) {
          throw new Error('No series cards found');
        }
        
        // Try to find the first card with a watch toggle
        for (let i = 0; i < count; i++) {
          const card = seriesCards.nth(i);
          const watchToggle = card.locator('[aria-label*="watching"]');
          
          if (await watchToggle.isVisible()) {
            // Extract series ID from the watch toggle's data-testid
            const testId = await watchToggle.getAttribute('data-testid');
            const seriesId = testId?.replace('watch-toggle-', '') || `series-${i}`;
            
            return { toggle: watchToggle, seriesId };
          }
        }
        
        throw new Error('No watch toggles found in series cards');
      } catch (error) {
        lastError = error as Error;
        if (retry < maxRetries - 1) {
          await this.page.waitForTimeout(1000); // Wait before retry
        }
      }
    }
    
    throw lastError || new Error('Failed to find available watch toggle');
  }

  /**
   * Safely click an element with retry logic
   */
  async safeClick(locator: Locator, options: { timeout?: number; retries?: number } = {}): Promise<void> {
    const { timeout = 5000, retries = 3 } = options;
    let lastError: Error | null = null;
    
    for (let i = 0; i < retries; i++) {
      try {
        await expect(locator).toBeVisible({ timeout });
        await expect(locator).toBeEnabled({ timeout });
        await locator.click();
        return;
      } catch (error) {
        lastError = error as Error;
        if (i < retries - 1) {
          await this.page.waitForTimeout(500);
        }
      }
    }
    
    throw lastError || new Error('Failed to click element after retries');
  }
}

/**
 * Test configuration for consistent behavior across environments
 */
export const TEST_CONFIG = {
  // Disable polling in tests to avoid timing conflicts
  polling: { enabled: false },
  
  // Disable WebSocket in tests to use HTTP-only mode
  websocket: { enabled: false },
  
  // Disable animations for more predictable tests
  animations: { disabled: true },
  
  // Shorter timeouts for faster test execution
  timeouts: {
    short: 2000,
    medium: 5000,
    long: 10000
  }
};

/**
 * Helper function to create TestHelpers instance
 */
export function createTestHelpers(page: Page): TestHelpers {
  return new TestHelpers(page);
}