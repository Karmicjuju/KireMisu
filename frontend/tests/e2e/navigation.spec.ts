import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should display standalone welcome page and navigate to settings', async ({ page }) => {
    // Go to the root page (standalone welcome page)
    await page.goto('/');

    // Check that we're on the standalone welcome page
    await expect(page.getByRole('heading', { name: 'Welcome to KireMisu!' })).toBeVisible();
    await expect(
      page.getByText('Your self-hosted manga reader and library management system')
    ).toBeVisible();

    // Navigate directly to settings (which has the app layout with sidebar)
    await page.goto('/settings');

    // Should navigate to settings page
    await expect(page).toHaveURL('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
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

  test('should display welcome page content', async ({ page }) => {
    await page.goto('/');

    // Check for welcome page content (standalone page)
    await expect(page.getByRole('heading', { name: 'Welcome to KireMisu!' })).toBeVisible();
    await expect(page.getByText('Your self-hosted manga reader and library management system')).toBeVisible();

    // Check for stats cards on welcome page
    await expect(page.getByText('Total Series')).toBeVisible();
    await expect(page.getByText('Chapters Read')).toBeVisible();
    await expect(page.getByText('Reading Time')).toBeVisible();
    await expect(page.getByText('Favorites')).toBeVisible();

    // Check for getting started section
    await expect(page.getByRole('heading', { name: 'Getting Started' })).toBeVisible();
    await expect(page.getByText('Navigate to Settings to configure your library paths')).toBeVisible();
  });

  test('should display sidebar elements', async ({ page }) => {
    // Navigate to settings (which has sidebar)
    await page.goto('/settings');

    // Check sidebar elements - KireMisu is in sidebar header, links are in nav
    await expect(page.getByText('KireMisu')).toBeVisible();
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
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

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
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

    // Test Dashboard link (goes to standalone welcome page)
    await page.getByRole('link', { name: 'Dashboard' }).click();
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { name: 'Welcome to KireMisu!' })).toBeVisible();
  });
});
