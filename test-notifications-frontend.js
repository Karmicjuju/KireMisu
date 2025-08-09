const { chromium } = require('playwright');

async function testNotificationsFrontend() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to the application
    console.log('Navigating to http://localhost:3000...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // Take a screenshot of the initial page
    await page.screenshot({ path: 'screenshots/initial-page.png', fullPage: true });
    console.log('Screenshot saved: screenshots/initial-page.png');

    // Check if notification bell is present
    const notificationBell = await page.locator('[aria-label*="Notifications"]').first();
    const bellExists = await notificationBell.count() > 0;
    console.log('Notification bell present:', bellExists);

    if (bellExists) {
      // Check if there's an unread count badge
      const badge = await page.locator('[aria-label*="Notifications"] .absolute').first();
      const badgeExists = await badge.count() > 0;
      console.log('Badge present:', badgeExists);

      // Click the notification bell
      console.log('Clicking notification bell...');
      await notificationBell.click();
      await page.waitForTimeout(1000);

      // Take screenshot of dropdown
      await page.screenshot({ path: 'screenshots/notification-dropdown.png', fullPage: true });
      console.log('Screenshot saved: screenshots/notification-dropdown.png');

      // Check if dropdown appeared
      const dropdown = await page.locator('[role="dialog"], [data-testid="notification-dropdown"]').first();
      const dropdownExists = await dropdown.count() > 0;
      console.log('Notification dropdown appeared:', dropdownExists);
    }

    // Look for series cards with watch toggles
    const seriesCards = await page.locator('[data-testid*="series"], .series-card, [role="article"]');
    const cardsCount = await seriesCards.count();
    console.log('Series cards found:', cardsCount);

    if (cardsCount > 0) {
      // Look for watch toggle buttons
      const watchButtons = await page.locator('[aria-label*="watching"], button:has-text("Watch"), button:has-text("Watching")');
      const watchButtonCount = await watchButtons.count();
      console.log('Watch toggle buttons found:', watchButtonCount);

      if (watchButtonCount > 0) {
        // Take screenshot of series with watch toggles
        await page.screenshot({ path: 'screenshots/series-with-watch-toggles.png', fullPage: true });
        console.log('Screenshot saved: screenshots/series-with-watch-toggles.png');

        // Try to click a watch toggle
        console.log('Clicking first watch toggle...');
        const firstWatchButton = watchButtons.first();
        await firstWatchButton.click();
        await page.waitForTimeout(2000);

        // Check for toast notification
        const toast = await page.locator('[role="alert"], .toast, [data-testid="toast"]').first();
        const toastExists = await toast.count() > 0;
        console.log('Toast notification appeared:', toastExists);

        if (toastExists) {
          const toastText = await toast.textContent();
          console.log('Toast message:', toastText);
        }

        // Take screenshot after toggle
        await page.screenshot({ path: 'screenshots/after-watch-toggle.png', fullPage: true });
        console.log('Screenshot saved: screenshots/after-watch-toggle.png');
      }
    }

    // Check network requests for API calls
    console.log('Checking network requests...');
    const responses = [];
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        responses.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText()
        });
      }
    });

    // Refresh to catch API calls
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('API Responses captured:');
    responses.forEach(response => {
      console.log(`- ${response.status} ${response.statusText}: ${response.url}`);
    });

  } catch (error) {
    console.error('Error during testing:', error);
    await page.screenshot({ path: 'screenshots/error-page.png', fullPage: true });
  } finally {
    await browser.close();
  }
}

// Create screenshots directory
require('fs').mkdirSync('screenshots', { recursive: true });

testNotificationsFrontend().catch(console.error);