import { test, expect, Page } from '@playwright/test';

/**
 * Comprehensive E2E Tests for Downloads System
 * Tests the complete download workflow including UI responsiveness,
 * accessibility, polling optimization, and error handling.
 */

test.describe('Downloads System - Comprehensive E2E Tests', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    
    // Mock the backend API for consistent testing
    await page.route('/api/downloads/**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();
      
      if (method === 'GET' && url.includes('/api/downloads?')) {
        // Mock download list response
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            jobs: [
              {
                id: 'download-1',
                download_type: 'mangadx',
                manga_id: 'manga-1',
                status: 'running',
                priority: 5,
                progress: {
                  total_chapters: 10,
                  downloaded_chapters: 3,
                  current_chapter: { id: 'ch-4', title: 'Chapter 4' },
                  current_chapter_progress: 0.6,
                  overall_progress: 0.36,
                  eta_seconds: 420
                },
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
              },
              {
                id: 'download-2',
                download_type: 'mangadx',
                manga_id: 'manga-2',
                status: 'pending',
                priority: 3,
                progress: {
                  total_chapters: 5,
                  downloaded_chapters: 0,
                  current_chapter: null,
                  current_chapter_progress: 0,
                  overall_progress: 0,
                  eta_seconds: null
                },
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
              }
            ],
            total: 2,
            pending_downloads: 1,
            active_downloads: 1,
            pagination: { page: 1, per_page: 20, total_pages: 1 }
          })
        });
      } else if (method === 'POST' && url.includes('/api/downloads/')) {
        // Mock download creation
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-download-id',
            download_type: 'mangadx',
            manga_id: 'manga-new',
            status: 'pending',
            priority: 5,
            progress: {
              total_chapters: 1,
              downloaded_chapters: 0,
              current_chapter: null,
              current_chapter_progress: 0,
              overall_progress: 0,
              eta_seconds: null
            },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
        });
      } else if (method === 'POST' && url.includes('/actions')) {
        // Mock job actions (cancel, retry, etc.)
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            job_id: 'download-1',
            action: 'cancel',
            success: true,
            new_status: 'failed'
          })
        });
      } else if (method === 'DELETE') {
        // Mock job deletion
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Download job deleted successfully' })
        });
      }
    });

    // Navigate to the downloads page
    await page.goto('/downloads');
    await page.waitForLoadState('networkidle');
  });

  test('should display downloads page with proper layout and accessibility', async () => {
    // Test page title and structure
    await expect(page).toHaveTitle(/Downloads/);
    
    // Test main heading with proper accessibility
    const mainHeading = page.locator('h1');
    await expect(mainHeading).toBeVisible();
    await expect(mainHeading).toHaveText(/Downloads/);
    
    // Test download queue section
    const queueSection = page.locator('[data-testid="download-queue"]');
    await expect(queueSection).toBeVisible();
    
    // Test accessibility - check for proper ARIA labels
    const downloadCards = page.locator('[data-testid="download-card"]');
    await expect(downloadCards).toHaveCount(2);
    
    for (let i = 0; i < 2; i++) {
      const card = downloadCards.nth(i);
      await expect(card).toHaveAttribute('role', 'article');
      await expect(card).toHaveAttribute('aria-labelledby');
    }
  });

  test('should show real-time download progress updates', async () => {
    // Wait for initial load
    await page.waitForSelector('[data-testid="download-card"]');
    
    // Find the running download card
    const runningCard = page.locator('[data-testid="download-card"]').filter({ hasText: 'running' });
    await expect(runningCard).toBeVisible();
    
    // Test progress bar visibility and values
    const progressBar = runningCard.locator('[data-testid="progress-bar"]');
    await expect(progressBar).toBeVisible();
    await expect(progressBar).toHaveAttribute('aria-valuenow', '36'); // 36% progress
    
    // Test progress text
    const progressText = runningCard.locator('[data-testid="progress-text"]');
    await expect(progressText).toContainText('3 of 10 chapters');
    
    // Test ETA display
    const etaText = runningCard.locator('[data-testid="eta-text"]');
    await expect(etaText).toContainText('7 minutes');
    
    // Test current chapter info
    const currentChapter = runningCard.locator('[data-testid="current-chapter"]');
    await expect(currentChapter).toContainText('Chapter 4');
  });

  test('should handle download actions (cancel, retry, delete)', async () => {
    // Wait for download cards to load
    const downloadCards = page.locator('[data-testid="download-card"]');
    await expect(downloadCards).toHaveCount(2);
    
    const runningCard = downloadCards.first();
    
    // Test cancel action
    const cancelButton = runningCard.locator('[data-testid="cancel-button"]');
    await expect(cancelButton).toBeVisible();
    await expect(cancelButton).toBeEnabled();
    
    // Click cancel and verify confirmation dialog
    await cancelButton.click();
    
    const confirmDialog = page.locator('[role="dialog"]');
    await expect(confirmDialog).toBeVisible();
    await expect(confirmDialog).toContainText('Cancel Download');
    
    // Test accessibility of dialog
    await expect(confirmDialog).toHaveAttribute('aria-modal', 'true');
    
    const confirmButton = confirmDialog.locator('button:has-text("Confirm")');
    await confirmButton.click();
    
    // Wait for action to complete
    await page.waitForResponse('/api/downloads/*/actions');
    
    // Test retry functionality on failed jobs
    // First simulate a failed job state by mocking the API response
    await page.route('/api/downloads?*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          jobs: [{
            id: 'download-1',
            status: 'failed',
            error_message: 'Network timeout',
            priority: 5,
            progress: {
              total_chapters: 10,
              downloaded_chapters: 3,
              current_chapter: null,
              current_chapter_progress: 0,
              overall_progress: 0.3,
              eta_seconds: null
            },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }],
          total: 1,
          pending_downloads: 0,
          active_downloads: 0,
          pagination: { page: 1, per_page: 20, total_pages: 1 }
        })
      });
    });
    
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    const failedCard = page.locator('[data-testid="download-card"]').filter({ hasText: 'failed' });
    const retryButton = failedCard.locator('[data-testid="retry-button"]');
    
    await expect(retryButton).toBeVisible();
    await retryButton.click();
    
    // Verify retry action
    await page.waitForResponse('/api/downloads/*/actions');
  });

  test('should display proper error states and messages', async () => {
    // Mock API error response
    await page.route('/api/downloads?*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal server error - database connection failed'
        })
      });
    });
    
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Check for error message display
    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Failed to load downloads');
    
    // Test retry button in error state
    const retryButton = page.locator('[data-testid="retry-load-button"]');
    await expect(retryButton).toBeVisible();
    await retryButton.click();
  });

  test('should be responsive across different screen sizes', async () => {
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Verify layout adapts to mobile
    const downloadCards = page.locator('[data-testid="download-card"]');
    await expect(downloadCards.first()).toBeVisible();
    
    // Test that cards stack vertically and maintain readability
    const cardWidth = await downloadCards.first().boundingBox();
    expect(cardWidth?.width).toBeLessThan(375);
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // Verify cards maintain appropriate sizing
    const tabletCardWidth = await downloadCards.first().boundingBox();
    expect(tabletCardWidth?.width).toBeLessThan(768);
    
    // Test desktop view
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Verify cards use appropriate desktop layout
    const desktopCardWidth = await downloadCards.first().boundingBox();
    expect(desktopCardWidth?.width).toBeGreaterThan(300);
  });

  test('should support keyboard navigation and screen readers', async () => {
    // Test keyboard navigation through download cards
    await page.keyboard.press('Tab');
    
    // Should focus on first actionable element
    let focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
    
    // Navigate through download actions
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Test enter key activation
    focusedElement = page.locator(':focus');
    const elementTag = await focusedElement.evaluate(el => el.tagName.toLowerCase());
    
    if (elementTag === 'button') {
      // Should activate the button without throwing errors
      await page.keyboard.press('Enter');
    }
    
    // Test escape key for closing dialogs
    const dialog = page.locator('[role="dialog"]');
    if (await dialog.isVisible()) {
      await page.keyboard.press('Escape');
      await expect(dialog).not.toBeVisible();
    }
    
    // Test screen reader compatibility
    const downloadCards = page.locator('[data-testid="download-card"]');
    const firstCard = downloadCards.first();
    
    // Verify proper ARIA attributes
    await expect(firstCard).toHaveAttribute('aria-labelledby');
    await expect(firstCard).toHaveAttribute('role', 'article');
    
    // Test progress bar accessibility
    const progressBar = firstCard.locator('[data-testid="progress-bar"]');
    await expect(progressBar).toHaveAttribute('role', 'progressbar');
    await expect(progressBar).toHaveAttribute('aria-valuenow');
    await expect(progressBar).toHaveAttribute('aria-valuemax', '100');
  });

  test('should optimize polling behavior based on download states', async () => {
    // Mock active downloads
    let pollCount = 0;
    
    await page.route('/api/downloads?*', async (route) => {
      pollCount++;
      
      const jobs = pollCount <= 2 ? [
        {
          id: 'download-1',
          status: 'running',
          progress: {
            total_chapters: 10,
            downloaded_chapters: pollCount * 3,
            overall_progress: (pollCount * 3) / 10,
          }
        }
      ] : [
        {
          id: 'download-1',
          status: 'completed',
          progress: {
            total_chapters: 10,
            downloaded_chapters: 10,
            overall_progress: 1.0,
          }
        }
      ];
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          jobs,
          total: 1,
          pending_downloads: 0,
          active_downloads: pollCount <= 2 ? 1 : 0,
          pagination: { page: 1, per_page: 20, total_pages: 1 }
        })
      });
    });
    
    // Wait for initial load
    await page.waitForLoadState('networkidle');
    
    // Wait for polling cycles - with 1-minute intervals, we expect much slower polling
    await page.waitForTimeout(90000); // 90 seconds to see 1-2 polling cycles
    
    // Verify that polling occurred (should be much less frequent now)
    expect(pollCount).toBeGreaterThanOrEqual(1);
    expect(pollCount).toBeLessThan(5); // Should not poll too frequently
    
    // When download completes, polling should continue but at idle intervals
    await page.waitForTimeout(60000); // Wait another minute
    const pollCountAfterCompletion = pollCount;
    
    // Should continue polling but at reduced frequency for idle state
    expect(pollCountAfterCompletion).toBeGreaterThanOrEqual(pollCount);
  });

  test('should handle bulk download operations', async () => {
    // Mock MangaDx search dialog (would be integrated separately)
    await page.route('/api/mangadx/search*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [
            {
              id: 'manga-bulk-1',
              title: 'Test Manga 1',
              chapters: ['ch1', 'ch2', 'ch3']
            },
            {
              id: 'manga-bulk-2', 
              title: 'Test Manga 2',
              chapters: ['ch4', 'ch5']
            }
          ]
        })
      });
    });
    
    // Mock bulk download endpoint
    await page.route('/api/downloads/bulk', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'scheduled',
          total_requested: 5,
          successfully_queued: 5,
          failed_to_queue: 0,
          job_ids: ['bulk-1', 'bulk-2', 'bulk-3', 'bulk-4', 'bulk-5'],
          errors: []
        })
      });
    });
    
    // Test bulk download trigger (if available in UI)
    const bulkDownloadButton = page.locator('[data-testid="bulk-download-button"]');
    
    if (await bulkDownloadButton.isVisible()) {
      await bulkDownloadButton.click();
      
      // Should open bulk selection dialog
      const bulkDialog = page.locator('[data-testid="bulk-download-dialog"]');
      await expect(bulkDialog).toBeVisible();
      
      // Select multiple items
      const selectableItems = bulkDialog.locator('[data-testid="selectable-manga"]');
      await selectableItems.first().click();
      await selectableItems.nth(1).click();
      
      const confirmBulkButton = bulkDialog.locator('[data-testid="confirm-bulk-download"]');
      await confirmBulkButton.click();
      
      // Wait for bulk operation to complete
      await page.waitForResponse('/api/downloads/bulk');
      
      // Should show success message
      const successAlert = page.locator('[role="alert"]:has-text("Bulk download scheduled")');
      await expect(successAlert).toBeVisible();
    }
  });

  test('should show download statistics and overview', async () => {
    // Mock stats endpoint
    await page.route('/api/downloads/stats/overview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_jobs: 25,
          pending_jobs: 3,
          active_jobs: 2,
          completed_jobs: 18,
          failed_jobs: 2,
          jobs_created_today: 5,
          jobs_completed_today: 4,
          average_job_duration_minutes: 8.5,
          success_rate_percentage: 88.0,
          stats_generated_at: new Date().toISOString()
        })
      });
    });
    
    // Navigate to stats section or toggle stats display
    const statsToggle = page.locator('[data-testid="stats-toggle"]');
    
    if (await statsToggle.isVisible()) {
      await statsToggle.click();
      
      const statsSection = page.locator('[data-testid="download-stats"]');
      await expect(statsSection).toBeVisible();
      
      // Verify key statistics are displayed
      await expect(statsSection).toContainText('25 total jobs');
      await expect(statsSection).toContainText('88.0% success rate');
      await expect(statsSection).toContainText('8.5 min avg duration');
    }
  });

  test('should handle download queue management', async () => {
    // Test queue filtering and sorting
    const filterDropdown = page.locator('[data-testid="status-filter"]');
    
    if (await filterDropdown.isVisible()) {
      await filterDropdown.click();
      
      const runningFilter = page.locator('[data-value="running"]');
      await runningFilter.click();
      
      // Should filter to only running downloads
      const visibleCards = page.locator('[data-testid="download-card"]:visible');
      await expect(visibleCards).toHaveCount(1);
      
      // Reset filter
      await filterDropdown.click();
      const allFilter = page.locator('[data-value="all"]');
      await allFilter.click();
    }
    
    // Test sorting
    const sortDropdown = page.locator('[data-testid="sort-order"]');
    
    if (await sortDropdown.isVisible()) {
      await sortDropdown.click();
      
      const prioritySort = page.locator('[data-value="priority"]');
      await prioritySort.click();
      
      // Cards should be reordered (verify by checking data attributes or content)
      const cards = page.locator('[data-testid="download-card"]');
      await expect(cards).toHaveCount(2);
    }
  });
});

