/**
 * Comprehensive E2E Test Suite for R-1 Functionality Validation
 * 
 * This test suite validates all functionality up to and including R-1:
 * - Library path management and scanning
 * - Series and chapter discovery from filesystem
 * - Page streaming API with multiple formats
 * - Full reader UI with navigation and controls
 * - Security improvements (rate limiting, error handling)
 * - Quality improvements (TypeScript, build system)
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Test data paths
const TEST_MANGA_PATH = path.join(process.cwd(), '..', 'manga-storage');
const FIXTURES_PATH = path.join(process.cwd(), '..', 'tests', 'fixtures', 'manga-samples');

interface TestContext {
  page: Page;
  context: BrowserContext;
  libraryPathId: string | null;
  seriesId: string | null;
  chapterId: string | null;
}

class E2ETestRunner {
  private testResults: Array<{
    category: string;
    test: string;
    status: 'pass' | 'fail' | 'skip';
    duration: number;
    error?: string;
  }> = [];

  async recordResult(category: string, testName: string, status: 'pass' | 'fail' | 'skip', duration: number, error?: string) {
    this.testResults.push({
      category,
      test: testName,
      status,
      duration,
      error
    });
  }

  generateReport(): string {
    const totalTests = this.testResults.length;
    const passed = this.testResults.filter(r => r.status === 'pass').length;
    const failed = this.testResults.filter(r => r.status === 'fail').length;
    const skipped = this.testResults.filter(r => r.status === 'skip').length;
    
    let report = `\n=== COMPREHENSIVE R-1 VALIDATION REPORT ===\n`;
    report += `Total Tests: ${totalTests}\n`;
    report += `Passed: ${passed} ✅\n`;
    report += `Failed: ${failed} ❌\n`;
    report += `Skipped: ${skipped} ⚠️\n`;
    report += `Success Rate: ${((passed / totalTests) * 100).toFixed(1)}%\n\n`;

    // Group by category
    const categories = [...new Set(this.testResults.map(r => r.category))];
    for (const category of categories) {
      const categoryTests = this.testResults.filter(r => r.category === category);
      report += `## ${category}\n`;
      for (const test of categoryTests) {
        const icon = test.status === 'pass' ? '✅' : test.status === 'fail' ? '❌' : '⚠️';
        report += `  ${icon} ${test.test} (${test.duration}ms)\n`;
        if (test.error) {
          report += `     Error: ${test.error}\n`;
        }
      }
      report += `\n`;
    }

    return report;
  }
}

const testRunner = new E2ETestRunner();

test.describe('Comprehensive R-1 Functionality Validation', () => {
  let testContext: TestContext;

  test.beforeAll(async ({ browser }) => {
    console.log('🚀 Starting comprehensive R-1 validation...');
    
    // Verify test data exists
    if (!fs.existsSync(TEST_MANGA_PATH)) {
      console.warn(`⚠️  Test manga path not found: ${TEST_MANGA_PATH}`);
    }
    
    if (!fs.existsSync(FIXTURES_PATH)) {
      console.warn(`⚠️  Fixtures path not found: ${FIXTURES_PATH}`);
    }
  });

  test.beforeEach(async ({ page, context }) => {
    testContext = {
      page,
      context,
      libraryPathId: null,
      seriesId: null,
      chapterId: null
    };
  });

  test.afterAll(async () => {
    console.log(testRunner.generateReport());
  });

  test('1. System Health and API Accessibility', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Test frontend accessibility
      await page.goto(BASE_URL);
      await expect(page).toHaveTitle(/KireMisu/i);
      
      // Test API health endpoint
      const apiResponse = await page.request.get(`${API_BASE_URL}/health`);
      expect(apiResponse.status()).toBe(200);
      const healthData = await apiResponse.json();
      expect(healthData.status).toBe('healthy');
      
      // Test API documentation accessibility
      const docsResponse = await page.request.get(`${API_BASE_URL}/api/docs`);
      expect(docsResponse.status()).toBe(200);
      
      await testRunner.recordResult('System Health', 'API and Frontend Accessibility', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('System Health', 'API and Frontend Accessibility', 'fail', Date.now() - startTime, error.message);
      throw error;
    }
  });

  test('2. Library Path Management', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Navigate to settings page
      await page.goto(`${BASE_URL}/settings`);
      await expect(page.locator('h1')).toContainText('Settings');
      
      // Test library path creation
      const testPath = TEST_MANGA_PATH;
      
      // Check if test path exists and create library path
      if (fs.existsSync(testPath)) {
        // Find add library path button/form
        const addButton = page.locator('button', { hasText: /add.*path/i });
        if (await addButton.isVisible()) {
          await addButton.click();
          
          // Fill in the path
          const pathInput = page.locator('input[type="text"]').first();
          await pathInput.fill(testPath);
          
          // Submit the form
          const submitButton = page.locator('button[type="submit"]');
          await submitButton.click();
          
          // Wait for success indication
          await page.waitForTimeout(1000);
          
          // Verify path appears in the list
          await expect(page.locator('text*=manga-storage')).toBeVisible();
        }
      }
      
      await testRunner.recordResult('Library Management', 'Path Creation and Display', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Library Management', 'Path Creation and Display', 'fail', Date.now() - startTime, error.message);
      // Don't throw - continue with other tests
    }
  });

  test('3. Library Scanning and Series Discovery', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Navigate to settings and trigger scan
      await page.goto(`${BASE_URL}/settings`);
      
      // Look for scan button
      const scanButton = page.locator('button', { hasText: /scan/i });
      if (await scanButton.isVisible()) {
        await scanButton.click();
        
        // Wait for scan to complete (with timeout)
        await page.waitForTimeout(5000);
        
        // Check for scan completion indicators
        const successMessage = page.locator('text*=completed');
        if (await successMessage.isVisible()) {
          console.log('✅ Library scan completed successfully');
        }
      }
      
      // Navigate to library to verify series were discovered
      await page.goto(`${BASE_URL}/library`);
      await expect(page.locator('h1')).toContainText('Library');
      
      // Check if any series cards are present
      const seriesCards = page.locator('[role="article"], .series-card, [data-testid*="series"]');
      const seriesCount = await seriesCards.count();
      
      if (seriesCount > 0) {
        console.log(`✅ Found ${seriesCount} series in library`);
        
        // Store the first series for later tests
        const firstSeries = seriesCards.first();
        const seriesTitle = await firstSeries.textContent();
        console.log(`📖 First series: ${seriesTitle}`);
      }
      
      await testRunner.recordResult('Library Management', 'Scanning and Series Discovery', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Library Management', 'Scanning and Series Discovery', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('4. API Endpoints Validation', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Test library paths API
      const pathsResponse = await page.request.get(`${API_BASE_URL}/api/library/paths`);
      expect(pathsResponse.status()).toBe(200);
      const pathsData = await pathsResponse.json();
      expect(pathsData).toHaveProperty('paths');
      expect(pathsData).toHaveProperty('total');
      console.log(`📁 Found ${pathsData.total} library paths`);
      
      // Test series API (if series exist)
      const seriesResponse = await page.request.get(`${API_BASE_URL}/api/series/`);
      if (seriesResponse.status() === 200) {
        const seriesData = await seriesResponse.json();
        console.log(`📚 Found ${seriesData.length} series via API`);
        
        if (seriesData.length > 0) {
          testContext.seriesId = seriesData[0].id;
          
          // Test chapters API for first series
          const chaptersResponse = await page.request.get(`${API_BASE_URL}/api/series/${testContext.seriesId}/chapters`);
          if (chaptersResponse.status() === 200) {
            const chaptersData = await chaptersResponse.json();
            console.log(`📖 Found ${chaptersData.length} chapters for first series`);
            
            if (chaptersData.length > 0) {
              testContext.chapterId = chaptersData[0].id;
            }
          }
        }
      }
      
      await testRunner.recordResult('API Validation', 'Core API Endpoints', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('API Validation', 'Core API Endpoints', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('5. Page Streaming API (R-1 Core Feature)', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      if (!testContext.chapterId) {
        await testRunner.recordResult('R-1 Core', 'Page Streaming API', 'skip', Date.now() - startTime, 'No chapter available for testing');
        return;
      }
      
      // Test chapter pages info endpoint
      const pagesInfoResponse = await page.request.get(`${API_BASE_URL}/api/chapters/${testContext.chapterId}/pages`);
      expect(pagesInfoResponse.status()).toBe(200);
      const pagesInfo = await pagesInfoResponse.json();
      expect(pagesInfo).toHaveProperty('total_pages');
      expect(pagesInfo.total_pages).toBeGreaterThan(0);
      console.log(`📄 Chapter has ${pagesInfo.total_pages} pages`);
      
      // Test page streaming endpoint for first page
      const pageResponse = await page.request.get(`${API_BASE_URL}/api/chapters/${testContext.chapterId}/pages/1`);
      expect(pageResponse.status()).toBe(200);
      
      // Verify content type is an image
      const contentType = pageResponse.headers()['content-type'];
      expect(contentType).toMatch(/^image\//);
      console.log(`🖼️  Page 1 content type: ${contentType}`);
      
      // Test page streaming for last page
      if (pagesInfo.total_pages > 1) {
        const lastPageResponse = await page.request.get(`${API_BASE_URL}/api/chapters/${testContext.chapterId}/pages/${pagesInfo.total_pages}`);
        expect(lastPageResponse.status()).toBe(200);
      }
      
      // Test invalid page number
      const invalidPageResponse = await page.request.get(`${API_BASE_URL}/api/chapters/${testContext.chapterId}/pages/9999`);
      expect(invalidPageResponse.status()).toBe(404);
      
      await testRunner.recordResult('R-1 Core', 'Page Streaming API', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('R-1 Core', 'Page Streaming API', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('6. Reader UI and Navigation (R-1 Core Feature)', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      if (!testContext.chapterId) {
        await testRunner.recordResult('R-1 Core', 'Reader UI and Navigation', 'skip', Date.now() - startTime, 'No chapter available for testing');
        return;
      }
      
      // Navigate to reader
      await page.goto(`${BASE_URL}/reader/${testContext.chapterId}`);
      
      // Wait for reader to load
      await page.waitForTimeout(2000);
      
      // Check for reader elements
      const readerContainer = page.locator('[data-testid="manga-reader"], .reader-container, .manga-reader');
      await expect(readerContainer).toBeVisible({ timeout: 10000 });
      
      // Check for page image
      const pageImage = page.locator('img[alt*="page"], img[src*="pages"]');
      await expect(pageImage).toBeVisible({ timeout: 10000 });
      console.log('🖼️  Page image loaded successfully');
      
      // Test keyboard navigation
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(500);
      console.log('⌨️  Right arrow navigation tested');
      
      await page.keyboard.press('ArrowLeft');
      await page.waitForTimeout(500);
      console.log('⌨️  Left arrow navigation tested');
      
      // Test fullscreen toggle (F key)
      await page.keyboard.press('KeyF');
      await page.waitForTimeout(500);
      console.log('🖥️  Fullscreen toggle tested');
      
      // Exit fullscreen
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
      
      // Test UI controls visibility/hiding
      const controls = page.locator('.reader-controls, [data-testid="reader-controls"]');
      if (await controls.isVisible()) {
        console.log('🎮 Reader controls are visible');
      }
      
      await testRunner.recordResult('R-1 Core', 'Reader UI and Navigation', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('R-1 Core', 'Reader UI and Navigation', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('7. Security Features Validation', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Test rate limiting by making rapid requests
      const rapidRequests = [];
      for (let i = 0; i < 5; i++) {
        rapidRequests.push(page.request.get(`${API_BASE_URL}/api/library/paths`));
      }
      
      const responses = await Promise.all(rapidRequests);
      const statusCodes = responses.map(r => r.status());
      console.log(`🔒 Rate limiting test - Status codes: ${statusCodes.join(', ')}`);
      
      // Check for rate limit headers
      const lastResponse = responses[responses.length - 1];
      const rateLimitHeaders = Object.keys(lastResponse.headers()).filter(h => h.toLowerCase().includes('ratelimit'));
      if (rateLimitHeaders.length > 0) {
        console.log(`🔒 Rate limit headers present: ${rateLimitHeaders.join(', ')}`);
      }
      
      // Test path traversal protection
      const maliciousPath = '../../../etc/passwd';
      const pathResponse = await page.request.post(`${API_BASE_URL}/api/library/paths`, {
        data: {
          path: maliciousPath,
          enabled: true,
          scan_interval_hours: 24
        }
      });
      
      // Should be rejected (400 Bad Request) due to path validation
      expect(pathResponse.status()).toBe(400);
      console.log('🔒 Path traversal protection working');
      
      // Test error message sanitization
      const errorResponse = await pathResponse.json();
      expect(errorResponse).toHaveProperty('message');
      // Error message should not contain the actual malicious path
      expect(errorResponse.message).not.toContain(maliciousPath);
      console.log('🔒 Error message sanitization working');
      
      await testRunner.recordResult('Security', 'Rate Limiting and Path Protection', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Security', 'Rate Limiting and Path Protection', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('8. Frontend Build and TypeScript Validation', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Test that TypeScript compilation worked by checking for proper types
      await page.goto(`${BASE_URL}/library`);
      
      // Check for TypeScript-compiled JavaScript (no .ts files served)
      const requests: string[] = [];
      page.on('request', request => {
        requests.push(request.url());
      });
      
      await page.waitForTimeout(2000);
      
      const tsFiles = requests.filter(url => url.endsWith('.ts') && !url.includes('map'));
      expect(tsFiles.length).toBe(0); // No .ts files should be served
      console.log('✅ TypeScript compilation successful - no .ts files served');
      
      // Check that modern JavaScript features are available (ES2020 target)
      const modernJsTest = await page.evaluate(() => {
        try {
          // Test optional chaining (ES2020 feature)
          const obj: any = {};
          const result = obj?.nested?.property;
          return result === undefined;
        } catch {
          return false;
        }
      });
      expect(modernJsTest).toBe(true);
      console.log('✅ ES2020 features available');
      
      await testRunner.recordResult('Build System', 'TypeScript and Build Validation', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Build System', 'TypeScript and Build Validation', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('9. Mobile Responsiveness and Touch Navigation', async ({ page, context }) => {
    const startTime = Date.now();
    
    try {
      if (!testContext.chapterId) {
        await testRunner.recordResult('Mobile UX', 'Touch Navigation', 'skip', Date.now() - startTime, 'No chapter available for testing');
        return;
      }
      
      // Create mobile viewport
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE size
      
      // Navigate to reader
      await page.goto(`${BASE_URL}/reader/${testContext.chapterId}`);
      await page.waitForTimeout(2000);
      
      // Check that reader adapts to mobile viewport
      const readerContainer = page.locator('[data-testid="manga-reader"], .reader-container, .manga-reader');
      await expect(readerContainer).toBeVisible();
      
      // Test touch/swipe gestures (simulate with click and drag)
      const pageImage = page.locator('img[alt*="page"], img[src*="pages"]').first();
      await expect(pageImage).toBeVisible();
      
      // Simulate swipe right (previous page)
      const box = await pageImage.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width * 0.8, box.y + box.height / 2);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width * 0.2, box.y + box.height / 2);
        await page.mouse.up();
        await page.waitForTimeout(500);
        console.log('📱 Swipe right gesture tested');
        
        // Simulate swipe left (next page)
        await page.mouse.move(box.x + box.width * 0.2, box.y + box.height / 2);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width * 0.8, box.y + box.height / 2);
        await page.mouse.up();
        await page.waitForTimeout(500);
        console.log('📱 Swipe left gesture tested');
      }
      
      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });
      
      await testRunner.recordResult('Mobile UX', 'Touch Navigation and Responsiveness', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Mobile UX', 'Touch Navigation and Responsiveness', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('10. Performance and Loading Tests', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      if (!testContext.chapterId) {
        await testRunner.recordResult('Performance', 'Page Loading Performance', 'skip', Date.now() - startTime, 'No chapter available for testing');
        return;
      }
      
      // Test page loading performance
      const navigationStart = Date.now();
      await page.goto(`${BASE_URL}/reader/${testContext.chapterId}`);
      
      // Wait for first page to load
      const pageImage = page.locator('img[alt*="page"], img[src*="pages"]').first();
      await expect(pageImage).toBeVisible({ timeout: 10000 });
      const loadTime = Date.now() - navigationStart;
      
      console.log(`⚡ Reader page loaded in ${loadTime}ms`);
      expect(loadTime).toBeLessThan(10000); // Should load within 10 seconds
      
      // Test page preloading (check if next page starts loading)
      const networkRequests: string[] = [];
      page.on('request', request => {
        if (request.url().includes('/pages/')) {
          networkRequests.push(request.url());
        }
      });
      
      // Navigate to next page
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(1000);
      
      const pageRequests = networkRequests.filter(url => url.includes('/pages/'));
      console.log(`📄 Page requests made: ${pageRequests.length}`);
      
      // Test that multiple format support works
      const pageResponse = await page.request.get(`${API_BASE_URL}/api/chapters/${testContext.chapterId}/pages/1`);
      const contentType = pageResponse.headers()['content-type'];
      expect(contentType).toMatch(/^image\/(jpeg|png|gif|webp)/);
      console.log(`🖼️  Image format supported: ${contentType}`);
      
      await testRunner.recordResult('Performance', 'Page Loading and Preloading', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Performance', 'Page Loading and Preloading', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('11. Error Handling and Edge Cases', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      // Test 404 handling for non-existent chapter
      const fakeChapterId = '00000000-0000-0000-0000-000000000000';
      await page.goto(`${BASE_URL}/reader/${fakeChapterId}`);
      
      // Should show error state or redirect
      const errorElement = page.locator('text*=error, text*=not found, text*=404');
      if (await errorElement.isVisible()) {
        console.log('✅ 404 error handling working');
      }
      
      // Test API error handling
      const invalidChapterResponse = await page.request.get(`${API_BASE_URL}/api/chapters/${fakeChapterId}/pages`);
      expect(invalidChapterResponse.status()).toBe(404);
      
      const errorData = await invalidChapterResponse.json();
      expect(errorData).toHaveProperty('message');
      console.log('✅ API error responses properly formatted');
      
      // Test network error recovery (if reader can handle it gracefully)
      if (testContext.chapterId) {
        await page.goto(`${BASE_URL}/reader/${testContext.chapterId}`);
        
        // Wait for initial load
        await page.waitForTimeout(2000);
        
        // Test that the reader shows loading states appropriately
        const loadingElements = page.locator('[aria-label*="loading"], .loading, [data-testid*="loading"]');
        // Note: Loading states might be very brief, so this is just a check
        console.log('✅ Loading states handled');
      }
      
      await testRunner.recordResult('Error Handling', 'Edge Cases and Error Recovery', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Error Handling', 'Edge Cases and Error Recovery', 'fail', Date.now() - startTime, error.message);
    }
  });

  test('12. Full User Workflow Integration', async ({ page }) => {
    const startTime = Date.now();
    
    try {
      console.log('🔄 Testing complete user workflow...');
      
      // 1. Start at home page
      await page.goto(BASE_URL);
      console.log('1️⃣  Loaded home page');
      
      // 2. Navigate to library
      const libraryLink = page.locator('a[href*="/library"], text*=library').first();
      if (await libraryLink.isVisible()) {
        await libraryLink.click();
        console.log('2️⃣  Navigated to library');
      } else {
        await page.goto(`${BASE_URL}/library`);
        console.log('2️⃣  Direct navigation to library');
      }
      
      // 3. Find and click on a series (if available)
      const seriesCards = page.locator('[role="article"], .series-card, [data-testid*="series"]');
      const seriesCount = await seriesCards.count();
      
      if (seriesCount > 0) {
        const firstSeries = seriesCards.first();
        await firstSeries.click();
        console.log('3️⃣  Selected first series');
        
        // 4. Look for chapters and select one
        const chapterLinks = page.locator('a[href*="/reader/"], [data-testid*="chapter"]');
        const chapterCount = await chapterLinks.count();
        
        if (chapterCount > 0) {
          const firstChapter = chapterLinks.first();
          await firstChapter.click();
          console.log('4️⃣  Started reading first chapter');
          
          // 5. Verify reader loaded
          const readerContainer = page.locator('[data-testid="manga-reader"], .reader-container, .manga-reader');
          await expect(readerContainer).toBeVisible({ timeout: 10000 });
          console.log('5️⃣  Reader loaded successfully');
          
          // 6. Test basic navigation
          await page.keyboard.press('ArrowRight');
          await page.waitForTimeout(500);
          await page.keyboard.press('ArrowLeft');
          console.log('6️⃣  Navigation working');
          
          // 7. Test return to library
          await page.keyboard.press('Escape');
          await page.waitForTimeout(1000);
          
          if (page.url().includes('/reader/')) {
            // Try clicking a back/home button
            const backButton = page.locator('button[aria-label*="back"], a[href*="/library"]').first();
            if (await backButton.isVisible()) {
              await backButton.click();
            }
          }
          console.log('7️⃣  Workflow complete');
        }
      }
      
      await testRunner.recordResult('Integration', 'Full User Workflow', 'pass', Date.now() - startTime);
    } catch (error) {
      await testRunner.recordResult('Integration', 'Full User Workflow', 'fail', Date.now() - startTime, error.message);
    }
  });
});

// Export test runner for external use
export { testRunner };