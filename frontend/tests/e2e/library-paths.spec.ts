import { test, expect } from '@playwright/test';

test.describe('Library Paths Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to settings page
    await page.goto('/settings');
  });

  test('should display library paths section', async ({ page }) => {
    // Check if the Library Paths section is visible
    await expect(page.getByRole('heading', { name: 'Library Paths' })).toBeVisible();
    
    // Check if the Add Path button is visible
    await expect(page.getByRole('button', { name: 'Add Path' })).toBeVisible();
    
    // Check if the Scan Now button is visible
    await expect(page.getByRole('button', { name: 'Scan Now' })).toBeVisible();
  });

  test('should show empty state when no paths are configured', async ({ page }) => {
    // Check for empty state message
    await expect(page.getByText('No library paths configured. Add a path to get started.')).toBeVisible();
  });

  test('should open add path form when Add Path button is clicked', async ({ page }) => {
    // Click the Add Path button
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Check if the form is visible
    await expect(page.getByRole('heading', { name: 'Add New Library Path' })).toBeVisible();
    
    // Check if form fields are present
    await expect(page.getByLabel('Directory Path')).toBeVisible();
    await expect(page.getByLabel('Enable automatic scanning')).toBeVisible();
    await expect(page.getByLabel('Scan Interval')).toBeVisible();
    
    // Check if form buttons are present
    await expect(page.getByRole('button', { name: 'Add Path' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
  });

  test('should close add path form when Cancel button is clicked', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    await expect(page.getByRole('heading', { name: 'Add New Library Path' })).toBeVisible();
    
    // Click Cancel
    await page.getByRole('button', { name: 'Cancel' }).click();
    
    // Form should be hidden
    await expect(page.getByRole('heading', { name: 'Add New Library Path' })).not.toBeVisible();
    
    // Add Path button should be visible again
    await expect(page.getByRole('button', { name: 'Add Path' })).toBeVisible();
  });

  test('should validate required fields in add path form', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Try to submit without filling required fields
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Check if browser validation kicks in (the input should be focused and invalid)
    const pathInput = page.getByLabel('Directory Path');
    await expect(pathInput).toBeFocused();
    
    // Check if the input has the required attribute
    await expect(pathInput).toHaveAttribute('required');
  });

  test('should populate form fields correctly', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Fill in the path
    await page.getByLabel('Directory Path').fill('/test/manga/path');
    
    // Toggle the enable switch (it should be enabled by default)
    const enableSwitch = page.getByLabel('Enable automatic scanning');
    await expect(enableSwitch).toBeChecked();
    
    // Change scan interval
    await page.getByLabel('Scan Interval').click();
    await page.getByRole('option', { name: '12 hours' }).click();
    
    // Verify the values are set
    await expect(page.getByLabel('Directory Path')).toHaveValue('/test/manga/path');
    await expect(enableSwitch).toBeChecked();
  });

  test('should handle directory picker button click', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Mock the prompt dialog since we can't interact with actual file picker in tests
    await page.evaluate(() => {
      window.prompt = () => '/mocked/directory/path';
    });
    
    // Click the directory picker button (folder icon)
    await page.getByRole('button').filter({ hasText: '' }).click(); // Folder icon button
    
    // Check if the path input was updated (this tests the JavaScript interaction)
    await expect(page.getByLabel('Directory Path')).toHaveValue('/mocked/directory/path');
  });

  test('should display scan interval options', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Click the scan interval dropdown
    await page.getByLabel('Scan Interval').click();
    
    // Check if all expected options are present
    await expect(page.getByRole('option', { name: '1 hour' })).toBeVisible();
    await expect(page.getByRole('option', { name: '2 hours' })).toBeVisible();
    await expect(page.getByRole('option', { name: '6 hours' })).toBeVisible();
    await expect(page.getByRole('option', { name: '12 hours' })).toBeVisible();
    await expect(page.getByRole('option', { name: '24 hours' })).toBeVisible();
    await expect(page.getByRole('option', { name: '48 hours' })).toBeVisible();
    await expect(page.getByRole('option', { name: '1 week' })).toBeVisible();
  });

  test('should have proper keyboard navigation', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    // Tab through form elements
    await page.keyboard.press('Tab'); // Should focus path input
    await expect(page.getByLabel('Directory Path')).toBeFocused();
    
    await page.keyboard.press('Tab'); // Should focus folder picker button
    await page.keyboard.press('Tab'); // Should focus enable switch
    await expect(page.getByLabel('Enable automatic scanning')).toBeFocused();
    
    await page.keyboard.press('Tab'); // Should focus scan interval
    await expect(page.getByLabel('Scan Interval')).toBeFocused();
    
    await page.keyboard.press('Tab'); // Should focus Add Path button
    await expect(page.getByRole('button', { name: 'Add Path' })).toBeFocused();
    
    await page.keyboard.press('Tab'); // Should focus Cancel button
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeFocused();
  });

  test('should handle enable/disable switch toggle', async ({ page }) => {
    // Open the form
    await page.getByRole('button', { name: 'Add Path' }).click();
    
    const enableSwitch = page.getByLabel('Enable automatic scanning');
    
    // Should be enabled by default
    await expect(enableSwitch).toBeChecked();
    
    // Click to disable
    await enableSwitch.click();
    await expect(enableSwitch).not.toBeChecked();
    
    // Click to enable again
    await enableSwitch.click();
    await expect(enableSwitch).toBeChecked();
  });

  test('should show loading state when API calls are in progress', async ({ page }) => {
    // Mock slow API response to test loading states
    await page.route('/api/library/paths', async route => {
      await new Promise(resolve => setTimeout(resolve, 100));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ paths: [], total: 0 })
      });
    });

    // Navigate to settings and check loading state
    await page.goto('/settings');
    await expect(page.getByText('Loading library paths...')).toBeVisible();
  });
});