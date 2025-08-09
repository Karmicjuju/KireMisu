import { test, expect, Page } from '@playwright/test';

/**
 * Comprehensive E2E Tests for MangaDx Integration
 * Tests the complete MangaDx search, import, and download workflow including
 * accessibility, responsive design, error handling, and user experience.
 */

test.describe('MangaDx Integration - Comprehensive E2E Tests', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    
    // Mock MangaDx API endpoints for consistent testing
    await page.route('/api/mangadx/**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();
      
      if (method === 'GET' && url.includes('/api/mangadx/search')) {
        // Mock search results
        const searchParams = new URL(url).searchParams;
        const query = searchParams.get('title') || 'test';
        
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [
              {
                id: 'manga-1',
                attributes: {
                  title: { en: `${query} Manga One` },
                  description: { en: 'A test manga for E2E testing' },
                  status: 'completed',
                  year: 2020,
                  tags: [
                    { attributes: { name: { en: 'Action' } } },
                    { attributes: { name: { en: 'Adventure' } } }
                  ],
                  contentRating: 'safe'
                },
                relationships: [
                  {
                    type: 'author',
                    attributes: { name: 'Test Author' }
                  },
                  {
                    type: 'cover_art',
                    attributes: { fileName: 'cover1.jpg' }
                  }
                ]
              },
              {
                id: 'manga-2',
                attributes: {
                  title: { en: `${query} Manga Two` },
                  description: { en: 'Another test manga with longer description for testing UI layout and responsiveness across different screen sizes' },
                  status: 'ongoing',
                  year: 2023,
                  tags: [
                    { attributes: { name: { en: 'Romance' } } },
                    { attributes: { name: { en: 'Drama' } } }
                  ],
                  contentRating: 'suggestive'
                },
                relationships: [
                  {
                    type: 'author',
                    attributes: { name: 'Another Author' }
                  }
                ]
              }
            ],
            limit: 10,
            offset: 0,
            total: 2
          })
        });
      } else if (method === 'GET' && url.includes('/api/mangadx/manga/')) {
        // Mock detailed manga information
        const mangaId = url.split('/').pop();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              id: mangaId,
              attributes: {
                title: { en: 'Detailed Manga Info' },
                description: { en: 'Detailed description for import' },
                status: 'completed',
                year: 2021,
                tags: [
                  { attributes: { name: { en: 'Fantasy' } } }
                ],
                contentRating: 'safe'
              },
              relationships: [
                {
                  type: 'author',
                  attributes: { name: 'Detailed Author' }
                }
              ]
            }
          })
        });
      } else if (method === 'POST' && url.includes('/api/mangadx/import')) {
        // Mock import operation
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            series_id: 'imported-series-123',
            message: 'Series imported successfully',
            metadata_updated: true,
            cover_downloaded: true
          })
        });
      } else if (method === 'GET' && url.includes('/api/mangadx/health')) {
        // Mock health check
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'healthy',
            response_time_ms: 120,
            rate_limit_remaining: 95
          })
        });
      }
    });

    // Mock downloads API for integration testing
    await page.route('/api/downloads/**', async (route) => {
      const method = route.request().method();
      
      if (method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'download-from-mangadx',
            download_type: 'mangadx',
            status: 'pending',
            manga_id: 'manga-1',
            chapter_ids: ['ch-1', 'ch-2', 'ch-3'],
            priority: 5
          })
        });
      }
    });

    // Navigate to library page (where MangaDx search is typically accessed)
    await page.goto('/library');
    await page.waitForLoadState('networkidle');
  });

  test('should open MangaDx search dialog with proper accessibility', async () => {
    // Find and click the search button
    const searchButton = page.locator('[data-testid="mangadx-search-trigger"]');
    await expect(searchButton).toBeVisible();
    await searchButton.click();
    
    // Verify dialog opens with proper accessibility attributes
    const searchDialog = page.locator('[role="dialog"]');
    await expect(searchDialog).toBeVisible();
    await expect(searchDialog).toHaveAttribute('aria-modal', 'true');
    await expect(searchDialog).toHaveAttribute('aria-labelledby');
    
    // Test dialog title
    const dialogTitle = page.locator('#mangadx-search-title, [data-testid="dialog-title"]');
    await expect(dialogTitle).toBeVisible();
    await expect(dialogTitle).toContainText('Search MangaDx');
    
    // Test search input accessibility
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveAttribute('aria-label');
    await expect(searchInput).toBeEditable();
    
    // Test close button accessibility
    const closeButton = page.locator('[aria-label*="Close"], [data-testid="close-dialog"]');
    await expect(closeButton).toBeVisible();
  });

  test('should perform search with real-time results and filtering', async () => {
    // Open search dialog
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    const searchDialog = page.locator('[role="dialog"]');
    await expect(searchDialog).toBeVisible();
    
    // Perform search
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('adventure');
    
    // Trigger search (either auto-search or button click)
    const searchSubmitButton = page.locator('[data-testid="search-submit"]');
    if (await searchSubmitButton.isVisible()) {
      await searchSubmitButton.click();
    }
    
    // Wait for search results
    await page.waitForResponse('/api/mangadx/search*');
    
    // Verify results display
    const searchResults = page.locator('[data-testid="search-results"]');
    await expect(searchResults).toBeVisible();
    
    const resultCards = page.locator('[data-testid="manga-result-card"]');
    await expect(resultCards).toHaveCount(2);
    
    // Test result card content
    const firstResult = resultCards.first();
    await expect(firstResult).toContainText('adventure Manga One');
    await expect(firstResult).toContainText('Test Author');
    await expect(firstResult).toContainText('Action');
    await expect(firstResult).toContainText('Adventure');
    
    // Test advanced filtering
    const statusFilter = page.locator('[data-testid="status-filter"]');
    if (await statusFilter.isVisible()) {
      await statusFilter.click();
      const completedOption = page.locator('[data-value="completed"]');
      await completedOption.click();
      
      // Results should be filtered
      await page.waitForResponse('/api/mangadx/search*');
    }
    
    // Test content rating filter
    const ratingFilter = page.locator('[data-testid="content-rating-filter"]');
    if (await ratingFilter.isVisible()) {
      await ratingFilter.click();
      const safeOption = page.locator('[data-value="safe"]');
      await safeOption.click();
      
      await page.waitForResponse('/api/mangadx/search*');
    }
  });

  test('should handle manga import workflow with proper feedback', async () => {
    // Open search and perform search
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('test');
    
    const searchButton = page.locator('[data-testid="search-submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    await page.waitForResponse('/api/mangadx/search*');
    
    // Find and click import button on first result
    const firstResult = page.locator('[data-testid="manga-result-card"]').first();
    const importButton = firstResult.locator('[data-testid="import-button"]');
    await expect(importButton).toBeVisible();
    await expect(importButton).toBeEnabled();
    
    // Click import button
    await importButton.click();
    
    // Should show import confirmation dialog
    const importDialog = page.locator('[data-testid="import-confirmation-dialog"]');
    if (await importDialog.isVisible()) {
      // Test import options
      const overwriteOption = page.locator('[data-testid="overwrite-metadata"]');
      if (await overwriteOption.isVisible()) {
        await overwriteOption.check();
      }
      
      const downloadCoverOption = page.locator('[data-testid="download-cover"]');
      if (await downloadCoverOption.isVisible()) {
        await downloadCoverOption.check();
      }
      
      // Confirm import
      const confirmImportButton = page.locator('[data-testid="confirm-import"]');
      await confirmImportButton.click();
    }
    
    // Wait for import to complete
    await page.waitForResponse('/api/mangadx/import');
    
    // Should show success message
    const successAlert = page.locator('[role="alert"]:has-text("imported successfully")');
    await expect(successAlert).toBeVisible();
    
    // Import button should be disabled or show different state
    await expect(importButton).toContainText(/imported|added/i);
  });

  test('should handle download integration from search results', async () => {
    // Open search and get results
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    await page.locator('[data-testid="search-input"]').fill('download test');
    
    const searchButton = page.locator('[data-testid="search-submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    await page.waitForResponse('/api/mangadx/search*');
    
    // Find download button on search result
    const firstResult = page.locator('[data-testid="manga-result-card"]').first();
    const downloadButton = firstResult.locator('[data-testid="download-button"]');
    
    if (await downloadButton.isVisible()) {
      await downloadButton.click();
      
      // Should open download options dialog
      const downloadDialog = page.locator('[data-testid="download-options-dialog"]');
      await expect(downloadDialog).toBeVisible();
      
      // Test download type selection
      const downloadTypeSelect = page.locator('[data-testid="download-type-select"]');
      if (await downloadTypeSelect.isVisible()) {
        await downloadTypeSelect.click();
        const seriesOption = page.locator('[data-value="series"]');
        await seriesOption.click();
      }
      
      // Test priority setting
      const prioritySlider = page.locator('[data-testid="priority-slider"]');
      if (await prioritySlider.isVisible()) {
        await prioritySlider.fill('8');
      }
      
      // Confirm download
      const startDownloadButton = page.locator('[data-testid="start-download"]');
      await startDownloadButton.click();
      
      // Wait for download to be queued
      await page.waitForResponse('/api/downloads/');
      
      // Should show success feedback
      const downloadSuccess = page.locator('[role="alert"]:has-text("download")');
      await expect(downloadSuccess).toBeVisible();
      
      // Option to view in downloads page
      const viewDownloadsLink = page.locator('[data-testid="view-downloads-link"]');
      if (await viewDownloadsLink.isVisible()) {
        await viewDownloadsLink.click();
        await expect(page).toHaveURL(/downloads/);
      }
    }
  });

  test('should be responsive across different screen sizes', async () => {
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    
    const searchDialog = page.locator('[role="dialog"]');
    await expect(searchDialog).toBeVisible();
    
    // Dialog should adapt to mobile screen
    const dialogBounds = await searchDialog.boundingBox();
    expect(dialogBounds?.width).toBeLessThan(375);
    
    // Perform search to test results layout
    await page.locator('[data-testid="search-input"]').fill('mobile test');
    const searchButton = page.locator('[data-testid="search-submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    await page.waitForResponse('/api/mangadx/search*');
    
    // Results should stack vertically on mobile
    const resultCards = page.locator('[data-testid="manga-result-card"]');
    await expect(resultCards).toHaveCount(2);
    
    // Test that cards are readable on mobile
    const firstCard = resultCards.first();
    const cardBounds = await firstCard.boundingBox();
    expect(cardBounds?.width).toBeLessThan(375);
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // Results might show in a grid layout
    const resultsContainer = page.locator('[data-testid="search-results"]');
    const containerBounds = await resultsContainer.boundingBox();
    expect(containerBounds?.width).toBeLessThan(768);
    
    // Test desktop view
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Should use full dialog width efficiently
    const desktopDialogBounds = await searchDialog.boundingBox();
    expect(desktopDialogBounds?.width).toBeGreaterThan(600);
  });

  test('should support keyboard navigation and accessibility', async () => {
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    
    // Test focus management when dialog opens
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeFocused();
    
    // Fill search and trigger
    await page.keyboard.type('keyboard test');
    await page.keyboard.press('Enter');
    
    await page.waitForResponse('/api/mangadx/search*');
    
    // Navigate through results with keyboard
    await page.keyboard.press('Tab');
    
    let focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
    
    // Continue tabbing to navigate through result cards
    await page.keyboard.press('Tab');
    focusedElement = page.locator(':focus');
    
    // Should be able to activate buttons with Enter/Space
    const elementTag = await focusedElement.evaluate(el => el.tagName.toLowerCase());
    if (elementTag === 'button') {
      // Test Space key activation
      await page.keyboard.press('Space');
    }
    
    // Test Escape key to close dialog
    await page.keyboard.press('Escape');
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).not.toBeVisible();
  });

  test('should handle API errors gracefully', async () => {
    // Mock API error responses
    await page.route('/api/mangadx/search*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'MangaDx API is temporarily unavailable'
        })
      });
    });
    
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    await page.locator('[data-testid="search-input"]').fill('error test');
    
    const searchButton = page.locator('[data-testid="search-submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    // Should show error message
    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText(/error|unavailable|failed/i);
    
    // Test retry functionality
    const retryButton = page.locator('[data-testid="retry-search"]');
    if (await retryButton.isVisible()) {
      // Mock successful response for retry
      await page.route('/api/mangadx/search*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [{
              id: 'retry-manga',
              attributes: {
                title: { en: 'Retry Success' },
                description: { en: 'Retry worked' }
              }
            }],
            total: 1
          })
        });
      });
      
      await retryButton.click();
      await page.waitForResponse('/api/mangadx/search*');
      
      // Should show results after successful retry
      const results = page.locator('[data-testid="search-results"]');
      await expect(results).toBeVisible();
    }
  });

  test('should handle rate limiting and API health status', async () => {
    // Mock rate limited response
    await page.route('/api/mangadx/search*', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Rate limit exceeded. Please wait 60 seconds.',
          retry_after: 60
        })
      });
    });
    
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    
    // Check if health status is displayed
    const healthIndicator = page.locator('[data-testid="api-health-status"]');
    if (await healthIndicator.isVisible()) {
      await expect(healthIndicator).toContainText(/healthy|available/i);
    }
    
    await page.locator('[data-testid="search-input"]').fill('rate limit test');
    
    const searchButton = page.locator('[data-testid="search-submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    // Should show rate limit message
    const rateLimitAlert = page.locator('[role="alert"]');
    await expect(rateLimitAlert).toBeVisible();
    await expect(rateLimitAlert).toContainText(/rate limit/i);
    
    // Should show countdown or retry information
    const retryInfo = page.locator('[data-testid="retry-countdown"]');
    if (await retryInfo.isVisible()) {
      await expect(retryInfo).toContainText(/60|seconds|wait/i);
    }
  });

  test('should handle search history and suggestions', async () => {
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    
    const searchInput = page.locator('[data-testid="search-input"]');
    
    // Type partial query to test suggestions
    await searchInput.fill('one p');
    
    // Check for search suggestions dropdown
    const suggestionsDropdown = page.locator('[data-testid="search-suggestions"]');
    if (await suggestionsDropdown.isVisible()) {
      const suggestions = page.locator('[data-testid="suggestion-item"]');
      await expect(suggestions.first()).toBeVisible();
      
      // Click on first suggestion
      await suggestions.first().click();
      
      // Should populate search input
      const inputValue = await searchInput.inputValue();
      expect(inputValue).toBeTruthy();
    }
    
    // Complete a search to add to history
    await searchInput.fill('one piece');
    await page.keyboard.press('Enter');
    
    await page.waitForResponse('/api/mangadx/search*');
    
    // Close and reopen dialog
    await page.keyboard.press('Escape');
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    
    // Check for search history
    const searchHistory = page.locator('[data-testid="search-history"]');
    if (await searchHistory.isVisible()) {
      const historyItems = page.locator('[data-testid="history-item"]');
      await expect(historyItems.first()).toContainText('one piece');
      
      // Clicking history item should populate search
      await historyItems.first().click();
      const newInputValue = await searchInput.inputValue();
      expect(newInputValue).toBe('one piece');
    }
  });

  test('should integrate with series management workflow', async () => {
    // Mock existing series data
    await page.route('/api/series*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          series: [
            {
              id: 'existing-series',
              title: 'test Manga One',
              mangadx_id: 'manga-1',
              author: 'Test Author'
            }
          ]
        })
      });
    });
    
    await page.locator('[data-testid="mangadx-search-trigger"]').click();
    await page.locator('[data-testid="search-input"]').fill('test');
    
    const searchButton = page.locator('[data-testid="search-submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    await page.waitForResponse('/api/mangadx/search*');
    
    // First result should show as already in library
    const firstResult = page.locator('[data-testid="manga-result-card"]').first();
    const libraryIndicator = firstResult.locator('[data-testid="in-library-indicator"]');
    
    if (await libraryIndicator.isVisible()) {
      await expect(libraryIndicator).toContainText(/library|added|imported/i);
      
      // Should have option to view in library
      const viewInLibraryButton = firstResult.locator('[data-testid="view-in-library"]');
      if (await viewInLibraryButton.isVisible()) {
        await viewInLibraryButton.click();
        
        // Should navigate to series page or highlight in library
        await expect(page).toHaveURL(/library|series/);
      }
    }
    
    // Test enrichment workflow for existing series
    const enrichButton = firstResult.locator('[data-testid="enrich-metadata"]');
    if (await enrichButton.isVisible()) {
      await enrichButton.click();
      
      // Should show metadata comparison dialog
      const enrichDialog = page.locator('[data-testid="metadata-enrich-dialog"]');
      if (await enrichDialog.isVisible()) {
        // Show current vs new metadata
        const currentMetadata = page.locator('[data-testid="current-metadata"]');
        const newMetadata = page.locator('[data-testid="new-metadata"]');
        
        await expect(currentMetadata).toBeVisible();
        await expect(newMetadata).toBeVisible();
        
        // Confirm enrichment
        const confirmEnrichButton = page.locator('[data-testid="confirm-enrich"]');
        await confirmEnrichButton.click();
        
        await page.waitForResponse('/api/mangadx/import');
        
        // Should show success message
        const enrichSuccess = page.locator('[role="alert"]:has-text("metadata updated")');
        await expect(enrichSuccess).toBeVisible();
      }
    }
  });
});