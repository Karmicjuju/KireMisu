/**
 * End-to-End Tests for File Operations
 * 
 * Tests the complete user workflow from UI to backend for safe file operations.
 * Covers the full stack including:
 * - Frontend components
 * - API endpoints
 * - Database operations
 * - File system operations
 * - Error handling and recovery
 */

import { test, expect, Page } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Test data setup
const TEST_DATA_DIR = path.join(__dirname, '../fixtures/file-operations-test-data');

test.describe('File Operations End-to-End', () => {
  let testDataCreated = false;

  test.beforeAll(async () => {
    // Create test data directory and files
    try {
      await fs.mkdir(TEST_DATA_DIR, { recursive: true });
      
      // Create test manga files
      await fs.writeFile(path.join(TEST_DATA_DIR, 'test-manga.cbz'), 'fake cbz content');
      await fs.writeFile(path.join(TEST_DATA_DIR, 'another-manga.cbz'), 'another fake cbz content');
      
      // Create test directory structure
      const seriesDir = path.join(TEST_DATA_DIR, 'Test Series');
      await fs.mkdir(seriesDir, { recursive: true });
      
      const chapterDir = path.join(seriesDir, 'Chapter 001');
      await fs.mkdir(chapterDir, { recursive: true });
      
      // Create test pages
      for (let i = 1; i <= 5; i++) {
        await fs.writeFile(
          path.join(chapterDir, `page_${i.toString().padStart(3, '0')}.jpg`),
          `fake page ${i} content`
        );
      }
      
      testDataCreated = true;
    } catch (error) {
      console.error('Failed to create test data:', error);
    }
  });

  test.afterAll(async () => {
    // Clean up test data
    if (testDataCreated) {
      try {
        await fs.rmdir(TEST_DATA_DIR, { recursive: true });
      } catch (error) {
        console.error('Failed to clean up test data:', error);
      }
    }
  });

  test('complete rename operation workflow', async ({ page }) => {
    // Navigate to library page (assuming it has file operations)
    await page.goto('/library');
    await expect(page).toHaveTitle(/KireMisu/);

    // Test assumes there's a way to trigger file operations from the library
    // This would depend on the actual UI implementation
    
    // Look for a series or file to rename
    const testFile = path.join(TEST_DATA_DIR, 'test-manga.cbz');
    
    // Simulate opening rename dialog
    // Note: This would need to be adapted based on actual UI implementation
    await page.evaluate((filePath) => {
      // This would trigger the FileOperationDialog component
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: {
          operation: 'rename',
          sourcePath: filePath,
          targetPath: filePath.replace('test-manga.cbz', 'renamed-manga.cbz')
        }
      }));
    }, testFile);

    // Wait for the dialog to appear
    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Verify dialog title
    await expect(page.locator('h2')).toContainText('Rename File/Directory');

    // Check that source path is populated
    await expect(page.locator('input[name="source_path"]')).toHaveValue(testFile);

    // Enter target path
    const targetPath = testFile.replace('test-manga.cbz', 'renamed-manga.cbz');
    await page.locator('input[name="target_path"]').fill(targetPath);

    // Ensure safety options are enabled
    await expect(page.locator('input[name="create_backup"]')).toBeChecked();
    await expect(page.locator('input[name="validate_consistency"]')).toBeChecked();

    // Start the operation
    await page.locator('button:has-text("Continue")').click();

    // Wait for validation to complete
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible();

    // Check validation results
    await expect(page.locator('[data-testid="risk-level"]')).toBeVisible();
    
    // If validation passed, proceed with execution
    const executeButton = page.locator('button:has-text("Execute")');
    if (await executeButton.isVisible()) {
      await executeButton.click();

      // Wait for operation to complete
      await expect(page.locator('[data-testid="operation-complete"]')).toBeVisible({ timeout: 30000 });

      // Verify success message
      await expect(page.locator('text=Operation Completed')).toBeVisible();

      // Verify backup was created
      await expect(page.locator('text=Backup created')).toBeVisible();
    }

    // Close dialog
    await page.locator('button:has-text("Close")').click();
    await expect(page.locator('[data-testid="file-operation-dialog"]')).not.toBeVisible();
  });

  test('complete delete operation with confirmation workflow', async ({ page }) => {
    await page.goto('/library');

    const testFile = path.join(TEST_DATA_DIR, 'another-manga.cbz');

    // Trigger delete operation
    await page.evaluate((filePath) => {
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: {
          operation: 'delete',
          sourcePath: filePath
        }
      }));
    }, testFile);

    // Wait for dialog
    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Verify delete dialog
    await expect(page.locator('h2')).toContainText('Delete File/Directory');

    // Start operation
    await page.locator('button:has-text("Continue")').click();

    // Wait for validation
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible();

    // Should show high risk for delete operations
    const riskLevel = page.locator('[data-testid="risk-level"]');
    await expect(riskLevel).toContainText(/high|medium/i);

    // Should require confirmation for delete
    await expect(page.locator('text=requires confirmation')).toBeVisible();

    // Proceed with high-risk operation
    const executeButton = page.locator('button:has-text("Execute")');
    await executeButton.click();

    // Wait for completion
    await expect(page.locator('[data-testid="operation-complete"]')).toBeVisible({ timeout: 30000 });

    // Should show rollback option
    await expect(page.locator('button:has-text("Rollback")')).toBeVisible();
  });

  test('operation validation with warnings and errors', async ({ page }) => {
    await page.goto('/library');

    // Test with non-existent source path
    const nonExistentPath = '/non/existent/path/fake.cbz';

    await page.evaluate((filePath) => {
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: {
          operation: 'rename',
          sourcePath: filePath,
          targetPath: filePath.replace('fake.cbz', 'renamed.cbz')
        }
      }));
    }, nonExistentPath);

    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Try to continue with invalid path
    await page.locator('button:has-text("Continue")').click();

    // Should show error
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('text=does not exist')).toBeVisible();
  });

  test('operations dashboard functionality', async ({ page }) => {
    await page.goto('/operations'); // Assuming there's an operations dashboard page

    // Wait for dashboard to load
    await expect(page.locator('[data-testid="operations-dashboard"]')).toBeVisible();

    // Should show operations list
    await expect(page.locator('[data-testid="operations-list"]')).toBeVisible();

    // Test filtering
    await page.locator('[data-testid="filter-button"]').click();
    await page.locator('select[name="status_filter"]').selectOption('completed');
    
    // Should filter operations
    await expect(page.locator('[data-testid="operations-list"] [data-status="completed"]')).toBeVisible();

    // Test refresh
    await page.locator('[data-testid="refresh-button"]').click();
    
    // Should reload operations
    await expect(page.locator('[data-testid="operations-list"]')).toBeVisible();

    // Test operation details expansion
    const firstOperation = page.locator('[data-testid="operation-item"]').first();
    if (await firstOperation.isVisible()) {
      await firstOperation.locator('[data-testid="expand-button"]').click();
      
      // Should show expanded details
      await expect(firstOperation.locator('[data-testid="operation-details"]')).toBeVisible();
    }
  });

  test('rollback operation functionality', async ({ page }) => {
    await page.goto('/operations');

    // Find a completed operation with backup
    const completedOp = page.locator('[data-testid="operation-item"][data-status="completed"]').first();
    
    if (await completedOp.isVisible()) {
      // Click rollback button
      await completedOp.locator('[data-testid="rollback-button"]').click();

      // Should show confirmation dialog
      page.on('dialog', async dialog => {
        expect(dialog.message()).toContain('rollback');
        await dialog.accept();
      });

      // Wait for rollback to complete
      await expect(completedOp).toHaveAttribute('data-status', 'rolled_back', { timeout: 30000 });
    }
  });

  test('error handling and recovery', async ({ page }) => {
    await page.goto('/library');

    // Test with invalid target path (e.g., path that would cause permission error)
    const testFile = path.join(TEST_DATA_DIR, 'test-manga.cbz');
    const invalidTarget = '/root/restricted/fake.cbz'; // Should cause permission error

    await page.evaluate(([source, target]) => {
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: {
          operation: 'move',
          sourcePath: source,
          targetPath: target
        }
      }));
    }, [testFile, invalidTarget]);

    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Fill in the invalid target path
    await page.locator('input[name="target_path"]').fill(invalidTarget);
    await page.locator('button:has-text("Continue")').click();

    // Should show validation error
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('text=not writable')).toBeVisible();

    // Error should be clearable
    await page.locator('[data-testid="clear-error-button"]').click();
    await expect(page.locator('[data-testid="error-message"]')).not.toBeVisible();
  });

  test('concurrent operations handling', async ({ page, context }) => {
    // Open multiple pages to simulate concurrent operations
    const page2 = await context.newPage();
    
    await page.goto('/library');
    await page2.goto('/library');

    // Create test files for concurrent operations
    const testFile1 = path.join(TEST_DATA_DIR, 'concurrent1.cbz');
    const testFile2 = path.join(TEST_DATA_DIR, 'concurrent2.cbz');

    // Trigger operations on both pages simultaneously
    await Promise.all([
      page.evaluate((filePath) => {
        window.dispatchEvent(new CustomEvent('openFileOperation', {
          detail: {
            operation: 'delete',
            sourcePath: filePath
          }
        }));
      }, testFile1),
      
      page2.evaluate((filePath) => {
        window.dispatchEvent(new CustomEvent('openFileOperation', {
          detail: {
            operation: 'delete',
            sourcePath: filePath
          }
        }));
      }, testFile2)
    ]);

    // Both dialogs should open
    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();
    await expect(page2.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Execute both operations
    await Promise.all([
      page.locator('button:has-text("Continue")').click(),
      page2.locator('button:has-text("Continue")').click()
    ]);

    // Both should complete without conflicts
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible();
    await expect(page2.locator('[data-testid="validation-results"]')).toBeVisible();

    await page2.close();
  });

  test('accessibility compliance', async ({ page }) => {
    await page.goto('/library');

    // Trigger operation dialog
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: {
          operation: 'rename',
          sourcePath: '/test/path.cbz',
          targetPath: '/test/renamed.cbz'
        }
      }));
    });

    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Test keyboard navigation
    await page.keyboard.press('Tab'); // Should focus first interactive element
    await page.keyboard.press('Tab'); // Should move to next element
    await page.keyboard.press('Escape'); // Should close dialog

    await expect(page.locator('[data-testid="file-operation-dialog"]')).not.toBeVisible();

    // Test ARIA labels and roles
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: { operation: 'delete', sourcePath: '/test/path.cbz' }
      }));
    });

    const dialog = page.locator('[data-testid="file-operation-dialog"]');
    await expect(dialog).toHaveAttribute('role', 'dialog');
    await expect(dialog).toHaveAttribute('aria-labelledby');
    await expect(dialog).toHaveAttribute('aria-describedby');

    // Test screen reader announcements
    const announcements = page.locator('[aria-live]');
    await expect(announcements).toBeVisible();
  });

  test('performance with large operations', async ({ page }) => {
    await page.goto('/library');

    // Test with large directory structure
    const largeDir = path.join(TEST_DATA_DIR, 'Large Series');

    await page.evaluate((dirPath) => {
      window.dispatchEvent(new CustomEvent('openFileOperation', {
        detail: {
          operation: 'delete',
          sourcePath: dirPath
        }
      }));
    }, largeDir);

    await expect(page.locator('[data-testid="file-operation-dialog"]')).toBeVisible();

    // Measure validation time
    const startTime = Date.now();
    await page.locator('button:has-text("Continue")').click();
    
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible();
    const validationTime = Date.now() - startTime;

    // Validation should complete in reasonable time
    expect(validationTime).toBeLessThan(10000); // Less than 10 seconds

    // Should show estimated size and duration
    await expect(page.locator('[data-testid="estimated-size"]')).toBeVisible();
    await expect(page.locator('[data-testid="estimated-duration"]')).toBeVisible();
  });
});

// Helper function to create mock file operations events
declare global {
  interface Window {
    dispatchEvent(event: CustomEvent): boolean;
  }
}