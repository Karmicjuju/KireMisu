/**
 * E2E tests for annotation functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Annotation System', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a reader page (assuming we have test data)
    await page.goto('/reader/test-chapter-id');
    
    // Wait for the reader to load
    await expect(page.locator('img[alt*="Page"]')).toBeVisible();
  });

  test('should display annotation controls in reader header', async ({ page }) => {
    // Check for annotation toggle button
    const annotationToggle = page.locator('[aria-label="Toggle annotation mode"]');
    await expect(annotationToggle).toBeVisible();

    // Check for annotation drawer button
    const annotationDrawer = page.locator('[aria-label="Show annotations"]');
    await expect(annotationDrawer).toBeVisible();
  });

  test('should toggle annotation mode', async ({ page }) => {
    const annotationToggle = page.locator('[aria-label="Toggle annotation mode"]');
    
    // Click to enable annotation mode
    await annotationToggle.click();
    
    // Should show toast message
    await expect(page.locator('[role="alert"]')).toContainText('Annotation Mode');
    
    // Should show annotation overlay
    await expect(page.locator('text=Click anywhere to add an annotation')).toBeVisible();
  });

  test('should open annotation drawer', async ({ page }) => {
    const annotationDrawer = page.locator('[aria-label="Show annotations"]');
    
    // Click to open drawer
    await annotationDrawer.click();
    
    // Should show annotation drawer
    await expect(page.locator('h2:has-text("Annotations")')).toBeVisible();
    
    // Should show add note button
    await expect(page.locator('button:has-text("Add Note")')).toBeVisible();
  });

  test('should create annotation through form', async ({ page }) => {
    // Open annotation drawer
    await page.locator('[aria-label="Show annotations"]').click();
    
    // Click add note button
    await page.locator('button:has-text("Add Note")').click();
    
    // Should show annotation form
    await expect(page.locator('h3:has-text("Add Annotation")')).toBeVisible();
    
    // Fill out form
    await page.locator('textarea[placeholder*="Enter your"]').fill('Test annotation content');
    
    // Select annotation type (note is default)
    await expect(page.locator('button:has-text("Note")').first()).toHaveClass(/border-blue-500/);
    
    // Submit form
    await page.locator('button:has-text("Create")').click();
    
    // Should show success message
    await expect(page.locator('[role="alert"]')).toContainText('Success');
  });

  test('should create annotation by clicking on page', async ({ page }) => {
    // Enable annotation mode
    await page.locator('[aria-label="Toggle annotation mode"]').click();
    
    // Wait for annotation mode to be active
    await expect(page.locator('text=Click anywhere to add an annotation')).toBeVisible();
    
    // Click on the manga page to create annotation
    const mangaPage = page.locator('img[alt*="Page"]');
    await mangaPage.click({ position: { x: 100, y: 150 } });
    
    // Should show annotation form
    await expect(page.locator('h3:has-text("Add Annotation")')).toBeVisible();
    
    // Should show position information
    await expect(page.locator('text=Position:')).toBeVisible();
    
    // Fill out form
    await page.locator('textarea[placeholder*="Enter your"]').fill('Clicked annotation');
    
    // Submit
    await page.locator('button:has-text("Create")').click();
    
    // Should create annotation marker on page
    await expect(page.locator('[title="Clicked annotation"]')).toBeVisible();
  });

  test('should display annotation markers on pages', async ({ page }) => {
    // Assuming we have some test annotations in the database
    // The markers should be visible as overlays on the manga page
    
    // Look for annotation markers (they have specific styling and icons)
    const markers = page.locator('.group.cursor-pointer'); // Based on AnnotationMarker component
    
    // If there are annotations, markers should be visible
    const markerCount = await markers.count();
    if (markerCount > 0) {
      // Check first marker
      await expect(markers.first()).toBeVisible();
      
      // Hover to see tooltip
      await markers.first().hover();
      await expect(page.locator('.opacity-0.group-hover\\:opacity-100')).toBeVisible();
    }
  });

  test('should filter annotations by type', async ({ page }) => {
    // Open annotation drawer
    await page.locator('[aria-label="Show annotations"]').click();
    
    // Find filter dropdown
    const filterSelect = page.locator('select');
    await expect(filterSelect).toBeVisible();
    
    // Test filtering by notes
    await filterSelect.selectOption('note');
    
    // Test filtering by bookmarks
    await filterSelect.selectOption('bookmark');
    
    // Test filtering by highlights
    await filterSelect.selectOption('highlight');
    
    // Reset to all
    await filterSelect.selectOption('all');
  });

  test('should close annotation drawer', async ({ page }) => {
    // Open drawer
    await page.locator('[aria-label="Show annotations"]').click();
    await expect(page.locator('h2:has-text("Annotations")')).toBeVisible();
    
    // Close using X button
    await page.locator('button[aria-label="Close"]').click();
    
    // Drawer should be hidden
    await expect(page.locator('h2:has-text("Annotations")')).not.toBeVisible();
  });

  test('should close annotation drawer by clicking overlay', async ({ page }) => {
    // Open drawer
    await page.locator('[aria-label="Show annotations"]').click();
    await expect(page.locator('h2:has-text("Annotations")')).toBeVisible();
    
    // Click overlay to close
    await page.locator('.fixed.inset-0.bg-black.bg-opacity-50').click();
    
    // Drawer should be hidden
    await expect(page.locator('h2:has-text("Annotations")')).not.toBeVisible();
  });
});