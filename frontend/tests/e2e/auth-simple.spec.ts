/**
 * Simple authentication test to verify login works
 */

import { test, expect } from '@playwright/test';

test('can login to application', async ({ page }) => {
  // Navigate to the application
  await page.goto('/');
  
  // Debug: Take screenshot before filling form
  await page.screenshot({ path: 'before-login.png' });
  
  // Check if we're on the login page or the app
  const loginForm = page.locator('[data-testid="login-form"]');
  const sidebar = page.locator('[data-testid="sidebar"]');
  
  if (await loginForm.isVisible({ timeout: 5000 }).catch(() => false)) {
    console.log('Login form is visible, attempting to login...');
    
    // Fill in the login form using typing for reliability
    await page.focus('[data-testid="username-input"]');
    await page.fill('[data-testid="username-input"]', ''); // Clear first
    await page.type('[data-testid="username-input"]', 'admin', { delay: 50 });
    
    await page.focus('[data-testid="password-input"]');
    await page.fill('[data-testid="password-input"]', ''); // Clear first  
    await page.type('[data-testid="password-input"]', 'KireMisu2025!', { delay: 50 });
    
    // Wait for values to settle
    await page.waitForTimeout(500);
    
    // Debug: Take screenshot after filling form
    await page.screenshot({ path: 'after-fill.png' });
    
    // Click login button
    await page.click('[data-testid="login-button"]');
    
    // Wait for either navigation or error
    await Promise.race([
      page.waitForURL('**/library', { timeout: 10000 }),
      page.waitForSelector('.text-destructive', { timeout: 10000 }) // Error message
    ]).catch(async (err) => {
      console.log('Login failed or timed out:', err.message);
      await page.screenshot({ path: 'login-failed.png' });
    });
  }
  
  // Check if we're authenticated
  await expect(sidebar).toBeVisible({ timeout: 15000 });
  console.log('Successfully authenticated!');
  
  // Verify we can see the header with notification bell
  await expect(page.locator('[data-testid="notification-bell"]')).toBeVisible();
});