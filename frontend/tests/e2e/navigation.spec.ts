import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should navigate from home page to settings', async ({ page }) => {
    // Go to home page
    await page.goto('/');
    
    // Check that we're on the home page
    await expect(page.getByRole('heading', { name: 'KireMisu' })).toBeVisible();
    await expect(page.getByText('Self-hosted manga reader and library management system')).toBeVisible();
    
    // Click the Settings button
    await page.getByRole('button', { name: 'Settings' }).click();
    
    // Should navigate to settings page
    await expect(page).toHaveURL('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Library Paths' })).toBeVisible();
  });

  test('should have accessible navigation elements', async ({ page }) => {
    await page.goto('/');
    
    // Check that the Settings button has proper accessibility attributes
    const settingsButton = page.getByRole('button', { name: 'Settings' });
    await expect(settingsButton).toBeVisible();
    await expect(settingsButton).toBeEnabled();
    
    // Should be keyboard accessible
    await settingsButton.focus();
    await expect(settingsButton).toBeFocused();
    
    // Should navigate when activated with keyboard
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL('/settings');
  });

  test('should display development status indicators', async ({ page }) => {
    await page.goto('/');
    
    // Check for development status indicators
    await expect(page.getByText('🚧 Under Development')).toBeVisible();
    await expect(page.getByText('📚 Manga Library Management')).toBeVisible();
    await expect(page.getByText('🔍 MangaDx Integration')).toBeVisible();
    await expect(page.getByText('📖 Advanced Reading Experience')).toBeVisible();
    await expect(page.getByText('🏷️ Custom Tagging & Organization')).toBeVisible();
  });
});