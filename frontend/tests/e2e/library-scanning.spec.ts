import { test, expect } from '@playwright/test';

test.describe('Library Scanning API Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the library paths API to ensure consistent test state
    await page.route('GET', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [],
          total: 0,
        }),
      });
    });

    // Navigate to settings page where library paths are managed
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display library paths management interface', async ({ page }) => {
    // Verify the Library Paths section is present
    await expect(page.getByRole('heading', { name: 'Library Paths' })).toBeVisible();

    // Check if main interface elements are present
    const mainContent = page.locator('main');
    await expect(mainContent.getByRole('button', { name: 'Add Path' })).toBeVisible();

    // Verify empty state message
    await expect(page.getByText('No library paths configured')).toBeVisible();
  });

  test('should handle filesystem parser validation scenarios', async ({ page }) => {
    // Mock API responses for different parser validation scenarios
    await page.route('POST', '/api/library/paths', async (route) => {
      const requestData = await route.request().postDataJSON();

      // Simulate filesystem parser validation
      if (requestData.path === '/invalid/path') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Library path does not exist: /invalid/path',
          }),
        });
      } else if (requestData.path === '/permission/denied') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Library path is not readable: /permission/denied',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'path-1',
            path: requestData.path,
            enabled: requestData.enabled,
            scan_interval: requestData.scan_interval,
          }),
        });
      }
    });

    const mainContent = page.locator('main');

    // Test valid path
    await mainContent.getByRole('button', { name: 'Add Path' }).click();
    await page.getByLabel('Directory Path').fill('/valid/manga/path');

    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    await dialog.getByRole('button', { name: 'Add Path' }).click();

    // Should succeed for valid path
    await expect(page.getByText(/successfully added/i)).toBeVisible({ timeout: 5000 });
  });

  test('should handle parser error responses', async ({ page }) => {
    // Mock error responses that would come from filesystem parser validation
    await page.route('POST', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Library path does not exist: /nonexistent/path',
        }),
      });
    });

    const mainContent = page.locator('main');

    // Try to add invalid path
    await mainContent.getByRole('button', { name: 'Add Path' }).click();
    await page.getByLabel('Directory Path').fill('/nonexistent/path');

    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    await dialog.getByRole('button', { name: 'Add Path' }).click();

    // Should show filesystem parser error
    await expect(page.getByText(/Library path does not exist/)).toBeVisible({ timeout: 5000 });
  });

  test('should validate different file format scenarios', async ({ page }) => {
    // Mock API responses for paths with different manga formats
    await page.route('GET', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [
            {
              id: 'path-1',
              path: '/manga/mixed-formats',
              enabled: true,
              scan_interval: 3600,
              last_scan: '2025-08-03T19:30:00Z',
              series_count: 5,
              chapter_count: 23,
              format_breakdown: {
                cbz: 15,
                cbr: 4,
                pdf: 3,
                folder: 1,
              },
            },
          ],
          total: 1,
        }),
      });
    });

    // Reload to get the mocked data
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Should show path with mixed formats
    await expect(page.getByText('/manga/mixed-formats')).toBeVisible();
    await expect(page.getByText(/5 series/)).toBeVisible();
    await expect(page.getByText(/23 chapters/)).toBeVisible();
  });

  test('should handle large library performance scenarios', async ({ page }) => {
    // Mock API response for large library scenario
    await page.route('GET', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [
            {
              id: 'path-1',
              path: '/manga/large-library',
              enabled: true,
              scan_interval: 3600,
              last_scan: '2025-08-03T19:30:00Z',
              series_count: 1247,
              chapter_count: 15632,
              scan_duration_ms: 45678,
            },
          ],
          total: 1,
        }),
      });
    });

    // Reload to get the mocked data
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Should handle large numbers gracefully
    await expect(page.getByText('/manga/large-library')).toBeVisible();
    await expect(page.getByText(/1247 series/)).toBeVisible();
    await expect(page.getByText(/15632 chapters/)).toBeVisible();
  });

  test('should handle security validation errors', async ({ page }) => {
    // Mock security-related errors that parser might detect
    await page.route('POST', '/api/library/paths', async (route) => {
      const requestData = await route.request().postDataJSON();

      if (requestData.path.includes('../')) {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Invalid path: Path traversal detected',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'path-1',
            path: requestData.path,
            enabled: requestData.enabled,
            scan_interval: requestData.scan_interval,
          }),
        });
      }
    });

    const mainContent = page.locator('main');

    // Try to add path with traversal attempt
    await mainContent.getByRole('button', { name: 'Add Path' }).click();
    await page.getByLabel('Directory Path').fill('/manga/../../../etc');

    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    await dialog.getByRole('button', { name: 'Add Path' }).click();

    // Should show security validation error
    await expect(page.getByText(/Path traversal detected/)).toBeVisible({ timeout: 5000 });
  });

  test('should display parser warnings and errors appropriately', async ({ page }) => {
    // Mock API response with parser warnings
    await page.route('GET', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [
            {
              id: 'path-1',
              path: '/manga/problematic',
              enabled: true,
              scan_interval: 3600,
              last_scan: '2025-08-03T19:30:00Z',
              series_count: 3,
              chapter_count: 12,
              last_scan_warnings: [
                'Could not extract chapter number from: random_file.txt',
                'Corrupted archive skipped: broken.cbz',
              ],
              last_scan_errors: ['Permission denied: restricted_folder/'],
            },
          ],
          total: 1,
        }),
      });
    });

    // Reload to get the mocked data
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Should show path with warnings
    await expect(page.getByText('/manga/problematic')).toBeVisible();

    // Should indicate scan completed with issues
    await expect(page.getByText(/warnings/i)).toBeVisible();
  });

  test('should handle concurrent operations gracefully', async ({ page }) => {
    // Test that UI can handle multiple API calls without breaking
    let requestCount = 0;

    await page.route('POST', '/api/library/paths', async (route) => {
      requestCount++;

      // Simulate different response times
      const delay = requestCount * 100;
      await new Promise((resolve) => setTimeout(resolve, delay));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `path-${requestCount}`,
          path: `/manga/path-${requestCount}`,
          enabled: true,
          scan_interval: 3600,
        }),
      });
    });

    const mainContent = page.locator('main');

    // Quickly add multiple paths
    for (let i = 1; i <= 3; i++) {
      await mainContent.getByRole('button', { name: 'Add Path' }).click();
      await page.getByLabel('Directory Path').fill(`/manga/path-${i}`);

      const dialog = page.locator('[role="dialog"], .space-y-4').first();
      await dialog.getByRole('button', { name: 'Add Path' }).click();

      // Brief wait between operations
      await page.waitForTimeout(50);
    }

    // All operations should eventually complete
    await expect(page.getByText(/successfully added/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('should maintain accessibility during parser operations', async ({ page }) => {
    // Mock slow API response to test loading states
    await page.route('POST', '/api/library/paths', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 200));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'path-1',
          path: '/manga/test',
          enabled: true,
          scan_interval: 3600,
        }),
      });
    });

    const mainContent = page.locator('main');

    // Start adding a path
    await mainContent.getByRole('button', { name: 'Add Path' }).click();
    await page.getByLabel('Directory Path').fill('/manga/test');

    const dialog = page.locator('[role="dialog"], .space-y-4').first();
    const addButton = dialog.getByRole('button', { name: 'Add Path' });

    // Check accessibility attributes before operation
    await expect(addButton).toHaveAttribute('aria-disabled', 'false');

    // Start operation
    await addButton.click();

    // During operation, button should be properly disabled
    await expect(addButton).toHaveAttribute('aria-disabled', 'true');

    // Should show loading indication
    await expect(page.getByText(/adding/i)).toBeVisible();

    // Wait for completion
    await expect(page.getByText(/successfully added/i)).toBeVisible({ timeout: 5000 });
  });
});
