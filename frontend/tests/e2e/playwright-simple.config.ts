/**
 * Simplified Playwright Configuration for Watching System Tests
 * Uses environment variables for credentials (loads from .env.test if present)
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  
  // Run tests in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter to use
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  
  // Global test timeout
  timeout: 30000,
  
  // Expect timeout for assertions
  expect: {
    timeout: 5000
  },
  
  use: {
    // Base URL for tests
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Take screenshot on failure
    screenshot: 'only-on-failure',
    
    // Record video on failure
    video: 'retain-on-failure',
    
    // Ignore HTTPS errors (for local development)
    ignoreHTTPSErrors: true,
    
    // Disable animations for more stable tests
    reducedMotion: 'reduce',
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Disable web security for testing
        launchOptions: {
          args: [
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--no-sandbox',
            '--disable-dev-shm-usage'
          ]
        }
      },
    },
  ],

  // No web server configuration - expect app to be running
});