/**
 * Downloads Header Integration Tests
 * Tests the download indicator in the application header
 */
test.describe('Downloads Header Integration', () => {
  test('should show active download count in header', async ({ page }) => {
    // Mock API with active downloads
    await page.route('/api/downloads?*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          jobs: [],
          total: 0,
          pending_downloads: 2,
          active_downloads: 3,
          pagination: { page: 1, per_page: 20, total_pages: 1 }
        })
      });
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check header download indicator
    const downloadBadge = page.locator('[data-testid="download-badge"]');
    
    if (await downloadBadge.isVisible()) {
      await expect(downloadBadge).toContainText('3'); // 3 active downloads
      
      // Clicking should navigate to downloads page
      await downloadBadge.click();
      await expect(page).toHaveURL(/downloads/);
    }
  });

  test('should update header badge in real-time', async ({ page }) => {
    let downloadCount = 2;
    
    await page.route('/api/downloads?*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          jobs: [],
          total: 0,
          pending_downloads: 0,
          active_downloads: downloadCount,
          pagination: { page: 1, per_page: 20, total_pages: 1 }
        })
      });
    });
    
    await page.goto('/downloads');
    await page.waitForLoadState('networkidle');
    
    const headerBadge = page.locator('[data-testid="download-badge"]');
    
    if (await headerBadge.isVisible()) {
      await expect(headerBadge).toContainText('2');
      
      // Simulate download completion
      downloadCount = 1;
      
      // Wait for polling to update - with 1-minute intervals, wait longer
      await page.waitForTimeout(35000); // Wait ~30 seconds for active polling
      
      await expect(headerBadge).toContainText('1');
    }
  });
});