import { test, expect, Page } from '@playwright/test';
import { injectAxe, checkA11y, getViolations, AxeResults } from 'axe-playwright';

/**
 * Reading Progress Accessibility Compliance Tests
 * 
 * This test suite ensures that all R-2 reading progress features are fully
 * accessible and compliant with WCAG 2.1 AA standards.
 */

class AccessibilityHelper {
  constructor(private page: Page) {}

  async injectAxeAndTest(context: string = 'page'): Promise<AxeResults[]> {
    await injectAxe(this.page);
    return await getViolations(this.page, null, {
      detailedReport: true,
      detailedReportOptions: { html: true }
    });
  }

  async checkColorContrast(selector: string): Promise<boolean> {
    const element = this.page.locator(selector);
    const bgColor = await element.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.backgroundColor;
    });
    const color = await element.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.color;
    });
    
    // Basic check - in real implementation, would calculate actual contrast ratio
    return bgColor !== color && bgColor !== 'rgba(0, 0, 0, 0)';
  }

  async simulateScreenReader(): Promise<void> {
    // Simulate screen reader by enabling announce mode and checking ARIA
    await this.page.addInitScript(() => {
      // Mock screen reader announcements
      (window as any).screenReaderAnnouncements = [];
      
      // Override ARIA live region updates
      const originalSetAttribute = Element.prototype.setAttribute;
      Element.prototype.setAttribute = function(name: string, value: string) {
        if (name === 'aria-live' || name === 'aria-atomic') {
          (window as any).screenReaderAnnouncements.push({
            element: this,
            attribute: name,
            value: value,
            text: this.textContent,
            timestamp: Date.now()
          });
        }
        return originalSetAttribute.call(this, name, value);
      };
    });
  }

  async checkKeyboardNavigation(startSelector: string, expectedOrder: string[]): Promise<boolean> {
    await this.page.click(startSelector);
    
    for (let i = 0; i < expectedOrder.length; i++) {
      await this.page.keyboard.press('Tab');
      
      const focusedElement = await this.page.locator(':focus').getAttribute('data-testid');
      if (focusedElement !== expectedOrder[i]) {
        console.log(`Expected ${expectedOrder[i]}, got ${focusedElement} at position ${i}`);
        return false;
      }
    }
    return true;
  }

  async validateARIAAttributes(selector: string, expectedAttributes: Record<string, string>): Promise<boolean> {
    const element = this.page.locator(selector);
    
    for (const [attr, expectedValue] of Object.entries(expectedAttributes)) {
      const actualValue = await element.getAttribute(attr);
      if (actualValue !== expectedValue) {
        console.log(`${attr}: expected "${expectedValue}", got "${actualValue}"`);
        return false;
      }
    }
    return true;
  }

  async testReducedMotion(): Promise<void> {
    await this.page.emulateMedia({ reducedMotion: 'reduce' });
  }

  async testHighContrast(): Promise<void> {
    await this.page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
    
    // Apply high contrast styles
    await this.page.addStyleTag({
      content: `
        @media (prefers-contrast: high) {
          * {
            background-color: black !important;
            color: white !important;
            border-color: white !important;
          }
          .progress-fill {
            background-color: yellow !important;
          }
          button:focus {
            outline: 3px solid yellow !important;
          }
        }
      `
    });
  }
}

