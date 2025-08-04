import { test, expect } from '@playwright/test';

test.describe('Reading Progress Visibility - R2 Exit Criteria', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Navigate to the application
    await page.goto('/');

    // Wait for the application to load
    await expect(page.locator('h1')).toContainText('KireMisu');
  });

  test('User can see series progress on library page', async ({ page }) => {
    // Navigate to library
    await page.click('text=Library');
    await expect(page).toHaveURL('/library');

    // Wait for series to load
    await page.waitForSelector('[data-testid="series-card"]', { timeout: 10000 });

    // Verify series cards show progress information
    const seriesCards = page.locator('[data-testid="series-card"]');
    const firstCard = seriesCards.first();

    // Check for progress bar
    await expect(firstCard.locator('[data-testid="progress-bar"]')).toBeVisible();

    // Check for progress text (e.g., "5/10 chapters read")
    await expect(firstCard.locator('text=/\\d+\\/\\d+ chapters/')).toBeVisible();

    // Check for progress percentage
    await expect(firstCard.locator('text=/%/')).toBeVisible();
  });

  test('User can see chapter progress in series detail view', async ({ page }) => {
    // Navigate to library and select a series
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();
    await firstSeries.click();

    // Wait for series detail page to load
    await page.waitForSelector('[data-testid="chapter-list"]');

    // Verify chapter list shows individual progress
    const chapters = page.locator('[data-testid^="chapter-"]');
    const firstChapter = chapters.first();

    // Check for individual chapter progress indicators
    await expect(firstChapter.locator('[data-testid="chapter-progress-bar"]')).toBeVisible();

    // Check for read status indicators
    await expect(firstChapter.locator('[data-testid="mark-read-button"]')).toBeVisible();

    // Verify progress text is visible (e.g., "85%" or "Complete")
    await expect(firstChapter.locator('text=/%|Complete/')).toBeVisible();
  });

  test('User can mark chapters as read and see progress update in real-time', async ({ page }) => {
    // Navigate to library and select a series
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();

    // Note initial progress
    const initialProgress = await firstSeries
      .locator('[data-testid="progress-percentage"]')
      .textContent();

    await firstSeries.click();
    await page.waitForSelector('[data-testid="chapter-list"]');

    // Find first unread chapter
    const unreadChapter = page
      .locator('[data-testid^="chapter-"] [data-testid="mark-read-button"]:has-text("Mark Read")')
      .first();

    if ((await unreadChapter.count()) > 0) {
      // Mark chapter as read
      await unreadChapter.click();

      // Wait for API call to complete
      await page.waitForResponse(
        (response) => response.url().includes('/mark-read') && response.status() === 200
      );

      // Verify button text changed
      await expect(unreadChapter).toHaveText(/Read|✓/);

      // Navigate back to library to check series progress update
      await page.click('text=Library');
      await page.waitForSelector('[data-testid="series-card"]');

      // Verify series progress updated
      const updatedProgress = await firstSeries
        .locator('[data-testid="progress-percentage"]')
        .textContent();
      expect(updatedProgress).not.toBe(initialProgress);
    }
  });

  test('User can see reading progress in dashboard stats', async ({ page }) => {
    // Navigate to dashboard/home page
    await page.goto('/');

    // Wait for dashboard stats to load
    await page.waitForSelector('[data-testid="dashboard-stats"]');

    // Verify overall statistics are visible
    await expect(page.locator('[data-testid="total-series"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-chapters"]')).toBeVisible();
    await expect(page.locator('[data-testid="read-chapters"]')).toBeVisible();

    // Verify overall progress percentage is displayed
    await expect(page.locator('[data-testid="overall-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="overall-progress"]')).toContainText('%');

    // Verify series breakdown is visible
    await expect(page.locator('[data-testid="series-breakdown"]')).toBeVisible();
    await expect(page.locator('text=Completed:')).toBeVisible();
    await expect(page.locator('text=In Progress:')).toBeVisible();
    await expect(page.locator('text=Unread:')).toBeVisible();

    // Verify reading streak is displayed
    await expect(page.locator('[data-testid="reading-streak"]')).toBeVisible();
    await expect(page.locator('[data-testid="reading-streak"]')).toContainText('day');
  });

  test('User can see recent reading activity on dashboard', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');
    await page.waitForSelector('[data-testid="dashboard-stats"]');

    // Check for recent reads section
    const recentReads = page.locator('[data-testid="recent-reads"]');
    await expect(recentReads).toBeVisible();

    // If there are recent reads, verify they show proper information
    const recentItems = recentReads.locator('.recent-read');
    const itemCount = await recentItems.count();

    if (itemCount > 0) {
      const firstItem = recentItems.first();
      // Should show series title and chapter info
      await expect(firstItem).toContainText(/Chapter|Ch\./);
    }
  });

  test('Progress bars respond correctly to different progress levels', async ({ page }) => {
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const seriesCards = page.locator('[data-testid="series-card"]');
    const cardCount = await seriesCards.count();

    for (let i = 0; i < Math.min(cardCount, 3); i++) {
      const card = seriesCards.nth(i);
      const progressBar = card.locator('[data-testid="progress-bar"]');
      const progressFill = progressBar.locator('[data-testid="progress-fill"]');

      // Verify progress bar is visible
      await expect(progressBar).toBeVisible();

      // Verify progress fill has appropriate width
      const progressText = await card.locator('[data-testid="progress-percentage"]').textContent();
      if (progressText) {
        const percentage = parseInt(progressText.replace('%', ''));

        // Get the actual width of the progress fill
        const fillWidth = await progressFill.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return style.width;
        });

        // Progress fill should have some width if percentage > 0
        if (percentage > 0) {
          expect(fillWidth).not.toBe('0px');
        }
      }
    }
  });

  test('Mark read button states are visually distinct', async ({ page }) => {
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();
    await firstSeries.click();

    await page.waitForSelector('[data-testid="chapter-list"]');

    // Look for both read and unread buttons
    const readButtons = page.locator('[data-testid="mark-read-button"]:has-text("Read")');
    const unreadButtons = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")');

    // Verify read buttons have distinct styling
    if ((await readButtons.count()) > 0) {
      const readButton = readButtons.first();
      await expect(readButton).toHaveClass(/read/);
    }

    // Verify unread buttons have distinct styling
    if ((await unreadButtons.count()) > 0) {
      const unreadButton = unreadButtons.first();
      await expect(unreadButton).toHaveClass(/unread/);
    }
  });

  test('Progress persists across page refreshes', async ({ page }) => {
    // Navigate to library and note progress
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();
    const initialProgress = await firstSeries
      .locator('[data-testid="progress-percentage"]')
      .textContent();

    // Refresh the page
    await page.reload();
    await page.waitForSelector('[data-testid="series-card"]');

    // Verify progress is the same
    const refreshedProgress = await firstSeries
      .locator('[data-testid="progress-percentage"]')
      .textContent();
    expect(refreshedProgress).toBe(initialProgress);
  });

  test('Progress is visible in reader interface', async ({ page }) => {
    // Navigate to library and open a chapter
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();
    await firstSeries.click();

    await page.waitForSelector('[data-testid="chapter-list"]');

    // Click on first chapter to open reader
    const firstChapter = page.locator('[data-testid^="chapter-"]').first();
    const chapterLink = firstChapter.locator('a, button').first();
    await chapterLink.click();

    // Wait for reader to load
    await page.waitForSelector('[data-testid="manga-reader"]', { timeout: 10000 });

    // Verify progress information is visible in reader
    await expect(page.locator('text=Progress')).toBeVisible();
    await expect(page.locator('text=/%/')).toBeVisible();

    // Verify page counter (e.g., "1 / 20")
    await expect(page.locator('text=/\\d+ \\/ \\d+/')).toBeVisible();
  });

  test('Navigation between chapters updates progress correctly', async ({ page }) => {
    // Open reader
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();
    await firstSeries.click();

    await page.waitForSelector('[data-testid="chapter-list"]');

    const firstChapter = page.locator('[data-testid^="chapter-"]').first();
    const chapterLink = firstChapter.locator('a, button').first();
    await chapterLink.click();

    await page.waitForSelector('[data-testid="manga-reader"]');

    // Navigate through pages to update progress
    const pageCounter = page.locator('text=/\\d+ \\/ \\d+/');
    const initialPage = await pageCounter.textContent();

    // Navigate to next page using keyboard
    await page.keyboard.press('ArrowRight');

    // Wait for page counter to update
    await page.waitForFunction(
      (initial) => {
        const current = document.querySelector('text=/\\d+ \\/ \\d+/')?.textContent;
        return current && current !== initial;
      },
      initialPage,
      { timeout: 5000 }
    );

    // Verify progress percentage updated
    const progressElement = page.locator('text=/%/');
    await expect(progressElement).toBeVisible();
  });

  test('Accessibility - Progress information is screen reader friendly', async ({ page }) => {
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const firstSeries = page.locator('[data-testid="series-card"]').first();

    // Check for proper ARIA labels on progress elements
    const progressBar = firstSeries.locator('[data-testid="progress-bar"]');

    // Progress bars should have appropriate aria attributes
    await expect(progressBar).toHaveAttribute('role', 'progressbar');

    // Mark read buttons should have descriptive labels
    await firstSeries.click();
    await page.waitForSelector('[data-testid="chapter-list"]');

    const markReadButton = page.locator('[data-testid="mark-read-button"]').first();
    const ariaLabel = await markReadButton.getAttribute('aria-label');
    expect(ariaLabel).toMatch(/Mark as (read|unread)/);
  });

  test('Responsive design - Progress visible on different screen sizes', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    const progressBar = page.locator('[data-testid="progress-bar"]').first();
    await expect(progressBar).toBeVisible();

    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(progressBar).toBeVisible();

    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(progressBar).toBeVisible();

    // Verify progress is still functional on mobile
    const markReadButton = page.locator('[data-testid="mark-read-button"]').first();
    if ((await markReadButton.count()) > 0) {
      await expect(markReadButton).toBeVisible();

      // Button should be tappable on mobile
      const boundingBox = await markReadButton.boundingBox();
      expect(boundingBox?.width).toBeGreaterThan(44); // Minimum touch target size
      expect(boundingBox?.height).toBeGreaterThan(44);
    }
  });

  test('Performance - Progress loading does not block UI', async ({ page }) => {
    // Measure time to interactive
    const startTime = Date.now();

    await page.click('text=Library');

    // Wait for initial UI to be visible (should be fast)
    await page.waitForSelector('[data-testid="series-card"]', { timeout: 3000 });
    const uiLoadTime = Date.now() - startTime;

    // UI should load quickly even if progress is still loading
    expect(uiLoadTime).toBeLessThan(3000);

    // Progress data can load after initial UI
    await page.waitForSelector('[data-testid="progress-bar"]', { timeout: 10000 });

    // Verify no blocking loading states
    const loadingSpinners = page.locator('.animate-spin, .loading, [data-testid="loading"]');
    const spinnerCount = await loadingSpinners.count();

    // Should not have persistent loading states
    if (spinnerCount > 0) {
      await expect(loadingSpinners.first()).not.toBeVisible({ timeout: 5000 });
    }
  });

  test('Error handling - Graceful degradation when progress data fails', async ({ page }) => {
    // Intercept and fail progress API calls
    await page.route('**/api/series/*/progress', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.click('text=Library');
    await page.waitForSelector('[data-testid="series-card"]');

    // UI should still be functional even if progress fails
    const seriesCard = page.locator('[data-testid="series-card"]').first();
    await expect(seriesCard).toBeVisible();

    // Should show some fallback or error state for progress
    // But core functionality should remain
    await seriesCard.click();

    // Should still be able to navigate to series detail
    await page.waitForSelector('[data-testid="chapter-list"]');

    // Clear the route intercept
    await page.unroute('**/api/series/*/progress');
  });
});
