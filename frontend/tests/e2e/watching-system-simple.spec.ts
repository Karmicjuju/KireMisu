/**
 * Simple E2E tests for watching system
 * Direct authentication and minimal setup
 */

import { test, expect } from '@playwright/test';

// Get test credentials from environment variables
const getTestCredentials = () => {
  const username = process.env.E2E_TEST_USERNAME || process.env.KIREMISU_TEST_USERNAME;
  const password = process.env.E2E_TEST_PASSWORD || process.env.KIREMISU_TEST_PASSWORD;
  
  if (!username) {
    throw new Error(
      'E2E_TEST_USERNAME environment variable is required. ' +
      'Set it before running tests: E2E_TEST_USERNAME=your_username npm run test:e2e'
    );
  }
  
  if (!password) {
    throw new Error(
      'E2E_TEST_PASSWORD environment variable is required. ' +
      'Set it before running tests: E2E_TEST_PASSWORD=your_password npm run test:e2e'
    );
  }
  
  console.log(`🔐 Using test credentials for user: ${username}`);
  return { username, password };
};

// Simple auth helper
async function simpleAuth(page: any) {
  console.log('🔐 Attempting simple authentication...');
  
  await page.goto('/library');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);
  
  // Check if we're on login page
  const currentUrl = page.url();
  console.log(`Current URL: ${currentUrl}`);
  
  if (currentUrl.includes('/login') || await page.locator('input[type="password"]').count() > 0) {
    console.log('Login required - attempting to authenticate');
    
    // Get credentials from environment
    const { username, password } = getTestCredentials();
    
    // Simple login attempt
    const usernameInput = page.locator('input[type="text"], input[name="username"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    const submitButton = page.locator('button[type="submit"], button:has-text("Sign in")').first();
    
    if (await usernameInput.count() > 0) {
      await usernameInput.fill(username);
      await passwordInput.fill(password);
      await submitButton.click();
      
      // Wait for potential navigation
      await page.waitForTimeout(5000);
    }
  }
  
  console.log(`✅ Authentication completed - final URL: ${page.url()}`);
}

test.describe('Watching System - Direct Tests', () => {
  test('should authenticate and access library', async ({ page }) => {
    await simpleAuth(page);
    
    // Should not be on login page
    expect(page.url()).not.toContain('/login');
    
    // Should have some content
    const body = await page.locator('body').textContent();
    expect(body).toBeTruthy();
    expect(body!.length).toBeGreaterThan(100);
    
    console.log('✅ Library page accessible');
  });

  test('should find watching system components', async ({ page }) => {
    await simpleAuth(page);
    
    let foundComponents = 0;
    
    // Look for notification bell
    const notificationBellSelectors = [
      '[data-testid="notification-bell"]',
      'button[aria-label*="notification"]',
      '[class*="bell"]'
    ];
    
    for (const selector of notificationBellSelectors) {
      const elements = await page.locator(selector).count();
      if (elements > 0) {
        console.log(`✅ Found notification bell with selector: ${selector}`);
        foundComponents++;
        break;
      }
    }
    
    // Look for series cards
    const seriesCardSelectors = [
      '[data-testid="series-card"]',
      '.series-card',
      'article'
    ];
    
    for (const selector of seriesCardSelectors) {
      const elements = await page.locator(selector).count();
      if (elements > 0) {
        console.log(`✅ Found ${elements} series card(s) with selector: ${selector}`);
        foundComponents++;
        break;
      }
    }
    
    // Look for watch toggles
    const watchToggleSelectors = [
      '[data-testid*="watch-toggle"]',
      '[aria-label*="watch"]',
      'button:has-text("Watch")',
      'button:has-text("Watching")'
    ];
    
    for (const selector of watchToggleSelectors) {
      const elements = await page.locator(selector).count();
      if (elements > 0) {
        console.log(`✅ Found ${elements} watch toggle(s) with selector: ${selector}`);
        foundComponents++;
        break;
      }
    }
    
    console.log(`Found ${foundComponents}/3 expected component types`);
    
    // Take screenshot for debugging
    await page.screenshot({ path: 'test-results/watching-components-debug.png', fullPage: true });
    
    // Should find at least some components
    expect(foundComponents).toBeGreaterThan(0);
  });

  test('should navigate to watching page', async ({ page }) => {
    await simpleAuth(page);
    
    // Navigate to watching page
    await page.goto('/library/watching');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    
    // Verify URL
    expect(page.url()).toContain('/watching');
    
    // Should have content
    const body = await page.locator('body').textContent();
    expect(body).toBeTruthy();
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/watching-page-debug.png', fullPage: true });
    
    console.log('✅ Watching page navigation successful');
  });

  test('should test basic interactions', async ({ page }) => {
    await simpleAuth(page);
    
    let interactionTests = 0;
    
    // Test 1: Try clicking any button (basic interactivity)
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    
    if (buttonCount > 0) {
      console.log(`Found ${buttonCount} buttons`);
      
      // Try clicking the first button
      try {
        await buttons.first().click();
        await page.waitForTimeout(1000);
        interactionTests++;
        console.log('✅ Button click successful');
      } catch (e) {
        console.log('Button click failed:', e.message);
      }
    }
    
    // Test 2: Test navigation between pages
    const currentUrl = page.url();
    await page.goto('/library/watching');
    await page.waitForTimeout(1000);
    
    if (page.url() !== currentUrl) {
      interactionTests++;
      console.log('✅ Navigation between pages works');
    }
    
    // Test 3: Test form interactions if available
    const inputs = await page.locator('input').count();
    if (inputs > 0) {
      try {
        await page.locator('input').first().click();
        interactionTests++;
        console.log('✅ Input interaction works');
      } catch (e) {
        console.log('Input interaction failed');
      }
    }
    
    console.log(`Completed ${interactionTests} interaction tests`);
    expect(interactionTests).toBeGreaterThan(0);
  });

  test('should handle API responses', async ({ page }) => {
    await simpleAuth(page);
    
    // Monitor network requests
    const apiRequests: string[] = [];
    
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push(request.url());
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        console.log(`API Response: ${response.status()} ${response.url()}`);
      }
    });
    
    // Trigger some navigation to generate API calls
    await page.goto('/library');
    await page.waitForTimeout(2000);
    
    await page.goto('/library/watching');
    await page.waitForTimeout(2000);
    
    console.log(`Captured ${apiRequests.length} API requests`);
    apiRequests.forEach(url => console.log(`  - ${url}`));
    
    // Should have some API activity
    expect(apiRequests.length).toBeGreaterThan(0);
  });

  test('should be responsive to different viewport sizes', async ({ page }) => {
    await simpleAuth(page);
    
    // Test desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/library');
    await page.waitForTimeout(1000);
    
    let viewportTests = 0;
    
    // Check if page renders at desktop size
    const desktopBody = await page.locator('body').boundingBox();
    if (desktopBody && desktopBody.width > 1000) {
      viewportTests++;
      console.log('✅ Desktop viewport renders correctly');
    }
    
    // Test tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);
    
    const tabletBody = await page.locator('body').boundingBox();
    if (tabletBody && tabletBody.width <= 800) {
      viewportTests++;
      console.log('✅ Tablet viewport renders correctly');
    }
    
    // Test mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);
    
    const mobileBody = await page.locator('body').boundingBox();
    if (mobileBody && mobileBody.width <= 400) {
      viewportTests++;
      console.log('✅ Mobile viewport renders correctly');
    }
    
    console.log(`Passed ${viewportTests}/3 viewport tests`);
    expect(viewportTests).toBeGreaterThan(0);
  });
});

