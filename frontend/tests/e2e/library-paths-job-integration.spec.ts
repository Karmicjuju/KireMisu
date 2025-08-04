import { test, expect } from '@playwright/test';

test.describe('Library Paths with Job Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Mock library paths API
    await page.route('GET', '/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [
            {
              id: 'path-1',
              path: '/manga/library/main',
              enabled: true,
              scan_interval_hours: 24,
              last_scan: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
              created_at: new Date(Date.now() - 86400000).toISOString(),
              updated_at: new Date(Date.now() - 3600000).toISOString()
            },
            {
              id: 'path-2',
              path: '/manga/library/secondary',
              enabled: false,
              scan_interval_hours: 168,
              last_scan: null,
              created_at: new Date(Date.now() - 172800000).toISOString(),
              updated_at: new Date(Date.now() - 172800000).toISOString()
            }
          ],
          total: 2
        }),
      });
    });

    // Mock recent jobs API with path-specific jobs
    await page.route('GET', '/api/jobs/recent*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          jobs: [
            {
              id: 'job-1',
              job_type: 'library_scan',
              payload: { library_path_id: 'path-1' },
              status: 'running',
              priority: 8,
              started_at: new Date(Date.now() - 30000).toISOString(),
              completed_at: null,
              error_message: null,
              retry_count: 0,
              max_retries: 3,
              scheduled_at: new Date(Date.now() - 35000).toISOString(),
              created_at: new Date(Date.now() - 35000).toISOString(),
              updated_at: new Date(Date.now() - 30000).toISOString()
            },
            {
              id: 'job-2',
              job_type: 'library_scan',
              payload: { library_path_id: 'path-2' },
              status: 'failed',
              priority: 5,
              started_at: new Date(Date.now() - 300000).toISOString(),
              completed_at: new Date(Date.now() - 240000).toISOString(),
              error_message: 'Permission denied: cannot read directory',
              retry_count: 1,
              max_retries: 3,
              scheduled_at: new Date(Date.now() - 305000).toISOString(),
              created_at: new Date(Date.now() - 305000).toISOString(),
              updated_at: new Date(Date.now() - 240000).toISOString()
            }
          ],
          total: 2,
          job_type_filter: 'library_scan'
        }),
      });
    });

    // Mock job status API
    await page.route('GET', '/api/jobs/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          queue_stats: {
            pending: 0,
            running: 1,
            completed: 5,
            failed: 1
          },
          worker_status: null,
          timestamp: new Date().toISOString()
        }),
      });
    });

    // Mock worker status API
    await page.route('GET', '/api/jobs/worker/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: true,
          active_jobs: 1,
          max_concurrent_jobs: 3,
          poll_interval_seconds: 10
        }),
      });
    });

    await page.goto('/settings');
  });

  test('should display library paths with job status indicators', async ({ page }) => {
    // Wait for library paths to load
    await expect(page.getByText('/manga/library/main')).toBeVisible();
    await expect(page.getByText('/manga/library/secondary')).toBeVisible();

    // Check for status indicators
    await expect(page.getByText('Scanning')).toBeVisible(); // For path-1 (running job)
    await expect(page.getByText('Error')).toBeVisible(); // For path-2 (failed job)

    // Check for relative time formatting
    await expect(page.getByText(/1 hour ago/)).toBeVisible();

    // Check for auto-scan status
    await expect(page.getByText('Auto-scan Enabled')).toBeVisible();
    await expect(page.getByText('Auto-scan Disabled')).toBeVisible();
  });

  test('should show error messages for failed jobs', async ({ page }) => {
    // Should display error message from failed job
    await expect(page.getByText('Error: Permission denied: cannot read directory')).toBeVisible();
  });

  test('should display global scanning status', async ({ page }) => {
    // Global status indicator should show scanning state
    const statusIndicator = page.locator('h2:has-text("Library Paths")').locator('..').getByText('Scanning');
    await expect(statusIndicator).toBeVisible();
  });

  test('should schedule jobs when scan buttons are clicked', async ({ page }) => {
    // Mock job scheduling API
    await page.route('POST', '/api/jobs/schedule', async (route) => {
      const requestBody = await route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'scheduled',
          message: `Job scheduled successfully for ${requestBody.library_path_id ? 'specific path' : 'all paths'}`,
          job_id: 'new-job-id',
          scheduled_count: 1
        }),
      });
    });

    // Click "Scan All Libraries" button
    const scanAllButton = page.getByRole('button', { name: 'Scan All Libraries' });
    await scanAllButton.click();

    // Should show success toast
    await expect(page.getByText('Library scan scheduled')).toBeVisible();
    await expect(page.getByText('Job scheduled successfully for all paths')).toBeVisible();
  });

  test('should disable scan buttons when scans are running', async ({ page }) => {
    // Both individual and global scan buttons should be disabled due to running job
    const scanAllButton = page.getByRole('button', { name: /Scan All Libraries|Scanning/ });
    await expect(scanAllButton).toBeDisabled();

    // Individual scan buttons should also show appropriate state
    const scanButtons = page.getByRole('button', { name: /Scan Now|Scanning/ });
    
    // At least one should be showing "Scanning..." state
    await expect(page.getByText('Scanning...')).toBeVisible();
  });

  test('should handle different scan intervals correctly', async ({ page }) => {
    // Check that different scan intervals are displayed
    await expect(page.getByText('Scan interval: 24 hours')).toBeVisible();
    await expect(page.getByText('Scan interval: 1 week')).toBeVisible();
  });

  test('should format relative time correctly', async ({ page }) => {
    // Should show relative time instead of absolute timestamps
    await expect(page.getByText(/Last scan:.*hour.*ago/)).toBeVisible();
    
    // Path without last_scan should not show "Last scan:" text
    const secondaryPath = page.locator('text=/manga/library/secondary').locator('..');
    await expect(secondaryPath.getByText(/Last scan:/)).not.toBeVisible();
  });
});