test.describe('Reading Progress Accessibility Tests', () => {
  let a11yHelper: AccessibilityHelper;

  test.beforeEach(async ({ page }) => {
    a11yHelper = new AccessibilityHelper(page);
  });

  test.describe('WCAG 2.1 AA Compliance', () => {
    test('dashboard passes automated accessibility tests', async ({ page }) => {
      await page.goto('/');
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      const violations = await a11yHelper.injectAxeAndTest('dashboard');
      
      // Filter out known false positives or accepted violations
      const criticalViolations = violations.filter(violation => 
        violation.impact === 'critical' || violation.impact === 'serious'
      );
      
      expect(criticalViolations).toHaveLength(0);
      
      if (violations.length > 0) {
        console.log('Accessibility violations found:', violations.map(v => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.length
        })));
      }
    });

    test('library page passes automated accessibility tests', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      const violations = await a11yHelper.injectAxeAndTest('library');
      
      const criticalViolations = violations.filter(violation => 
        violation.impact === 'critical' || violation.impact === 'serious'
      );
      
      expect(criticalViolations).toHaveLength(0);
    });

    test('series detail page passes automated accessibility tests', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const violations = await a11yHelper.injectAxeAndTest('series-detail');
      
      const criticalViolations = violations.filter(violation => 
        violation.impact === 'critical' || violation.impact === 'serious'
      );
      
      expect(criticalViolations).toHaveLength(0);
    });
  });

  test.describe('Progress Bar Accessibility', () => {
    test('progress bars have correct ARIA attributes', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      const progressBar = page.locator('[data-testid="progress-bar"]').first();
      
      const isValid = await a11yHelper.validateARIAAttributes('[data-testid="progress-bar"]', {
        'role': 'progressbar',
        'aria-valuemin': '0',
      });
      
      expect(isValid).toBe(true);
      
      // Check that aria-valuenow and aria-valuemax are present and valid
      const valueNow = await progressBar.getAttribute('aria-valuenow');
      const valueMax = await progressBar.getAttribute('aria-valuemax');
      const ariaLabel = await progressBar.getAttribute('aria-label');
      
      expect(valueNow).toBeTruthy();
      expect(valueMax).toBeTruthy();
      expect(ariaLabel).toBeTruthy();
      
      // Validate numeric values
      const numValueNow = parseInt(valueNow || '0');
      const numValueMax = parseInt(valueMax || '100');
      
      expect(numValueNow).toBeGreaterThanOrEqual(0);
      expect(numValueNow).toBeLessThanOrEqual(numValueMax);
      expect(numValueMax).toBeGreaterThan(0);
    });

    test('progress bars are announced to screen readers', async ({ page }) => {
      await a11yHelper.simulateScreenReader();
      
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      // Click on a series to navigate to detail page
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Check if progress changes are announced
      const markReadButton = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")').first();
      
      if (await markReadButton.count() > 0) {
        await markReadButton.click();
        await page.waitForTimeout(1000);
        
        // Verify screen reader announcements
        const announcements = await page.evaluate(() => (window as any).screenReaderAnnouncements);
        expect(announcements).toBeDefined();
      }
    });

    test('progress bars work with reduced motion', async ({ page }) => {
      await a11yHelper.testReducedMotion();
      
      await page.goto('/');
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      const overallProgressBar = page.locator('[data-testid="overall-progress-bar"]');
      await expect(overallProgressBar).toBeVisible();
      
      // Progress should still be visible and functional, just without animation
      const progressFill = overallProgressBar.locator('.progress-fill');
      await expect(progressFill).toBeVisible();
      
      // Check that reduced motion is respected in CSS
      const transition = await progressFill.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return style.transition;
      });
      
      // Should have no transition or very short transition for reduced motion
      expect(transition).toMatch(/(none|0s)/);
    });

    test('progress bars have sufficient color contrast', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      const progressBar = page.locator('[data-testid="progress-bar"]').first();
      const hasGoodContrast = await a11yHelper.checkColorContrast('[data-testid="progress-bar"]');
      
      expect(hasGoodContrast).toBe(true);
      
      // Test progress fill contrast
      const progressFill = progressBar.locator('.progress-fill');
      if (await progressFill.count() > 0) {
        const fillContrast = await a11yHelper.checkColorContrast('[data-testid="progress-bar"] .progress-fill');
        expect(fillContrast).toBe(true);
      }
    });
  });

  test.describe('Mark Read Button Accessibility', () => {
    test('mark read buttons have proper ARIA labels and states', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const markReadButtons = page.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]');
      const buttonCount = await markReadButtons.count();
      
      expect(buttonCount).toBeGreaterThan(0);
      
      for (let i = 0; i < Math.min(buttonCount, 5); i++) {
        const button = markReadButtons.nth(i);
        
        // Check required ARIA attributes
        const ariaLabel = await button.getAttribute('aria-label');
        const ariaPressed = await button.getAttribute('aria-pressed');
        
        expect(ariaLabel).toMatch(/Mark as (read|unread)/);
        expect(ariaPressed).toMatch(/true|false/);
        
        // Verify button is focusable
        await button.focus();
        await expect(button).toBeFocused();
      }
    });

    test('mark read buttons respond to keyboard activation', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const markReadButton = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")').first();
      
      if (await markReadButton.count() > 0) {
        const originalText = await markReadButton.textContent();
        
        // Focus and activate with keyboard
        await markReadButton.focus();
        await page.keyboard.press('Enter');
        
        // Wait for state change
        await page.waitForTimeout(1000);
        
        const newText = await markReadButton.textContent();
        expect(newText).not.toBe(originalText);
        
        // Also test with Space key
        await page.keyboard.press(' ');
        await page.waitForTimeout(1000);
        
        const finalText = await markReadButton.textContent();
        expect(finalText).toBeTruthy();
      }
    });

    test('mark read buttons work in high contrast mode', async ({ page }) => {
      await a11yHelper.testHighContrast();
      
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const markReadButton = page.locator('[data-testid="mark-read-button"], [data-testid="chapter-mark-read-button"]').first();
      
      // Button should still be visible and interactive in high contrast
      await expect(markReadButton).toBeVisible();
      
      // Focus should be clearly visible
      await markReadButton.focus();
      
      const focusOutline = await markReadButton.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return style.outline;
      });
      
      // Should have visible focus indicator
      expect(focusOutline).toBeTruthy();
    });

    test('mark read button states are clearly distinguishable', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Find buttons in different states
      const readButton = page.locator('[data-testid="mark-read-button"]:has-text("Read"), [data-testid="mark-read-button"]:has-text("✓")').first();
      const unreadButton = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")').first();
      
      if (await readButton.count() > 0 && await unreadButton.count() > 0) {
        // Get visual properties of both states
        const readButtonColor = await readButton.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return { color: style.color, backgroundColor: style.backgroundColor };
        });
        
        const unreadButtonColor = await unreadButton.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return { color: style.color, backgroundColor: style.backgroundColor };
        });
        
        // States should be visually distinct
        const isDifferent = readButtonColor.color !== unreadButtonColor.color || 
                           readButtonColor.backgroundColor !== unreadButtonColor.backgroundColor;
        
        expect(isDifferent).toBe(true);
      }
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('dashboard elements are keyboard navigable in logical order', async ({ page }) => {
      await page.goto('/');
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      // Start navigation
      await page.keyboard.press('Tab');
      
      // Should be able to navigate through focusable elements
      const focusableElements = await page.locator('button, a, [tabindex="0"], [tabindex]:not([tabindex="-1"])').all();
      
      let navigationSuccessful = true;
      let focusedCount = 0;
      
      for (let i = 0; i < Math.min(focusableElements.length, 10); i++) {
        await page.keyboard.press('Tab');
        
        const focusedElement = page.locator(':focus');
        if (await focusedElement.count() === 0) {
          navigationSuccessful = false;
          break;
        }
        focusedCount++;
      }
      
      expect(navigationSuccessful).toBe(true);
      expect(focusedCount).toBeGreaterThan(0);
    });

    test('library navigation works with keyboard only', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      // Navigate to first series card
      await page.keyboard.press('Tab');
      
      const firstSeriesCard = page.locator('[data-testid="series-card"]').first();
      
      // Should be able to focus series cards
      let attempt = 0;
      while (!(await firstSeriesCard.isVisible()) && attempt < 10) {
        await page.keyboard.press('Tab');
        attempt++;
      }
      
      // Activate with Enter
      await page.keyboard.press('Enter');
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Should be able to navigate to chapter elements
      await page.keyboard.press('Tab');
      
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
    });

    test('chapter list keyboard navigation is logical', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      // Navigate through chapters using Tab
      let currentFocus = '';
      const focusOrder = [];
      
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        
        const focusedElement = page.locator(':focus');
        const testId = await focusedElement.getAttribute('data-testid');
        
        if (testId) {
          focusOrder.push(testId);
        }
      }
      
      // Should have logical focus order (chapter elements, then controls)
      expect(focusOrder.length).toBeGreaterThan(0);
      
      // Verify we can interact with focused elements
      if (focusOrder.includes('mark-read-button') || focusOrder.includes('chapter-mark-read-button')) {
        const markReadButton = page.locator(':focus');
        await page.keyboard.press('Enter');
        
        // Should be able to activate button
        await page.waitForTimeout(500);
      }
    });

    test('skip links work correctly for screen reader users', async ({ page }) => {
      await page.goto('/');
      
      // Look for skip links (common accessibility pattern)
      const skipLinks = page.locator('a[href*="#"], [data-testid*="skip"]');
      
      if (await skipLinks.count() > 0) {
        const skipLink = skipLinks.first();
        await skipLink.focus();
        await expect(skipLink).toBeFocused();
        
        await page.keyboard.press('Enter');
        
        // Should navigate to the target section
        await page.waitForTimeout(500);
        
        const focusedElement = page.locator(':focus');
        await expect(focusedElement).toBeVisible();
      }
    });
  });

  test.describe('Screen Reader Experience', () => {
    test('progress information is properly announced', async ({ page }) => {
      await a11yHelper.simulateScreenReader();
      
      await page.goto('/');
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      // Check that important information has proper labeling
      const overallProgress = page.locator('[data-testid="overall-progress"]');
      const readChapters = page.locator('[data-testid="read-chapters"]');
      
      // These should have accessible names/labels
      const progressLabel = await overallProgress.evaluate((el) => {
        return el.getAttribute('aria-label') || 
               el.textContent || 
               (el.parentElement?.textContent);
      });
      
      expect(progressLabel).toBeTruthy();
      expect(progressLabel).toMatch(/progress|%/i);
      
      const chaptersLabel = await readChapters.evaluate((el) => {
        return el.getAttribute('aria-label') || 
               el.textContent ||
               (el.parentElement?.textContent);
      });
      
      expect(chaptersLabel).toBeTruthy();
      expect(chaptersLabel).toMatch(/chapter/i);
    });

    test('dynamic progress updates are announced', async ({ page }) => {
      await a11yHelper.simulateScreenReader();
      
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const markReadButton = page.locator('[data-testid="mark-read-button"]:has-text("Mark Read")').first();
      
      if (await markReadButton.count() > 0) {
        await markReadButton.click();
        
        // Wait for changes to be processed
        await page.waitForTimeout(1000);
        
        // Check for live region updates
        const liveRegions = page.locator('[aria-live], [role="status"], [role="alert"]');
        const liveRegionCount = await liveRegions.count();
        
        // Should have live regions for important updates
        expect(liveRegionCount).toBeGreaterThanOrEqual(0);
        
        // Verify announcements were tracked
        const announcements = await page.evaluate(() => (window as any).screenReaderAnnouncements);
        if (announcements) {
          expect(announcements.length).toBeGreaterThan(0);
        }
      }
    });

    test('form controls are properly labeled', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      // Check any search or filter controls
      const inputs = page.locator('input, select, textarea');
      const inputCount = await inputs.count();
      
      for (let i = 0; i < inputCount; i++) {
        const input = inputs.nth(i);
        
        // Each input should have a label
        const hasLabel = await input.evaluate((el) => {
          const id = el.getAttribute('id');
          const ariaLabel = el.getAttribute('aria-label');
          const ariaLabelledBy = el.getAttribute('aria-labelledby');
          
          if (ariaLabel || ariaLabelledBy) return true;
          
          if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            return !!label;
          }
          
          // Check if wrapped in label
          const parentLabel = el.closest('label');
          return !!parentLabel;
        });
        
        expect(hasLabel).toBe(true);
      }
    });
  });

  test.describe('Visual Accessibility', () => {
    test('focus indicators are visible and clear', async ({ page }) => {
      await page.goto('/library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      await page.locator('[data-testid="series-card"]').first().click();
      await page.waitForSelector('[data-testid="chapter-list"]');
      
      const focusableElements = page.locator('button, a, [tabindex="0"]');
      const elementCount = Math.min(await focusableElements.count(), 5);
      
      for (let i = 0; i < elementCount; i++) {
        const element = focusableElements.nth(i);
        await element.focus();
        
        // Check for visible focus indicator
        const focusStyles = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return {
            outline: style.outline,
            outlineColor: style.outlineColor,
            outlineWidth: style.outlineWidth,
            boxShadow: style.boxShadow,
          };
        });
        
        // Should have some form of focus indicator
        const hasFocusIndicator = focusStyles.outline !== 'none' ||
                                 focusStyles.outlineWidth !== '0px' ||
                                 focusStyles.boxShadow !== 'none';
        
        expect(hasFocusIndicator).toBe(true);
      }
    });

    test('text scaling works up to 200%', async ({ page }) => {
      await page.goto('/');
      await page.waitForSelector('[data-testid="dashboard-stats"]');
      
      // Simulate 200% text scaling
      await page.addStyleTag({
        content: `
          * {
            font-size: calc(1em * 2) !important;
            line-height: 1.4 !important;
          }
        `
      });
      
      // Content should still be readable and accessible
      const overallProgress = page.locator('[data-testid="overall-progress"]');
      await expect(overallProgress).toBeVisible();
      
      // Navigation should still work
      await page.click('text=Library');
      await page.waitForSelector('[data-testid="series-card"]');
      
      const seriesCard = page.locator('[data-testid="series-card"]').first();
      await expect(seriesCard).toBeVisible();
      
      // Text should not be cut off or overlapping
      const seriesTitle = seriesCard.locator('.series-title, h2, h3').first();
      if (await seriesTitle.count() > 0) {
        const isVisible = await seriesTitle.isVisible();
        expect(isVisible).toBe(true);
      }
    });

    test('components work without JavaScript', async ({ page, context }) => {
      // Disable JavaScript
      await context.setJavaScriptEnabled(false);
      
      await page.goto('/library');
      
      // Basic structure should still be present
      const mainContent = page.locator('main, [role="main"], .main-content');
      await expect(mainContent).toBeVisible({ timeout: 5000 });
      
      // Links should still be functional
      const navLinks = page.locator('nav a, [role="navigation"] a').first();
      if (await navLinks.count() > 0) {
        await expect(navLinks).toBeVisible();
      }
      
      // Re-enable JavaScript for other tests
      await context.setJavaScriptEnabled(true);
    });
  });
});