test.describe('Watching System - Error Handling', () => {
  test('should handle page not found', async ({ page }) => {
    await simpleAuth(page);
    
    // Navigate to non-existent page
    await page.goto('/library/nonexistent');
    await page.waitForLoadState('domcontentloaded');
    
    // Should handle gracefully
    const body = await page.locator('body').textContent();
    const has404 = body?.includes('404') || body?.includes('not found');
    const hasRedirect = !page.url().includes('/nonexistent');
    
    console.log(`404 handling: ${has404 ? 'Shows 404' : hasRedirect ? 'Redirects' : 'Other'}`);
    expect(has404 || hasRedirect).toBe(true);
  });

  test('should handle network issues', async ({ page }) => {
    await simpleAuth(page);
    
    // FIRST load the page while online
    await page.goto('/library/watching');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);
    
    // Verify page loaded successfully
    const onlineBody = await page.locator('body').textContent();
    expect(onlineBody).toBeTruthy();
    
    // THEN simulate network failure
    await page.context().setOffline(true);
    
    try {
      // Test that existing page content is still accessible
      const offlineBody = await page.locator('body').textContent();
      expect(offlineBody).toBeTruthy();
      expect(offlineBody).toBe(onlineBody); // Should be the same content
      
      // Test that interactive elements still exist (even if they don't work)
      const buttons = await page.locator('button').count();
      expect(buttons).toBeGreaterThan(0);
      
      // Test that we can still interact with cached content
      const heading = page.locator('h1, h2, h3').first();
      if (await heading.count() > 0) {
        await expect(heading).toBeVisible();
      }
      
      console.log('✅ Cached content remains accessible while offline');
      
      // Test that new navigation attempts show appropriate behavior
      const navigationPromise = page.goto('/library/other-page');
      
      // This should either:
      // 1. Fail with network error (expected)
      // 2. Show cached content
      // 3. Show offline indicator
      
      try {
        await navigationPromise;
        console.log('Navigation succeeded - may have cached content');
      } catch (error) {
        if (error.message.includes('ERR_INTERNET_DISCONNECTED')) {
          console.log('✅ Navigation properly fails when offline (expected behavior)');
        } else {
          throw error; // Re-throw unexpected errors
        }
      }
      
      console.log('✅ Handles offline state gracefully');
    } finally {
      // Restore network
      await page.context().setOffline(false);
    }
  });
});