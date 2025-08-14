import { test, expect } from '@playwright/test';

test.describe('Simple Authentication Test', () => {
  test('debug authentication flow', async ({ page }) => {
    console.log('Starting simple auth test...');
    
    // Listen for console messages
    page.on('console', msg => {
      console.log(`CONSOLE ${msg.type()}: ${msg.text()}`);
    });

    page.on('request', request => {
      if (request.url().includes('api') || request.url().includes('localhost:8000')) {
        console.log(`REQUEST: ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('api') || response.url().includes('localhost:8000')) {
        console.log(`RESPONSE: ${response.status()} ${response.url()}`);
      }
    });
    
    console.log('Navigating to homepage...');
    await page.goto('http://localhost:3000');
    
    console.log('Waiting 5 seconds to see what happens...');
    await page.waitForTimeout(5000);
    
    // Check current page state
    const bodyText = await page.locator('body').textContent();
    const hasSpinner = await page.locator('.animate-spin').count() > 0;
    const hasLoginForm = await page.locator('[data-testid="login-form"]').count() > 0;
    const title = await page.title();
    
    console.log('Final page state:', {
      title,
      hasSpinner,
      hasLoginForm,
      bodyTextSnippet: bodyText?.substring(0, 200)
    });
    
    // The test should either show login form or complete without infinite loading
    const authResolved = hasLoginForm || (!hasSpinner && !bodyText?.includes('Loading'));
    
    expect(authResolved).toBe(true);
  });
});