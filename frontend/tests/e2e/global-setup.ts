/**
 * Global Setup for KireMisu E2E Tests
 * Ensures test environment is properly configured
 */

import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Setting up E2E test environment...');
  
  // Launch browser for setup
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // Wait for the application to be ready
    const baseURL = config.webServer?.url || 'http://localhost:3000';
    console.log(`📡 Checking application availability at ${baseURL}`);
    
    await page.goto(baseURL, { 
      waitUntil: 'domcontentloaded',
      timeout: 30000 
    });
    
    // Wait for initial content to load instead of network idle
    await page.waitForTimeout(2000);
    
    // Verify the app is responding
    await page.waitForSelector('body', { timeout: 10000 });
    console.log('✅ Application is ready');
    
    // Set up test data if needed
    await setupTestData(page);
    
    // Configure test environment
    await configureTestEnvironment(page);
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
  
  console.log('✅ E2E test environment setup complete');
}

async function setupTestData(page: any) {
  console.log('📝 Setting up test data...');
  
  // Clear any existing test data
  await page.evaluate(() => {
    // Clear local storage
    localStorage.clear();
    // Clear session storage
    sessionStorage.clear();
    // Clear any IndexedDB data if used
    if ('indexedDB' in window) {
      // Note: Full IndexedDB clearing would require more complex logic
    }
  });
  
  // Set up test configuration in localStorage
  await page.evaluate(() => {
    const testConfig = {
      pollingEnabled: false,
      websocketEnabled: false,
      animationsDisabled: true,
      testMode: true,
      // Reduce timeouts for faster tests
      notificationTimeout: 1000,
      toastTimeout: 2000
    };
    
    localStorage.setItem('kiremisu-test-config', JSON.stringify(testConfig));
  });
  
  console.log('✅ Test data setup complete');
}

async function configureTestEnvironment(page: any) {
  console.log('⚙️ Configuring test environment...');
  
  // Disable animations via CSS
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
      
      /* Disable smooth scrolling */
      html {
        scroll-behavior: auto !important;
      }
      
      /* Make portals render instantly */
      .animate-in {
        animation: none !important;
      }
      
      /* Remove toast animations */
      .toast {
        transition: none !important;
      }
    `
  });
  
  // Override window methods that might cause timing issues
  await page.evaluate(() => {
    // Mock setTimeout/setInterval to be faster in tests
    const originalSetTimeout = window.setTimeout;
    const originalSetInterval = window.setInterval;
    
    window.setTimeout = ((fn: Function, delay: number = 0, ...args: any[]) => {
      // Reduce delays in test environment
      const testDelay = Math.min(delay, delay > 1000 ? 100 : delay);
      return originalSetTimeout(fn, testDelay, ...args);
    }) as typeof setTimeout;
    
    window.setInterval = ((fn: Function, delay: number = 0, ...args: any[]) => {
      // Reduce intervals in test environment
      const testDelay = Math.min(delay, delay > 5000 ? 1000 : delay);
      return originalSetInterval(fn, testDelay, ...args);
    }) as typeof setInterval;
    
    // Disable requestAnimationFrame delays
    window.requestAnimationFrame = (callback: FrameRequestCallback) => {
      return setTimeout(callback, 0);
    };
  });
  
  console.log('✅ Test environment configuration complete');
}

export default globalSetup;