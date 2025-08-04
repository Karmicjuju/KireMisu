import { test, expect } from '@playwright/test';

test.describe('Job Status Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Enable logging to see network requests
    page.on('request', (req) => console.log('REQUEST:', req.method(), req.url()));
    page.on('response', (res) => console.log('RESPONSE:', res.status(), res.url()));

    // Mock job status API
    await page.route('**/api/jobs/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          queue_stats: {
            pending: 2,
            running: 1,
            completed: 15,
            failed: 0,
          },
          worker_status: {
            running: true,
            active_jobs: 1,
            max_concurrent_jobs: 3,
            poll_interval_seconds: 10,
          },
          timestamp: new Date().toISOString(),
        }),
      });
    });

    // Mock recent jobs API - handle both filtered and unfiltered requests
    await page.route('**/api/jobs/recent**', async (route) => {
      const url = new URL(route.request().url());
      const jobType = url.searchParams.get('job_type');
      const limit = url.searchParams.get('limit');

      let jobs = [
        {
          id: 'job-1',
          job_type: 'library_scan',
          payload: { library_path_id: null },
          status: 'running',
          priority: 8,
          started_at: new Date(Date.now() - 30000).toISOString(),
          completed_at: null,
          error_message: null,
          retry_count: 0,
          max_retries: 3,
          scheduled_at: new Date(Date.now() - 35000).toISOString(),
          created_at: new Date(Date.now() - 35000).toISOString(),
          updated_at: new Date(Date.now() - 30000).toISOString(),
        },
        {
          id: 'job-2',
          job_type: 'library_scan',
          payload: { library_path_id: 'path-123' },
          status: 'completed',
          priority: 5,
          started_at: new Date(Date.now() - 120000).toISOString(),
          completed_at: new Date(Date.now() - 60000).toISOString(),
          error_message: null,
          retry_count: 0,
          max_retries: 3,
          scheduled_at: new Date(Date.now() - 125000).toISOString(),
          created_at: new Date(Date.now() - 125000).toISOString(),
          updated_at: new Date(Date.now() - 60000).toISOString(),
        },
      ];

      // Filter by job type if requested
      if (jobType) {
        jobs = jobs.filter((job) => job.job_type === jobType);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          jobs: jobs,
          total: jobs.length,
          job_type_filter: jobType,
        }),
      });
    });

    // Mock worker status API
    await page.route('**/api/jobs/worker/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: true,
          active_jobs: 1,
          max_concurrent_jobs: 3,
          poll_interval_seconds: 10,
          message: null,
        }),
      });
    });

    // Mock library paths for the main settings page
    await page.route('**/api/library/paths', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          paths: [],
          total: 0,
        }),
      });
    });

    await page.goto('/settings');
  });

  test('should display job queue statistics', async ({ page }) => {
    // Track API calls
    let apiCalls = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        apiCalls.push(req.url());
        console.log('API REQUEST:', req.method(), req.url());
      }
    });

    // Wait for the job status dashboard to load
    await expect(page.getByText('Job Status')).toBeVisible({ timeout: 10000 });

    // Wait longer for SWR to make initial requests
    await page.waitForTimeout(8000);

    console.log('API calls made:', apiCalls);

    // Check if the error message is showing instead
    const errorMsg = page.getByText('Failed to load job status information.');
    if (await errorMsg.isVisible()) {
      console.log('Error message is visible - API calls are failing');
    }

    // Check if no recent jobs message is showing
    const noJobsMsg = page.getByText('No recent jobs found.');
    if (await noJobsMsg.isVisible()) {
      console.log('No recent jobs message is visible - jobs API data is empty');
    }

    // Take a screenshot for debugging
    await page.screenshot({ path: 'debug-job-status-after-wait.png' });

    // If no API calls were made, wait longer and force SWR to make requests
    if (apiCalls.length === 0) {
      console.log('No API calls detected, refreshing page to trigger SWR');
      await page.reload();
      await page.waitForTimeout(3000);
    }

    // Check queue statistics cards - should be visible now
    await expect(page.getByText('Pending')).toBeVisible();
    await expect(page.getByText('2', { exact: true })).toBeVisible(); // Pending count

    await expect(page.getByText('Running')).toBeVisible();
    await expect(page.getByText('1', { exact: true })).toBeVisible(); // Running count

    await expect(page.getByText('Completed')).toBeVisible();
    await expect(page.getByText('15', { exact: true })).toBeVisible(); // Completed count

    await expect(page.getByText('Failed')).toBeVisible();
    await expect(page.getByText('0', { exact: true })).toBeVisible(); // Failed count
  });

  test('should display worker status information', async ({ page }) => {
    // Check worker status indicator
    await expect(page.getByText('Worker Running')).toBeVisible();

    // Check worker details
    await expect(page.getByText('Worker Details')).toBeVisible();
    await expect(page.getByText('Active Jobs: 1 / 3')).toBeVisible();
    await expect(page.getByText('Poll Interval: 10s')).toBeVisible();
    await expect(page.getByText('Status: Active')).toBeVisible();
  });

  test('should display recent jobs list', async ({ page }) => {
    await expect(page.getByText('Recent Jobs')).toBeVisible();

    // Check for job entries
    await expect(page.getByText('Library Scan')).toBeVisible();

    // Check for job status badges
    await expect(page.getByText('Running')).toBeVisible();
    await expect(page.getByText('Completed')).toBeVisible();

    // Check relative time formatting
    await expect(page.getByText(/ago/)).toBeVisible();
  });

  test('should show job priority badges for non-default priorities', async ({ page }) => {
    // The first job has priority 8 (non-default), should show badge
    await expect(page.getByText('Priority 8')).toBeVisible();

    // The second job has priority 5 (default), should not show badge
    await expect(page.getByText('Priority 5')).not.toBeVisible();
  });

  test('should handle job status API errors gracefully', async ({ page }) => {
    // Override with error response
    await page.route('**/api/jobs/status', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.reload();

    // Should show error message
    await expect(page.getByText('Failed to load job status information.')).toBeVisible();
  });
});
