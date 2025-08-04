import { test, expect, Page } from '@playwright/test';

test.describe('Reader Smoke Tests', () => {
  // Use real test chapter ID from test data
  const TEST_CHAPTER_ID = '5e331adb-4a29-4e96-97fb-519d6e95171a';
  
  // Mock chapter data for testing
  const mockChapterInfo = {
    id: TEST_CHAPTER_ID,
    series_id: '7a4892c8-4a11-404e-96ad-e69edeb8244e',
    series_title: 'Test Manga Series',
    chapter_number: 1,
    volume_number: 1,
    title: 'First Chapter',
    page_count: 5,
    is_read: false,
    last_read_page: 0,
    read_at: null,
    file_size: 1024000,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  // Helper function to setup API mocks
  async function setupReaderMocks(page: Page) {
    // Mock chapter info endpoint
    await page.route(`**/api/reader/chapter/${TEST_CHAPTER_ID}/info`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChapterInfo),
      });
    });

    // Mock page image endpoints with simple test images
    for (let i = 0; i < mockChapterInfo.page_count; i++) {
      await page.route(`**/api/reader/chapter/${TEST_CHAPTER_ID}/page/${i}`, async (route) => {
        // Return a simple 1x1 PNG for testing
        const pngBuffer = Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
          'base64'
        );
        await route.fulfill({
          status: 200,
          contentType: 'image/png',
          body: pngBuffer,
          headers: {
            'Content-Length': pngBuffer.length.toString(),
            'Cache-Control': 'public, max-age=3600',
          },
        });
      });
    }

    // Mock progress update endpoint
    await page.route(`**/api/reader/chapter/${TEST_CHAPTER_ID}/progress`, async (route) => {
      if (route.request().method() === 'PUT') {
        const requestBody = await route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: mockChapterInfo.id,
            last_read_page: requestBody.last_read_page,
            is_read:
              requestBody.is_read || requestBody.last_read_page >= mockChapterInfo.page_count - 1,
            read_at:
              requestBody.is_read || requestBody.last_read_page >= mockChapterInfo.page_count - 1
                ? new Date().toISOString()
                : null,
          }),
        });
      } else {
        await route.abort();
      }
    });
  }

  test.beforeEach(async ({ page }) => {
    // Setup mocks before each test
    await setupReaderMocks(page);
  });

  test('should load reader page and display first page', async ({ page }) => {
    // Navigate to reader page
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);

    // Wait for loading to complete
    await expect(page.getByText('Loading chapter...')).toBeVisible();
    await expect(page.getByText('Loading chapter...')).not.toBeVisible({ timeout: 10000 });

    // Check that the reader UI loads
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Verify series and chapter information in header
    await expect(page.getByText('Test Manga Series')).toBeVisible();
    await expect(page.getByText('Chapter 1 - First Chapter')).toBeVisible();

    // Verify page counter components
    await expect(page.getByText('/ 5')).toBeVisible();
    await expect(page.locator('input[value="1"]')).toBeVisible();

    // Verify progress bar exists
    await expect(page.locator('[role="progressbar"]')).toBeVisible();
  });

  test('should navigate pages using next/previous buttons', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Click next page button
    await page
      .getByRole('button')
      .filter({ has: page.locator('svg').first() })
      .last()
      .click();

    // Verify we're on page 2
    await expect(page.getByText('2 / 5')).toBeVisible();
    await expect(page.locator('img[alt*="Page 2"]')).toBeVisible();

    // Click previous page button
    await page
      .getByRole('button')
      .filter({ has: page.locator('svg').first() })
      .first()
      .click();

    // Verify we're back on page 1
    await expect(page.getByText('1 / 5')).toBeVisible();
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible();
  });

  test('should navigate pages using keyboard shortcuts', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Use right arrow key to go to next page
    await page.keyboard.press('ArrowRight');
    await expect(page.getByText('2 / 5')).toBeVisible();
    await expect(page.locator('img[alt*="Page 2"]')).toBeVisible();

    // Use left arrow key to go to previous page
    await page.keyboard.press('ArrowLeft');
    await expect(page.getByText('1 / 5')).toBeVisible();
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible();

    // Use spacebar to go to next page
    await page.keyboard.press('Space');
    await expect(page.getByText('2 / 5')).toBeVisible();

    // Use 'a' key to go to previous page (alternative shortcut)
    await page.keyboard.press('a');
    await expect(page.getByText('1 / 5')).toBeVisible();
  });

  test('should navigate using image click zones', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    const image = page.locator('img[alt*="Page 1"]');
    const bbox = await image.boundingBox();

    if (bbox) {
      // Click on right side of image to go to next page
      await page.mouse.click(bbox.x + bbox.width * 0.75, bbox.y + bbox.height / 2);
      await expect(page.getByText('2 / 5')).toBeVisible();

      // Click on left side of image to go to previous page
      const image2 = page.locator('img[alt*="Page 2"]');
      const bbox2 = await image2.boundingBox();
      if (bbox2) {
        await page.mouse.click(bbox2.x + bbox2.width * 0.25, bbox2.y + bbox2.height / 2);
        await expect(page.getByText('1 / 5')).toBeVisible();
      }
    }
  });

  test('should show loading states when navigating pages', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Add a delay to the page 2 request to see loading state
    await page.route('**/api/reader/chapter/${TEST_CHAPTER_ID}/page/1', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500)); // 500ms delay
      const pngBuffer = Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
        'base64'
      );
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: pngBuffer,
      });
    });

    // Navigate to page 2
    await page.keyboard.press('ArrowRight');

    // Check for loading spinner
    await expect(page.locator('.animate-spin')).toBeVisible();

    // Wait for loading to complete
    await expect(page.locator('.animate-spin')).not.toBeVisible({ timeout: 2000 });
    await expect(page.getByText('2 / 5')).toBeVisible();
  });

  test('should update reading progress', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Track API calls for progress updates
    const progressCalls: any[] = [];
    await page.route('**/api/reader/chapter/${TEST_CHAPTER_ID}/progress', async (route) => {
      if (route.request().method() === 'PUT') {
        const requestBody = await route.request().postDataJSON();
        progressCalls.push(requestBody);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: mockChapterInfo.id,
            last_read_page: requestBody.last_read_page,
            is_read:
              requestBody.is_read || requestBody.last_read_page >= mockChapterInfo.page_count - 1,
            read_at:
              requestBody.is_read || requestBody.last_read_page >= mockChapterInfo.page_count - 1
                ? new Date().toISOString()
                : null,
          }),
        });
      }
    });

    // Navigate through pages
    await page.keyboard.press('ArrowRight'); // Page 2
    await page.keyboard.press('ArrowRight'); // Page 3

    // Wait a bit for progress updates
    await page.waitForTimeout(500);

    // Verify progress API calls were made
    expect(progressCalls.length).toBeGreaterThan(0);
    expect(progressCalls[progressCalls.length - 1].last_read_page).toBe(2); // 0-based indexing
  });

  test('should toggle UI visibility with U key', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Initially UI should be visible
    await expect(page.getByText('Test Manga Series')).toBeVisible();
    await expect(page.getByText('1 / 5')).toBeVisible();

    // Press U to hide UI
    await page.keyboard.press('u');

    // UI should be hidden (check with timeout as it might animate)
    await expect(page.getByText('Test Manga Series')).not.toBeVisible({ timeout: 2000 });
    await expect(page.getByText('1 / 5')).not.toBeVisible({ timeout: 2000 });

    // Press U again to show UI
    await page.keyboard.press('u');

    // UI should be visible again
    await expect(page.getByText('Test Manga Series')).toBeVisible();
    await expect(page.getByText('1 / 5')).toBeVisible();
  });

  test('should go back to library when clicking back button', async ({ page }) => {
    // Mock library page
    await page.route('**/library', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body><h1>Library Page</h1></body></html>',
      });
    });

    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Click back button
    await page.getByRole('button', { name: 'Back' }).click();

    // Should navigate back (browser history)
    // Note: In real tests, this would go back to the actual library page
    await expect(page).not.toHaveURL(`/reader/${TEST_CHAPTER_ID}`);
  });

  test('should handle keyboard shortcut for going home and end', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Go to page 3 first
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await expect(page.getByText('3 / 5')).toBeVisible();

    // Press Home to go to first page
    await page.keyboard.press('Home');
    await expect(page.getByText('1 / 5')).toBeVisible();
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible();

    // Press End to go to last page
    await page.keyboard.press('End');
    await expect(page.getByText('5 / 5')).toBeVisible();
    await expect(page.locator('img[alt*="Page 5"]')).toBeVisible();
  });

  test('should disable navigation buttons at boundaries', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // On first page, previous button should be disabled
    const prevButton = page
      .getByRole('button')
      .filter({ has: page.locator('svg').first() })
      .first();
    await expect(prevButton).toBeDisabled();

    // Navigate to last page
    await page.keyboard.press('End');
    await expect(page.getByText('5 / 5')).toBeVisible();

    // On last page, next button should be disabled
    const nextButton = page
      .getByRole('button')
      .filter({ has: page.locator('svg').first() })
      .last();
    await expect(nextButton).toBeDisabled();
  });

  test('should show keyboard shortcuts help', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Check that keyboard shortcuts are visible in UI
    await expect(page.getByText('← → : Navigate pages')).toBeVisible();
    await expect(page.getByText('Space: Next page')).toBeVisible();
    await expect(page.getByText('F: Toggle fit mode')).toBeVisible();
    await expect(page.getByText('U: Toggle UI')).toBeVisible();
    await expect(page.getByText('Esc: Exit reader')).toBeVisible();
  });

  test('should handle error state when chapter not found', async ({ page }) => {
    // Mock error response for non-existent chapter
    await page.route('**/api/reader/chapter/non-existent/info', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Chapter not found: non-existent' }),
      });
    });

    await page.goto('/reader/non-existent');

    // Should show error state
    await expect(page.getByText(/Error:/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Chapter not found/)).toBeVisible();

    // Should show back button
    await expect(page.getByRole('button', { name: 'Go Back' })).toBeVisible();
  });

  test('should be accessible via keyboard navigation', async ({ page }) => {
    await page.goto(`/reader/${TEST_CHAPTER_ID}`);
    await expect(page.locator('img[alt*="Page 1"]')).toBeVisible({ timeout: 10000 });

    // Test focus management for navigation buttons
    const backButton = page.getByRole('button', { name: 'Back' });
    await backButton.focus();
    await expect(backButton).toBeFocused();

    // Tab to next focusable element
    await page.keyboard.press('Tab');
    // Settings button should be focused (if implemented)

    // Tab to navigation buttons
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should be able to activate buttons with Enter/Space
    const nextButton = page
      .getByRole('button')
      .filter({ has: page.locator('svg').first() })
      .last();
    await nextButton.focus();
    await expect(nextButton).toBeFocused();

    await page.keyboard.press('Enter');
    await expect(page.getByText('2 / 5')).toBeVisible();
  });
});
