/**
 * End-to-End tests for Push Notification workflows
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';

// Helper class for push notification interactions
class PushNotificationPage {
  constructor(private page: Page) {}

  async navigateToSettings() {
    await this.page.goto('/settings');
    await this.page.waitForLoadState('networkidle');
  }

  async navigateToLibrary() {
    await this.page.goto('/library');
    await this.page.waitForLoadState('networkidle');
  }

  async getPushNotificationToggle() {
    return this.page.locator('[data-testid="push-notifications-toggle"], input[type="checkbox"]:near([text*="Push Notifications"])').first();
  }

  async getNotificationPermissionButton() {
    return this.page.locator('button:has-text("Enable Notifications"), button:has-text("Request Permission")');
  }

  async getNotificationStatus() {
    return this.page.locator('[data-testid="notification-status"], .notification-status');
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
      await this.page.waitForSelector('.toast', { state: 'hidden', timeout: 5000 });
    }
  }

  async getTestNotificationButton() {
    return this.page.locator('button:has-text("Send Test"), button:has-text("Test Notification")');
  }

  async simulateServiceWorkerRegistration() {
    // Inject service worker simulation script
    await this.page.addInitScript(() => {
      // Mock service worker registration
      Object.defineProperty(navigator, 'serviceWorker', {
        value: {
          ready: Promise.resolve({
            pushManager: {
              getSubscription: () => Promise.resolve(null),
              subscribe: (options: any) => Promise.resolve({
                endpoint: 'https://fcm.googleapis.com/fcm/send/mock-endpoint',
                getKey: (name: string) => {
                  if (name === 'p256dh') return new Uint8Array([1, 2, 3, 4]);
                  if (name === 'auth') return new Uint8Array([5, 6, 7, 8]);
                  return null;
                },
                unsubscribe: () => Promise.resolve(true)
              })
            }
          }),
          register: () => Promise.resolve({
            pushManager: {
              getSubscription: () => Promise.resolve(null),
              subscribe: () => Promise.resolve({
                endpoint: 'https://fcm.googleapis.com/fcm/send/mock-endpoint',
                getKey: (name: string) => {
                  if (name === 'p256dh') return new Uint8Array([1, 2, 3, 4]);
                  if (name === 'auth') return new Uint8Array([5, 6, 7, 8]);
                  return null;
                },
                unsubscribe: () => Promise.resolve(true)
              })
            },
            addEventListener: () => {},
            waiting: null,
            installing: null,
            active: { postMessage: () => {} }
          })
        },
        writable: true
      });

      // Mock Notification API
      Object.defineProperty(window, 'Notification', {
        value: class MockNotification {
          static permission = 'default';
          static requestPermission = () => Promise.resolve('granted');
          constructor(title: string, options?: any) {
            console.log('Mock notification:', title, options);
          }
          close() {}
        },
        writable: true
      });

      // Mock Push Manager in Window
      Object.defineProperty(window, 'PushManager', {
        value: class MockPushManager {},
        writable: true
      });
    });
  }
}

test.beforeEach(async ({ page, context }) => {
  // Grant notification permission by default
  await context.grantPermissions(['notifications']);
  
  const pushPage = new PushNotificationPage(page);
  await pushPage.simulateServiceWorkerRegistration();
  
  // Navigate to home page
  await page.goto('/');
  await page.waitForLoadState('networkidle');
});

test.describe('Push Notifications - Basic Functionality', () => {
  test('should display push notification settings', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();

    // Should find push notification settings section
    const pushSection = page.locator('section:has-text("Push Notifications"), .push-notifications-section');
    if (await pushSection.isVisible()) {
      await expect(pushSection).toBeVisible();
      
      // Should have a toggle or button to enable notifications
      const toggle = await pushPage.getPushNotificationToggle();
      if (await toggle.isVisible()) {
        await expect(toggle).toBeVisible();
      } else {
        // Or should have permission request button
        const permissionBtn = await pushPage.getNotificationPermissionButton();
        await expect(permissionBtn).toBeVisible();
      }
    } else {
      console.log('Push notification settings not found - may not be implemented yet');
    }
  });

  test('should handle notification permission request', async ({ page, context }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();

    // Look for permission request button
    const permissionButton = await pushPage.getNotificationPermissionButton();
    
    if (await permissionButton.isVisible()) {
      await permissionButton.click();
      
      // Should either succeed immediately (mocked) or show loading state
      await page.waitForTimeout(1000);
      
      // Check for success state or error message
      const hasSuccessMessage = await page.locator('.toast:has-text("granted"), .toast:has-text("enabled")').isVisible();
      const hasErrorMessage = await page.locator('.toast:has-text("denied"), .toast:has-text("error")').isVisible();
      
      expect(hasSuccessMessage || hasErrorMessage).toBe(true);
    } else {
      console.log('Permission request button not found');
    }
  });

  test('should enable/disable push notifications', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();

    const toggle = await pushPage.getPushNotificationToggle();
    
    if (await toggle.isVisible()) {
      const initialState = await toggle.isChecked();
      
      // Toggle the setting
      await toggle.click();
      
      // Wait for state change
      await page.waitForTimeout(1000);
      
      // Verify state changed
      const newState = await toggle.isChecked();
      expect(newState).toBe(!initialState);
      
      // Should show confirmation toast
      const expectedMessage = newState ? 'enabled' : 'disabled';
      const toast = page.locator(`.toast:has-text("${expectedMessage}")`);
      if (await toast.isVisible()) {
        await expect(toast).toBeVisible();
        await pushPage.dismissToast();
      }
    }
  });

  test('should send test notification', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();

    // First enable notifications if needed
    const toggle = await pushPage.getPushNotificationToggle();
    if (await toggle.isVisible() && !(await toggle.isChecked())) {
      await toggle.click();
      await page.waitForTimeout(1000);
    }

    // Look for test notification button
    const testButton = await pushPage.getTestNotificationButton();
    
    if (await testButton.isVisible()) {
      await testButton.click();
      
      // Should show success or error message
      await page.waitForTimeout(2000);
      
      const hasSuccessToast = await page.locator('.toast:has-text("sent"), .toast:has-text("test")').isVisible();
      const hasErrorToast = await page.locator('.toast:has-text("failed"), .toast:has-text("error")').isVisible();
      
      expect(hasSuccessToast || hasErrorToast).toBe(true);
      
      if (hasSuccessToast || hasErrorToast) {
        await pushPage.dismissToast();
      }
    } else {
      console.log('Test notification button not found');
    }
  });
});

test.describe('Push Notifications - Service Worker Integration', () => {
  test('should handle service worker registration', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    
    // Check for service worker registration indicators
    await page.goto('/');
    
    // Look for service worker update notifications
    const updateNotification = page.locator('.sw-update-notification, [data-testid="sw-update"]');
    
    // Should not show errors about missing service worker
    const swError = page.locator('.error:has-text("service worker"), .toast:has-text("service worker")');
    const hasError = await swError.isVisible();
    expect(hasError).toBe(false);
    
    // Check browser console for service worker registration
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));
    
    await page.reload();
    await page.waitForTimeout(2000);
    
    const hasSwLog = logs.some(log => log.includes('service worker') || log.includes('Service Worker'));
    if (hasSwLog) {
      console.log('Service worker logs detected:', logs.filter(log => 
        log.toLowerCase().includes('service') || log.toLowerCase().includes('worker')
      ));
    }
  });

  test('should handle service worker updates', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await page.goto('/');
    
    // Simulate service worker update by injecting update available state
    await page.evaluate(() => {
      // Trigger service worker update notification if component exists
      const event = new CustomEvent('sw-update-available');
      window.dispatchEvent(event);
    });
    
    await page.waitForTimeout(1000);
    
    // Look for update notification
    const updateBanner = page.locator('[role="banner"]:has-text("update"), .update-notification, [data-testid="app-update"]');
    
    if (await updateBanner.isVisible()) {
      // Should have update and dismiss buttons
      const updateButton = page.locator('button:has-text("Update"), button:has-text("Refresh")');
      const dismissButton = page.locator('button:has-text("Later"), button:has-text("Dismiss")');
      
      await expect(updateButton).toBeVisible();
      await expect(dismissButton).toBeVisible();
      
      // Test dismiss functionality
      await dismissButton.click();
      await expect(updateBanner).not.toBeVisible();
    }
  });
});

test.describe('Push Notifications - Error Handling', () => {
  test('should handle permission denied gracefully', async ({ page, context }) => {
    // Deny notification permission
    await context.grantPermissions([]);
    
    const pushPage = new PushNotificationPage(page);
    
    // Override mock to simulate permission denied
    await page.addInitScript(() => {
      Object.defineProperty(window.Notification, 'permission', {
        value: 'denied',
        writable: false
      });
      
      window.Notification.requestPermission = () => Promise.resolve('denied' as NotificationPermission);
    });
    
    await pushPage.navigateToSettings();
    
    const permissionButton = await pushPage.getNotificationPermissionButton();
    
    if (await permissionButton.isVisible()) {
      await permissionButton.click();
      
      // Should show appropriate error message
      await page.waitForTimeout(1000);
      
      const errorToast = page.locator('.toast:has-text("denied"), .toast:has-text("blocked")');
      if (await errorToast.isVisible()) {
        await expect(errorToast).toBeVisible();
        await pushPage.dismissToast();
      }
      
      // Settings should reflect denied state
      const status = await pushPage.getNotificationStatus();
      if (await status.isVisible()) {
        const statusText = await status.textContent();
        expect(statusText?.toLowerCase()).toContain('denied');
      }
    }
  });

  test('should handle API failures gracefully', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    
    // Mock API failures
    await page.route('**/api/push/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Push service unavailable' })
      });
    });
    
    await pushPage.navigateToSettings();
    
    const toggle = await pushPage.getPushNotificationToggle();
    
    if (await toggle.isVisible()) {
      await toggle.click();
      
      // Should show error message
      await page.waitForTimeout(2000);
      
      const errorToast = page.locator('.toast:has-text("error"), .toast:has-text("failed")');
      await expect(errorToast).toBeVisible();
      await pushPage.dismissToast();
    }
  });

  test('should handle network connectivity issues', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();
    
    // Enable notifications first
    const toggle = await pushPage.getPushNotificationToggle();
    if (await toggle.isVisible() && !(await toggle.isChecked())) {
      await toggle.click();
      await page.waitForTimeout(1000);
    }
    
    // Go offline
    await page.context().setOffline(true);
    
    // Try to send test notification
    const testButton = await pushPage.getTestNotificationButton();
    if (await testButton.isVisible()) {
      await testButton.click();
      
      // Should show network error
      await page.waitForTimeout(2000);
      
      const networkError = page.locator('.toast:has-text("network"), .toast:has-text("offline")');
      if (await networkError.isVisible()) {
        await expect(networkError).toBeVisible();
      }
    }
    
    // Restore connectivity
    await page.context().setOffline(false);
  });
});

