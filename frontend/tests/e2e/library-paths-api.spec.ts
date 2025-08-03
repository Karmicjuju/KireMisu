import { test, expect } from '@playwright/test';

test.describe('Library Paths API Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the API endpoints to avoid needing a real backend
    await page.route('/api/library/paths', async (route) => {
      const request = route.request();

      if (request.method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            paths: [
              {
                id: '123e4567-e89b-12d3-a456-426614174000',
                path: '/manga/library',
                enabled: true,
                scan_interval_hours: 24,
                last_scan: '2025-08-03T10:00:00Z',
                created_at: '2025-08-01T10:00:00Z',
                updated_at: '2025-08-03T10:00:00Z',
              },
            ],
            total: 1,
          }),
        });
      } else if (request.method() === 'POST') {
        const body = await request.postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '456e7890-e89b-12d3-a456-426614174001',
            path: body.path,
            enabled: body.enabled,
            scan_interval_hours: body.scan_interval_hours,
            last_scan: null,
            created_at: '2025-08-03T10:00:00Z',
            updated_at: '2025-08-03T10:00:00Z',
          }),
        });
      }
    });

    await page.route('/api/library/paths/*', async (route) => {
      const request = route.request();

      if (request.method() === 'PUT') {
        const body = await request.postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '123e4567-e89b-12d3-a456-426614174000',
            path: body.path || '/manga/library',
            enabled: body.enabled !== undefined ? body.enabled : true,
            scan_interval_hours: body.scan_interval_hours || 24,
            last_scan: '2025-08-03T10:00:00Z',
            created_at: '2025-08-01T10:00:00Z',
            updated_at: '2025-08-03T10:00:00Z',
          }),
        });
      } else if (request.method() === 'DELETE') {
        await route.fulfill({
          status: 204,
        });
      }
    });

    await page.route('/api/library/scan', async (route) => {
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Library scan initiated',
          paths_to_scan: 1,
          status: 'queued',
        }),
      });
    });
  });

  test('should display existing library paths', async ({ page }) => {
    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Should show the existing path
    await expect(page.getByText('/manga/library')).toBeVisible();
    await expect(page.getByText('Scan interval: 24 hours')).toBeVisible();
    // Updated date format and made it more flexible
    await expect(page.getByText(/Last scan:.*2025/)).toBeVisible();
    await expect(page.getByText('Enabled')).toBeVisible();

    // Should show edit and delete buttons (scope to main content)
    const mainContent = page.locator('main');
    await expect(mainContent.getByRole('button', { name: 'Edit' })).toBeVisible();
    await expect(mainContent.locator('button').filter({ has: page.locator('svg') })).toBeVisible(); // Trash icon
  });

  test('should successfully add a new library path', async ({ page }) => {
    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Click Add Path (scope to main content)
    const mainContent = page.locator('main');
    await mainContent.getByRole('button', { name: 'Add Path' }).click();

    // Fill in the form
    await page.getByLabel('Directory Path').fill('/new/manga/path');
    await page.getByLabel('Scan Interval').click();
    await page.getByRole('option', { name: '12 hours' }).click();

    // Submit the form (target form button specifically)
    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    await dialog.getByRole('button', { name: 'Add Path' }).click();

    // Should show success toast
    await expect(page.getByText('Path added')).toBeVisible();
    await expect(page.getByText('Library path has been added successfully.')).toBeVisible();

    // Form should be hidden
    await expect(page.getByRole('heading', { name: 'Add New Library Path' })).not.toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Override the mock to return an error
    await page.route('/api/library/paths', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Path does not exist: /invalid/path',
          }),
        });
      }
    });

    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Try to add an invalid path
    const mainContent = page.locator('main');
    await mainContent.getByRole('button', { name: 'Add Path' }).click();
    await page.getByLabel('Directory Path').fill('/invalid/path');
    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    await dialog.getByRole('button', { name: 'Add Path' }).click();

    // Should show error toast (using Radix UI toast structure)
    await expect(page.getByText('Error')).toBeVisible();
    await expect(page.getByText('Path does not exist: /invalid/path')).toBeVisible();
  });

  test('should successfully edit a library path', async ({ page }) => {
    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Click Edit button (scope to main content)
    const mainContent = page.locator('main');
    await mainContent.getByRole('button', { name: 'Edit' }).click();

    // Should open form in edit mode
    await expect(page.getByRole('heading', { name: 'Edit Library Path' })).toBeVisible();

    // Form should be pre-filled
    await expect(page.getByLabel('Directory Path')).toHaveValue('/manga/library');
    await expect(page.getByLabel('Enable automatic scanning')).toBeChecked();

    // Change the scan interval
    await page.getByLabel('Scan Interval').click();
    await page.getByRole('option', { name: '48 hours' }).click();

    // Submit the form (target form button specifically)
    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    await dialog.getByRole('button', { name: 'Update Path' }).click();

    // Should show success toast
    await expect(page.getByText('Path updated')).toBeVisible();
    await expect(page.getByText('Library path has been updated successfully.')).toBeVisible();
  });

  test('should successfully delete a library path', async ({ page }) => {
    // Mock the confirm dialog
    page.on('dialog', (dialog) => dialog.accept());

    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Click delete button (trash icon) - scope to main content to avoid sidebar conflicts
    const mainContent = page.locator('main');
    await mainContent.locator('button').filter({ has: page.locator('svg') }).click();

    // Should show success toast
    await expect(page.getByText('Path deleted')).toBeVisible();
    await expect(page.getByText('Library path has been deleted successfully.')).toBeVisible();
  });

  test('should handle scan now functionality', async ({ page }) => {
    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Click Scan Now button (scope to main content)
    const mainContent = page.locator('main');
    await mainContent.getByRole('button', { name: 'Scan Now' }).click();

    // Should show success toast
    await expect(page.getByText('Scan initiated')).toBeVisible();
    await expect(page.getByText('Scanning 1 library paths...')).toBeVisible();
  });

  test('should handle network errors', async ({ page }) => {
    // Override to simulate network error
    await page.route('/api/library/paths', (route) => route.abort());

    // Navigate directly to settings
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');

    // Should show empty state (component handles errors gracefully)
    await expect(page.getByText('No library paths configured. Add a path to get started.')).toBeVisible();
  });
});
