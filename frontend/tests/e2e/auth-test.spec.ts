import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should show login form for unauthenticated user', async ({ page }) => {
    console.log('Starting auth test...');
    
    // Listen for console messages and network requests
    page.on('console', msg => {
      console.log(`CONSOLE ${msg.type()}: ${msg.text()}`);
    });

    page.on('request', request => {
      if (request.url().includes('api')) {
        console.log(`REQUEST: ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('api')) {
        console.log(`RESPONSE: ${response.status()} ${response.url()}`);
      }
    });
    
    await page.goto('/');
    
    // Wait a reasonable time for auth to initialize
    await page.waitForTimeout(3000);
    
    // Check what's visible after auth initialization
    const hasLoadingSpinner = await page.locator('.animate-spin').count() > 0;
    const hasLoginForm = await page.locator('[data-testid="login-form"]').count() > 0;
    const hasErrorMessage = await page.locator('text=Error').count() > 0;
    
    console.log('Page state after 3s:', {
      hasLoadingSpinner,
      hasLoginForm,
      hasErrorMessage,
      url: page.url()
    });
    
    // If still loading after 3s, something is wrong
    if (hasLoadingSpinner) {
      console.log('Still showing loading spinner after 3s - authentication not resolving');
      
      // Check if there are any JavaScript errors
      const pageContent = await page.content();
      console.log('Page title:', await page.title());
      
      // Force fail if still loading
      expect(hasLoadingSpinner).toBe(false);
    }
    
    // Should show login form for unauthenticated user
    expect(hasLoginForm).toBe(true);
  });

  test('should login successfully', async ({ page }) => {
    await page.goto('/');
    
    // Wait for login form to appear
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible({ timeout: 10000 });
    
    // Fill in credentials
    await page.fill('[data-testid="username-input"]', 'admin');
    await page.fill('[data-testid="password-input"]', 'KireMisu2025!');
    
    // Click login
    await page.click('[data-testid="login-button"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    // Should not show login form anymore
    await expect(page.locator('[data-testid="login-form"]')).not.toBeVisible();
    
    // Should show dashboard content (or at least not be stuck on loading)
    await expect(page.locator('.animate-spin')).not.toBeVisible({ timeout: 5000 });
  });
});