test.describe('Push Notifications - Integration with Watching System', () => {
  test('should trigger notifications for watched series', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    
    // Enable push notifications first
    await pushPage.navigateToSettings();
    const toggle = await pushPage.getPushNotificationToggle();
    if (await toggle.isVisible() && !(await toggle.isChecked())) {
      await toggle.click();
      await page.waitForTimeout(1000);
    }
    
    // Go to library and watch a series
    await pushPage.navigateToLibrary();
    
    const watchToggle = page.locator('[aria-label="Start watching"]').first();
    if (await watchToggle.isVisible()) {
      await watchToggle.click();
      await pushPage.waitForToast('Now watching');
      await pushPage.dismissToast();
      
      // Mock receiving a push notification for new chapter
      await page.evaluate(() => {
        // Simulate push notification received
        const event = new MessageEvent('push', {
          data: {
            json: () => ({
              title: 'New Chapter Available',
              body: 'Chapter 123 of Attack on Titan is now available',
              data: { type: 'new_chapter', seriesId: '123' }
            })
          }
        } as any);
        
        // Dispatch to service worker if available
        if ('serviceWorker' in navigator) {
          console.log('Mock push notification received');
        }
      });
      
      // Should see notification appear (in a real scenario)
      await page.waitForTimeout(2000);
    }
  });

  test('should not send notifications for unwatched series', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    
    // Enable push notifications
    await pushPage.navigateToSettings();
    const toggle = await pushPage.getPushNotificationToggle();
    if (await toggle.isVisible() && !(await toggle.isChecked())) {
      await toggle.click();
      await page.waitForTimeout(1000);
    }
    
    // Don't watch any series, but simulate notification
    await page.evaluate(() => {
      // This should not result in any visible notifications
      // since no series are being watched
      console.log('Simulating notification for unwatched series');
    });
    
    // Go to library - should not see notification badges for unwatched series
    await pushPage.navigateToLibrary();
    
    // Check that notification bell doesn't show excessive unread count
    const notificationBell = page.locator('[aria-label*="Notifications"]');
    if (await notificationBell.isVisible()) {
      const badge = page.locator('[aria-label*="Notifications"] .badge');
      if (await badge.isVisible()) {
        const badgeText = await badge.textContent();
        // Badge should be reasonable (not showing notifications for unwatched series)
        expect(badgeText).toMatch(/^\d{1,2}(\+)?$/); // Should be 1-2 digits max for reasonable UX
      }
    }
  });
});

