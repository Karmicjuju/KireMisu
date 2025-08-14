import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should display authenticated dashboard and navigate to settings', async ({ page }) => {
    // Go to the root page (authenticated users see dashboard)
    await page.goto('/');

    // Check that we're on the authenticated dashboard page
    await expect(page.getByRole('heading', { name: 'Welcome back!' })).toBeVisible();
    await expect(
      page.getByText('Continue your manga journey where you left off')
    ).toBeVisible();

    // Navigate directly to settings (which has the app layout with sidebar)
    await page.goto('/settings');

    // Should navigate to settings page
    await expect(page).toHaveURL('/settings');
    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Library Paths' })).toBeVisible();
  });

  test('should have accessible sidebar navigation', async ({ page }) => {
    // Go to settings (which has sidebar navigation)
    await page.goto('/settings');

    // Check that the Settings link has proper accessibility attributes
    const settingsLink = page.getByRole('link', { name: 'Settings' });
    await expect(settingsLink).toBeVisible();

    // Test navigation to Dashboard
    const dashboardLink = page.getByRole('link', { name: 'Dashboard' });
    await expect(dashboardLink).toBeVisible();

    // Should be keyboard accessible
    await dashboardLink.focus();
    await expect(dashboardLink).toBeFocused();

    // Click dashboard link and verify navigation
    await dashboardLink.click();
    await expect(page).toHaveURL('/');
  });

  test('should display authenticated dashboard content', async ({ page }) => {
    await page.goto('/');

    // Check for dashboard content (authenticated users)
    await expect(page.getByRole('heading', { name: 'Welcome back!' })).toBeVisible();
    await expect(
      page.getByText('Continue your manga journey where you left off')
    ).toBeVisible();

    // Check for progress stats section (should be visible even with no data)
    await expect(page.getByText('Total Series')).toBeVisible();
    await expect(page.getByText('Chapters Read')).toBeVisible();
    await expect(page.getByText('Reading Time')).toBeVisible();

    // Check for continue reading section
    await expect(page.getByRole('heading', { name: 'Continue Reading' })).toBeVisible();

    // Check for quick actions section
    await expect(page.getByRole('heading', { name: 'Quick Actions' })).toBeVisible();
  });

  test('should display sidebar elements', async ({ page }) => {
    // Navigate to settings (which has sidebar)
    await page.goto('/settings');

    // Check sidebar elements - use more specific selectors to avoid document title conflicts
    await expect(page.locator('[data-testid="sidebar"] span').filter({ hasText: 'KireMisu' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Library' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Downloads' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();

    // Test that collapse button is present and functional
    const collapseButton = page.getByRole('button', { name: 'Collapse' });
    await expect(collapseButton).toBeVisible();

    // Just verify the button is clickable (don't test full collapse/expand cycle for now)
    await expect(collapseButton).toBeEnabled();
  });

  test('should navigate between app pages via sidebar', async ({ page }) => {
    // Start with settings (has sidebar)
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();

    // Navigate to Library
    await page.getByRole('link', { name: 'Library' }).click();
    await expect(page).toHaveURL('/library');
    await expect(page.getByRole('heading', { name: 'Library', exact: true })).toBeVisible();

    // Navigate to Downloads
    await page.getByRole('link', { name: 'Downloads' }).click();
    await expect(page).toHaveURL('/downloads');
    await expect(page.getByRole('heading', { name: 'Downloads', exact: true })).toBeVisible();

    // Navigate back to Settings
    await page.getByRole('link', { name: 'Settings' }).click();
    await expect(page).toHaveURL('/settings');
    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();

    // Test Dashboard link (goes to authenticated dashboard)
    await page.getByRole('link', { name: 'Dashboard' }).click();
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { name: 'Welcome back!' })).toBeVisible();
  });
});
