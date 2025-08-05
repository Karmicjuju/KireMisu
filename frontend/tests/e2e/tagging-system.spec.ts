/**
 * End-to-end tests for the tagging system functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Tagging System', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the library page
    await page.goto('/library');
    await page.waitForLoadState('networkidle');
  });

  test('can create and manage tags', async ({ page }) => {
    // Navigate to first series
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    await firstSeriesCard.click();
    
    // Wait for series detail page to load
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Create a new tag by typing in the input
    const tagInput = page.locator('[data-testid="tag-input"]');
    await tagInput.fill('action');
    
    // Wait for autocomplete suggestions and click create option
    await page.waitForSelector('[data-testid="tag-suggestion-create"]');
    await page.locator('[data-testid="tag-suggestion-create"]').click();
    
    // Add another existing tag
    await tagInput.fill('fantasy');
    await page.locator('[data-testid="tag-suggestion-create"]').click();
    
    // Save the changes
    const saveButton = page.locator('button:has-text("Save")');
    await saveButton.click();
    
    // Verify tags are displayed
    await expect(page.locator('[data-testid="tag-chip"]:has-text("action")')).toBeVisible();
    await expect(page.locator('[data-testid="tag-chip"]:has-text("fantasy")')).toBeVisible();
  });

  test('can filter library by tags', async ({ page }) => {
    // Wait for library to load
    await page.waitForSelector('[data-testid="library-filter"]');
    
    // Open tag filter
    const tagFilterButton = page.locator('[data-testid="tag-filter-button"]');
    await tagFilterButton.click();
    
    // Select a tag to filter by
    const actionTagFilter = page.locator('[data-testid="tag-filter-option"]:has-text("action")');
    await actionTagFilter.click();
    
    // Apply filter
    const applyFilterButton = page.locator('button:has-text("Apply Filter")');
    await applyFilterButton.click();
    
    // Verify filtered results
    const seriesCards = page.locator('[data-testid="series-card"]');
    await expect(seriesCards).toHaveCount(1); // Should only show series with action tag
    
    // Verify the series has the action tag
    await expect(seriesCards.first().locator('[data-testid="tag-chip"]:has-text("action")')).toBeVisible();
  });

  test('can remove tags from series', async ({ page }) => {
    // Navigate to first series with tags
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    await firstSeriesCard.click();
    
    // Wait for series detail page to load
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Remove a tag by clicking the X button
    const removeTagButton = page.locator('[data-testid="tag-chip"]:has-text("action") button[aria-label*="Remove"]');
    await removeTagButton.click();
    
    // Save the changes
    const saveButton = page.locator('button:has-text("Save")');
    await saveButton.click();
    
    // Verify tag is removed
    await expect(page.locator('[data-testid="tag-chip"]:has-text("action")')).not.toBeVisible();
    await expect(page.locator('[data-testid="tag-chip"]:has-text("fantasy")')).toBeVisible();
  });

  test('tag autocomplete works correctly', async ({ page }) => {
    // Navigate to series detail page
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    await firstSeriesCard.click();
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Type partial tag name
    const tagInput = page.locator('[data-testid="tag-input"]');
    await tagInput.fill('fan');
    
    // Verify autocomplete suggestions appear
    await expect(page.locator('[data-testid="tag-suggestion"]:has-text("fantasy")')).toBeVisible();
    
    // Select existing tag from suggestions
    await page.locator('[data-testid="tag-suggestion"]:has-text("fantasy")').click();
    
    // Verify tag is added
    await expect(page.locator('[data-testid="selected-tag"]:has-text("fantasy")')).toBeVisible();
  });

  test('displays tag usage counts', async ({ page }) => {
    // Navigate to tag management page (if available)
    // Or verify tag usage counts in autocomplete
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    await firstSeriesCard.click();
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Type to trigger autocomplete
    const tagInput = page.locator('[data-testid="tag-input"]');
    await tagInput.fill('a');
    
    // Verify usage counts are displayed in suggestions
    const tagSuggestion = page.locator('[data-testid="tag-suggestion"]').first();
    await expect(tagSuggestion).toContainText('series'); // Should show usage count
  });

  test('keyboard navigation works in tag input', async ({ page }) => {
    // Navigate to series detail page
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    await firstSeriesCard.click();
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Type to trigger autocomplete
    const tagInput = page.locator('[data-testid="tag-input"]');
    await tagInput.fill('action');
    
    // Use arrow keys to navigate suggestions
    await tagInput.press('ArrowDown');
    
    // Press Enter to select highlighted suggestion
    await tagInput.press('Enter');
    
    // Verify tag is added
    await expect(page.locator('[data-testid="selected-tag"]:has-text("action")')).toBeVisible();
  });

  test('handles empty states correctly', async ({ page }) => {
    // Navigate to series with no tags
    const seriesWithoutTags = page.locator('[data-testid="series-card"]').last();
    await seriesWithoutTags.click();
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Verify empty state message
    await expect(page.locator('text=No tags assigned')).toBeVisible();
    await expect(page.locator('text=Click "Edit Tags" to add some tags')).toBeVisible();
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Verify placeholder text
    const tagInput = page.locator('[data-testid="tag-input"]');
    await expect(tagInput).toHaveAttribute('placeholder', /Type to search or create tags/);
  });

  test('tag-based organization views work', async ({ page }) => {
    // Navigate to library page
    await page.goto('/library');
    
    // Switch to tag-based view (if implemented)
    const viewToggle = page.locator('[data-testid="view-toggle"]');
    if (await viewToggle.isVisible()) {
      await viewToggle.click();
      const tagView = page.locator('[data-testid="tag-view-option"]');
      await tagView.click();
      
      // Verify series are grouped by tags
      await expect(page.locator('[data-testid="tag-group"]')).toHaveCount(2); // action, fantasy
      
      // Verify series appear under correct tag groups
      const actionGroup = page.locator('[data-testid="tag-group"]:has-text("action")');
      await expect(actionGroup.locator('[data-testid="series-card"]')).toHaveCount(1);
    }
  });

  test('mobile responsive tag interface', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate to series detail page
    const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
    await firstSeriesCard.click();
    await page.waitForSelector('[data-testid="series-tag-editor"]');
    
    // Verify tag editor is responsive
    const tagEditor = page.locator('[data-testid="series-tag-editor"]');
    await expect(tagEditor).toBeVisible();
    
    // Open tag editor
    const editTagsButton = page.locator('button:has-text("Edit Tags")');
    await editTagsButton.click();
    
    // Verify tag input is properly sized for mobile
    const tagInput = page.locator('[data-testid="tag-input"]');
    const inputBox = await tagInput.boundingBox();
    expect(inputBox?.width).toBeLessThan(375);
    
    // Test touch interactions work
    await tagInput.fill('mobile');
    await page.locator('[data-testid="tag-suggestion-create"]').click();
    
    // Verify tag is added and displayed properly on mobile
    await expect(page.locator('[data-testid="selected-tag"]:has-text("mobile")')).toBeVisible();
  });
});

// Utility test for tag management API
test.describe('Tag Management API', () => {
  test('CRUD operations work correctly', async ({ request }) => {
    // Create a new tag
    const createResponse = await request.post('/api/tags/', {
      data: {
        name: 'test-tag',
        description: 'A test tag',
        color: '#FF0000'
      }
    });
    expect(createResponse.ok()).toBeTruthy();
    const createdTag = await createResponse.json();
    expect(createdTag.name).toBe('test-tag');
    
    // Get all tags
    const getResponse = await request.get('/api/tags/');
    expect(getResponse.ok()).toBeTruthy();
    const tagsList = await getResponse.json();
    expect(tagsList.tags).toContainEqual(expect.objectContaining({
      name: 'test-tag'
    }));
    
    // Update the tag
    const updateResponse = await request.put(`/api/tags/${createdTag.id}`, {
      data: {
        name: 'updated-tag',
        color: '#00FF00'
      }
    });
    expect(updateResponse.ok()).toBeTruthy();
    const updatedTag = await updateResponse.json();
    expect(updatedTag.name).toBe('updated-tag');
    expect(updatedTag.color).toBe('#00FF00');
    
    // Delete the tag
    const deleteResponse = await request.delete(`/api/tags/${createdTag.id}`);
    expect(deleteResponse.ok()).toBeTruthy();
    
    // Verify tag is deleted
    const getAfterDelete = await request.get(`/api/tags/${createdTag.id}`);
    expect(getAfterDelete.status()).toBe(404);
  });

  test('series tag assignment works correctly', async ({ request }) => {
    // Assuming we have a test series ID
    const testSeriesId = 'test-series-id';
    
    // Create test tags
    const tag1Response = await request.post('/api/tags/', {
      data: { name: 'series-tag-1' }
    });
    const tag2Response = await request.post('/api/tags/', {
      data: { name: 'series-tag-2' }
    });
    
    const tag1 = await tag1Response.json();
    const tag2 = await tag2Response.json();
    
    // Assign tags to series
    const assignResponse = await request.put(`/api/tags/series/${testSeriesId}`, {
      data: {
        tag_ids: [tag1.id, tag2.id]
      }
    });
    expect(assignResponse.ok()).toBeTruthy();
    
    // Get series tags
    const seriesTagsResponse = await request.get(`/api/tags/series/${testSeriesId}`);
    expect(seriesTagsResponse.ok()).toBeTruthy();
    const seriesTags = await seriesTagsResponse.json();
    expect(seriesTags).toHaveLength(2);
    
    // Remove one tag
    const removeResponse = await request.delete(`/api/tags/series/${testSeriesId}/remove`, {
      data: {
        tag_ids: [tag1.id]
      }
    });
    expect(removeResponse.ok()).toBeTruthy();
    
    // Verify only one tag remains
    const remainingTagsResponse = await request.get(`/api/tags/series/${testSeriesId}`);
    const remainingTags = await remainingTagsResponse.json();
    expect(remainingTags).toHaveLength(1);
    expect(remainingTags[0].id).toBe(tag2.id);
    
    // Cleanup
    await request.delete(`/api/tags/${tag1.id}`);
    await request.delete(`/api/tags/${tag2.id}`);
  });
});