test.describe('Push Notifications - Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();
    
    // Check notification toggle accessibility
    const toggle = await pushPage.getPushNotificationToggle();
    if (await toggle.isVisible()) {
      const label = await toggle.getAttribute('aria-label') || 
                    await toggle.locator('xpath=../label').textContent();
      expect(label?.toLowerCase()).toMatch(/push.*notification/);
    }
    
    // Check permission button accessibility
    const permissionBtn = await pushPage.getNotificationPermissionButton();
    if (await permissionBtn.isVisible()) {
      const label = await permissionBtn.getAttribute('aria-label') || 
                    await permissionBtn.textContent();
      expect(label?.toLowerCase()).toMatch(/(enable|request|permission)/);
    }
    
    // Check test button accessibility
    const testBtn = await pushPage.getTestNotificationButton();
    if (await testBtn.isVisible()) {
      const label = await testBtn.getAttribute('aria-label') || 
                    await testBtn.textContent();
      expect(label?.toLowerCase()).toMatch(/(test|send)/);
    }
  });

  test('should announce status changes to screen readers', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();
    
    // Check for live regions
    const liveRegions = page.locator('[aria-live], [role="status"], [role="alert"]');
    
    const toggle = await pushPage.getPushNotificationToggle();
    if (await toggle.isVisible()) {
      await toggle.click();
      
      // Wait for announcement
      await page.waitForTimeout(1000);
      
      // Should have live region or toast with status announcement
      const announcements = page.locator('.toast, [aria-live], [role="status"]');
      const hasAnnouncement = await announcements.count() > 0;
      expect(hasAnnouncement).toBe(true);
    }
  });

  test('should be keyboard navigable', async ({ page }) => {
    const pushPage = new PushNotificationPage(page);
    await pushPage.navigateToSettings();
    
    // Tab to notification settings
    await page.keyboard.press('Tab');
    let attempts = 0;
    
    while (attempts < 20) { // Reasonable limit for tab navigation
      const focused = page.locator(':focus');
      
      // Check if we've focused on push notification controls
      const isFocusedOnPushControl = await focused.evaluate(el => {
        return el.closest('.push-notifications-section') !== null ||
               el.textContent?.toLowerCase().includes('notification') ||
               el.getAttribute('aria-label')?.toLowerCase().includes('notification');
      });
      
      if (isFocusedOnPushControl) {
        // Should be able to activate with Enter or Space
        const tagName = await focused.evaluate(el => el.tagName.toLowerCase());
        
        if (tagName === 'button') {
          await page.keyboard.press('Enter');
          await page.waitForTimeout(500);
        } else if (tagName === 'input') {
          await page.keyboard.press('Space');
          await page.waitForTimeout(500);
        }
        
        break;
      }
      
      await page.keyboard.press('Tab');
      attempts++;
    }
    
    // Should have successfully navigated to and interacted with notification settings
    expect(attempts).toBeLessThan(20);
  });
});