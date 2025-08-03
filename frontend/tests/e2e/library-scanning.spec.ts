import { test, expect } from '@playwright/test';

test.describe('Library Scanning Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the library paths API to ensure consistent test state
    await page.route('GET', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [
            {
              id: 'path-1',
              path: '/manga/test-library',
              enabled: true,
              scan_interval_hours: 24,
              last_scan: '2025-08-03T10:00:00Z',
              created_at: '2025-08-01T00:00:00Z',
              updated_at: '2025-08-03T10:00:00Z',
            },
            {
              id: 'path-2', 
              path: '/manga/second-library',
              enabled: false,
              scan_interval_hours: 12,
              last_scan: null,
              created_at: '2025-08-02T00:00:00Z',
              updated_at: '2025-08-02T00:00:00Z',
            },
          ],
          total: 2,
        }),
      });
    });

    // Navigate to settings page where library paths are managed
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display library paths with scan buttons', async ({ page }) => {
    // Verify the Library Paths section is present
    await expect(page.getByRole('heading', { name: 'Library Paths' })).toBeVisible();

    // Check if scan all button is present
    await expect(page.getByRole('button', { name: 'Scan All Libraries' })).toBeVisible();

    // Check that individual library paths have scan buttons
    await expect(page.getByText('/manga/test-library')).toBeVisible();
    await expect(page.getByText('/manga/second-library')).toBeVisible();
    
    // Verify individual scan buttons are present
    const scanNowButtons = page.getByRole('button', { name: 'Scan Now' });
    await expect(scanNowButtons).toHaveCount(2);
  });

  test('should successfully scan all libraries', async ({ page }) => {
    // Mock successful scan response
    await page.route('POST', '/api/library/scan', async (route) => {
      const requestData = await route.request().postDataJSON();
      
      // Check if scanning all libraries (no library_path_id)
      if (!requestData.library_path_id) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'completed',
            message: 'Library scan completed',
            stats: {
              series_found: 5,
              series_created: 2,
              series_updated: 1,
              chapters_found: 23,
              chapters_created: 12,
              chapters_updated: 3,
              errors: 0,
            },
          }),
        });
      }
    });

    // Click "Scan All Libraries" button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show loading state
    await expect(page.getByRole('button', { name: 'Scanning...' })).toBeVisible();
    
    // Should show success toast
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Found 5 series with 23 chapters/)).toBeVisible();
  });

  test('should successfully scan individual library path', async ({ page }) => {
    // Mock successful individual scan response
    await page.route('POST', '/api/library/scan', async (route) => {
      const requestData = await route.request().postDataJSON();
      
      // Check if scanning specific library path
      if (requestData.library_path_id === 'path-1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'completed',
            message: 'Library path scan completed',
            stats: {
              series_found: 3,
              series_created: 1,
              series_updated: 0,
              chapters_found: 15,
              chapters_created: 8,
              chapters_updated: 0,
              errors: 0,
            },
          }),
        });
      }
    });

    // Find the first library path and click its scan button
    const libraryPathRow = page.locator('div').filter({ hasText: '/manga/test-library' }).first();
    const scanButton = libraryPathRow.getByRole('button', { name: 'Scan Now' });
    
    await scanButton.click();

    // Should show loading state for this specific path
    await expect(libraryPathRow.getByRole('button', { name: 'Scanning...' })).toBeVisible();
    
    // Should show success toast
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Found 3 series with 15 chapters/)).toBeVisible();
  });

  test('should handle scan errors gracefully', async ({ page }) => {
    // Mock error response for scan
    await page.route('POST', '/api/library/scan', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Library scan failed: Permission denied accessing /manga/restricted',
        }),
      });
    });

    // Click "Scan All Libraries" button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show loading state initially
    await expect(page.getByRole('button', { name: 'Scanning...' })).toBeVisible();
    
    // Should show error toast
    await expect(page.getByText(/Library scan failed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Permission denied accessing/)).toBeVisible();
    
    // Button should return to normal state
    await expect(page.getByRole('button', { name: 'Scan All Libraries' })).toBeVisible();
  });

  test('should handle scan with warnings and errors', async ({ page }) => {
    // Mock scan response with warnings and errors
    await page.route('POST', '/api/library/scan', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed_with_errors',
          message: 'Library scan completed (2 errors encountered)',
          stats: {
            series_found: 8,
            series_created: 3,
            series_updated: 2,
            chapters_found: 45,
            chapters_created: 20,
            chapters_updated: 5,
            errors: 2,
          },
        }),
      });
    });

    // Click "Scan All Libraries" button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show success toast even with errors
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Found 8 series with 45 chapters/)).toBeVisible();
  });

  test('should disable buttons during scan operations', async ({ page }) => {
    // Mock delayed scan response to test button states
    await page.route('POST', '/api/library/scan', async (route) => {
      const requestData = await route.request().postDataJSON();
      
      // Add delay to simulate longer scan
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          message: 'Library scan completed',
          stats: {
            series_found: 2,
            series_created: 1,
            series_updated: 0,
            chapters_found: 10,
            chapters_created: 5,
            chapters_updated: 0,
            errors: 0,
          },
        }),
      });
    });

    // Start scanning all libraries
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // During scan, other scan buttons should be disabled
    const individualScanButtons = page.getByRole('button', { name: 'Scan Now' });
    for (const button of await individualScanButtons.all()) {
      await expect(button).toBeDisabled();
    }
    
    // Wait for scan to complete
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    
    // After completion, buttons should be re-enabled
    await expect(scanAllButton).toBeEnabled();
    for (const button of await individualScanButtons.all()) {
      await expect(button).toBeEnabled();
    }
  });

  test('should handle scan timeout scenarios', async ({ page }) => {
    // Mock timeout response
    await page.route('POST', '/api/library/scan', async (route) => {
      // Simulate timeout by not responding
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 408,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Library scan timed out after 60 seconds',
        }),
      });
    });

    // Click "Scan All Libraries" button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show loading state
    await expect(page.getByRole('button', { name: 'Scanning...' })).toBeVisible();
    
    // Should eventually show timeout error
    await expect(page.getByText(/Library scan failed/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/timed out/)).toBeVisible();
  });

  test('should prevent concurrent scan operations', async ({ page }) => {
    // Mock delayed scan response
    await page.route('POST', '/api/library/scan', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          message: 'Library scan completed',
          stats: {
            series_found: 1,
            series_created: 1,
            series_updated: 0,
            chapters_found: 5,
            chapters_created: 5,
            chapters_updated: 0,
            errors: 0,
          },
        }),
      });
    });

    // Start first scan
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show scanning state
    await expect(page.getByRole('button', { name: 'Scanning...' })).toBeVisible();
    
    // Try to start another scan - all scan buttons should be disabled
    const individualScanButtons = page.getByRole('button', { name: 'Scan Now' });
    for (const button of await individualScanButtons.all()) {
      await expect(button).toBeDisabled();
    }
    
    // Wait for first scan to complete
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    
    // Now buttons should be enabled again
    await expect(scanAllButton).toBeEnabled();
  });

  test('should maintain accessibility during scan operations', async ({ page }) => {
    // Mock delayed scan response to test accessibility
    await page.route('POST', '/api/library/scan', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          message: 'Library scan completed',
          stats: {
            series_found: 1,
            series_created: 1,
            series_updated: 0,
            chapters_found: 5,
            chapters_created: 5,
            chapters_updated: 0,
            errors: 0,
          },
        }),
      });
    });

    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    
    // Check accessibility attributes before operation
    await expect(scanAllButton).not.toHaveAttribute('disabled');
    await expect(scanAllButton).toHaveAttribute('aria-disabled', 'false');

    // Start scan operation
    await scanAllButton.click();

    // During operation, button should be properly disabled with aria attributes
    const scanningButton = page.getByRole('button', { name: 'Scanning...' });
    await expect(scanningButton).toBeVisible();
    await expect(scanningButton).toHaveAttribute('disabled');
    
    // Wait for completion
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    
    // After completion, button should be accessible again
    await expect(scanAllButton).not.toHaveAttribute('disabled');
    await expect(scanAllButton).toHaveAttribute('aria-disabled', 'false');
  });

  test('should display scan results statistics correctly', async ({ page }) => {
    // Mock scan response with detailed stats
    await page.route('POST', '/api/library/scan', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          message: 'Library scan completed',
          stats: {
            series_found: 12,
            series_created: 8,
            series_updated: 3,
            chapters_found: 156,
            chapters_created: 98,
            chapters_updated: 12,
            errors: 0,
          },
        }),
      });
    });

    // Click scan button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show detailed statistics in toast
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Found 12 series with 156 chapters/)).toBeVisible();
  });

  test('should handle API rate limiting gracefully', async ({ page }) => {
    // Mock rate limiting response
    await page.route('POST', '/api/library/scan', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Rate limit exceeded. Please try again later.',
        }),
      });
    });

    // Click scan button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show rate limiting error
    await expect(page.getByText(/Library scan failed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Rate limit exceeded/)).toBeVisible();
    
    // Button should return to normal state
    await expect(scanAllButton).toBeEnabled();
  });

  test('should handle large library scan results', async ({ page }) => {
    // Mock large library scan response
    await page.route('POST', '/api/library/scan', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          message: 'Library scan completed',
          stats: {
            series_found: 1247,
            series_created: 856,
            series_updated: 123,
            chapters_found: 15634,
            chapters_created: 12456,
            chapters_updated: 897,
            errors: 0,
          },
        }),
      });
    });

    // Click scan button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should handle large numbers properly
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Found 1247 series with 15634 chapters/)).toBeVisible();
  });

  test('should refresh library path data after successful scan', async ({ page }) => {
    let getPathsCalled = 0;
    
    // Count calls to GET /api/library/paths
    await page.route('GET', '/api/library/paths', async (route) => {
      getPathsCalled++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [
            {
              id: 'path-1',
              path: '/manga/test-library',
              enabled: true,
              scan_interval_hours: 24,
              last_scan: getPathsCalled > 1 ? '2025-08-03T15:30:00Z' : '2025-08-03T10:00:00Z',
              created_at: '2025-08-01T00:00:00Z',
              updated_at: '2025-08-03T15:30:00Z',
            },
          ],
          total: 1,
        }),
      });
    });

    // Mock successful scan
    await page.route('POST', '/api/library/scan', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          message: 'Library scan completed',
          stats: {
            series_found: 2,
            series_created: 1,
            series_updated: 0,
            chapters_found: 8,
            chapters_created: 4,
            chapters_updated: 0,
            errors: 0,
          },
        }),
      });
    });

    // Navigate to page (first API call)
    await page.goto('/settings');
    await page.waitForLoadState('domcontentloaded');
    
    // Initially should show old timestamp
    await expect(page.getByText(/Last scan.*10:00/)).toBeVisible();
    
    // Trigger scan
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();
    
    // Wait for scan completion
    await expect(page.getByText(/Library scan completed/)).toBeVisible({ timeout: 5000 });
    
    // Should refresh and show updated timestamp
    await expect(page.getByText(/Last scan.*15:30/)).toBeVisible({ timeout: 5000 });
    
    // Verify API was called twice (initial load + refresh after scan)
    expect(getPathsCalled).toBeGreaterThanOrEqual(2);
  });
});
