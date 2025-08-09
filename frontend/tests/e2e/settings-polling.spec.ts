import { test, expect, Page } from '@playwright/test';

/**
 * E2E Tests for Settings Page - Polling Configuration
 * Tests the collapsible polling settings component and its functionality
 */

test.describe('Settings Page - Polling Configuration', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Clear localStorage to start with defaults
    await page.addInitScript(() => {
      window.localStorage.clear();
    });

    // Navigate to settings page
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
  });

  test('should display collapsible polling settings component', async () => {
    // Test page title and structure
    await expect(page).toHaveTitle(/Settings/);
    
    // Find the polling settings section
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await expect(pollingSection).toBeVisible();

    // Should initially be collapsed (chevron right)
    const chevronRight = pollingSection.locator('svg').first();
    await expect(chevronRight).toBeVisible();

    // Should show summary when collapsed
    const summaryText = pollingSection.locator('text=Initial:');
    await expect(summaryText).toBeVisible();
    await expect(pollingSection).toContainText('Active:');
  });

  test('should expand and collapse polling settings', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    
    // Click to expand
    await pollingSection.click();
    
    // Should show expanded content
    const expandedContent = page.locator('label:has-text("Initial Polling Interval")');
    await expect(expandedContent).toBeVisible();
    
    // Should show chevron down when expanded
    const chevronDown = pollingSection.locator('svg').first();
    await expect(chevronDown).toBeVisible();

    // Click to collapse
    await pollingSection.click();
    
    // Expanded content should be hidden
    await expect(expandedContent).not.toBeVisible();
  });

  test('should display default polling settings correctly', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Check default values (1-minute intervals)
    const initialIntervalInput = page.locator('#initialInterval');
    await expect(initialIntervalInput).toHaveValue('60');
    
    const activeIntervalInput = page.locator('#activeInterval');
    await expect(activeIntervalInput).toHaveValue('30');
    
    const maxIntervalInput = page.locator('#maxInterval');
    await expect(maxIntervalInput).toHaveValue('300');
    
    const maxErrorsInput = page.locator('#maxConsecutiveErrors');
    await expect(maxErrorsInput).toHaveValue('3');
  });

  test('should validate polling settings input', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Test validation - set invalid value (below minimum)
    const initialIntervalInput = page.locator('#initialInterval');
    await initialIntervalInput.fill('5'); // Below minimum of 10
    
    // Should show validation error
    const validationError = page.locator('text=Initial Interval must be between 10 and 600');
    await expect(validationError).toBeVisible();
    
    // Save button should be disabled
    const saveButton = page.locator('button:has-text("Save Changes")');
    await expect(saveButton).toBeDisabled();
  });

  test('should validate cross-field relationships', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Set active interval greater than initial interval
    const activeIntervalInput = page.locator('#activeInterval');
    const initialIntervalInput = page.locator('#initialInterval');
    
    await initialIntervalInput.fill('30');
    await activeIntervalInput.fill('60'); // Greater than initial
    
    // Should show cross-field validation error
    const crossFieldError = page.locator('text=Active interval should not be greater than initial interval');
    await expect(crossFieldError).toBeVisible();
    
    const saveButton = page.locator('button:has-text("Save Changes")');
    await expect(saveButton).toBeDisabled();
  });

  test('should save and restore polling settings', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Change settings
    const initialIntervalInput = page.locator('#initialInterval');
    await initialIntervalInput.fill('120'); // 2 minutes
    
    const activeIntervalInput = page.locator('#activeInterval');
    await activeIntervalInput.fill('45'); // 45 seconds
    
    // Save button should be enabled
    const saveButton = page.locator('button:has-text("Save Changes")');
    await expect(saveButton).toBeEnabled();
    
    // Click save
    await saveButton.click();
    
    // Should show success toast
    const successToast = page.locator('text=Settings Saved');
    await expect(successToast).toBeVisible();
    
    // Refresh page and verify settings are restored
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    await pollingSection.click(); // Expand again
    
    await expect(page.locator('#initialInterval')).toHaveValue('120');
    await expect(page.locator('#activeInterval')).toHaveValue('45');
  });

  test('should reset settings to defaults', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Change a setting
    const initialIntervalInput = page.locator('#initialInterval');
    await initialIntervalInput.fill('120');
    
    // Click reset
    const resetButton = page.locator('button:has-text("Reset")');
    await resetButton.click();
    
    // Should show reset toast
    const resetToast = page.locator('text=Settings Reset');
    await expect(resetToast).toBeVisible();
    
    // Should restore default value
    await expect(initialIntervalInput).toHaveValue('60');
  });

  test('should display time formatting correctly', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    
    // Check collapsed view shows formatted time
    await expect(pollingSection).toContainText('Initial: 1m');
    await expect(pollingSection).toContainText('Active: 30s');
    
    await pollingSection.click(); // Expand
    
    // Check expanded view shows formatted time in descriptions
    const initialDescription = page.locator('text=(1m)').first();
    await expect(initialDescription).toBeVisible();
    
    const activeDescription = page.locator('text=(30s)').first();
    await expect(activeDescription).toBeVisible();
    
    const maxDescription = page.locator('text=(5m)').first();
    await expect(maxDescription).toBeVisible();
  });

  test('should show unsaved changes indicator', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    
    // Initially no unsaved changes indicator
    const unsavedDot = pollingSection.locator('div.bg-orange-500');
    await expect(unsavedDot).not.toBeVisible();
    
    await pollingSection.click(); // Expand
    
    // Change a setting
    const initialIntervalInput = page.locator('#initialInterval');
    await initialIntervalInput.fill('90');
    
    // Collapse to see indicator
    await pollingSection.click();
    
    // Should show unsaved changes dot
    await expect(unsavedDot).toBeVisible();
  });

  test('should handle localStorage errors gracefully', async () => {
    // Simulate localStorage error by making it read-only
    await page.addInitScript(() => {
      // Override localStorage to throw error
      const originalGetItem = window.localStorage.getItem;
      window.localStorage.getItem = () => {
        throw new Error('localStorage not available');
      };
    });
    
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Should still work with defaults
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click();
    
    const initialIntervalInput = page.locator('#initialInterval');
    await expect(initialIntervalInput).toHaveValue('60'); // Default value
    
    // Should show warning toast
    const warningToast = page.locator('text=Could not load saved settings');
    await expect(warningToast).toBeVisible();
  });

  test('should be accessible with keyboard navigation', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    
    // Tab to the polling section
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab'); // May need multiple tabs to reach
    await page.keyboard.press('Tab');
    
    // Enter should expand/collapse
    await page.keyboard.press('Enter');
    
    const expandedContent = page.locator('label:has-text("Initial Polling Interval")');
    const isVisible = await expandedContent.isVisible();
    
    // Should toggle expansion state
    expect(isVisible).toBeTruthy();
    
    // Tab through form fields
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('should show help text and recommendations', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Should show "How Polling Works" section
    const helpSection = page.locator('text=How Polling Works');
    await expect(helpSection).toBeVisible();
    
    // Should show adaptive polling explanation
    const adaptiveText = page.locator('text=Adaptive Polling Strategy');
    await expect(adaptiveText).toBeVisible();
    
    // Should show recommended settings
    const recommendedSection = page.locator('text=Recommended Settings');
    await expect(recommendedSection).toBeVisible();
    
    const lightUsage = page.locator('text=Light Usage');
    await expect(lightUsage).toBeVisible();
    
    const heavyUsage = page.locator('text=Heavy Usage');
    await expect(heavyUsage).toBeVisible();
  });

  test('should handle edge cases in validation', async () => {
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Test maximum values
    const initialIntervalInput = page.locator('#initialInterval');
    await initialIntervalInput.fill('600'); // Maximum allowed
    
    // Should not show validation error
    const validationError = page.locator('text=Initial Interval must be between');
    await expect(validationError).not.toBeVisible();
    
    // Test beyond maximum
    await initialIntervalInput.fill('700'); // Beyond maximum
    await expect(validationError).toBeVisible();
    
    // Test non-numeric input
    await initialIntervalInput.fill('abc');
    await expect(initialIntervalInput).toHaveValue('0'); // Should default to 0
    await expect(validationError).toBeVisible(); // 0 is below minimum
  });
});

/**
 * Integration tests for polling settings with other components
 */
test.describe('Settings Page - Polling Integration', () => {
  test('should dispatch custom event when settings are saved', async ({ page }) => {
    let eventFired = false;
    
    // Listen for custom event
    await page.addInitScript(() => {
      window.addEventListener('polling-settings-updated', (event) => {
        window.testEventData = event.detail;
      });
    });
    
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    
    const pollingSection = page.locator('text=Download Polling Settings').locator('..');
    await pollingSection.click(); // Expand
    
    // Change and save settings
    const initialIntervalInput = page.locator('#initialInterval');
    await initialIntervalInput.fill('180');
    
    const saveButton = page.locator('button:has-text("Save Changes")');
    await saveButton.click();
    
    // Wait for save to complete
    await page.waitForSelector('text=Settings Saved');
    
    // Check if event was fired with correct data
    const eventData = await page.evaluate(() => window.testEventData);
    expect(eventData).toBeTruthy();
    expect(eventData.initialInterval).toBe(180);
  });
});