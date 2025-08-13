/**
 * Playwright Configuration for KireMisu E2E Tests
 * Optimized for watching system and notification testing
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter to use
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    process.env.CI ? ['github'] : ['list']
  ],
  
  // Global test timeout
  timeout: 60000,
  
  // Expect timeout for assertions
  expect: {
    timeout: 10000
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
    
    // Extra headers for API calls
    extraHTTPHeaders: {
      // Disable caching to ensure fresh data
      'Cache-Control': 'no-cache',
    },
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
            // Disable animations for more predictable tests
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            // Reduce flakiness
            '--no-sandbox',
            '--disable-dev-shm-usage'
          ]
        }
      },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Test against mobile viewports
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },

    // Microsoft Edge
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
  ],

  // Web server configuration for local development
  webServer: {
    command: process.env.CI 
      ? 'npm run build && npm run start' 
      : 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: {
      // Test environment variables
      NODE_ENV: 'test',
      NEXT_PUBLIC_API_URL: 'http://localhost:8000',
      
      // Disable polling and websockets for tests
      NEXT_PUBLIC_POLLING_ENABLED: 'false',
      NEXT_PUBLIC_WEBSOCKET_ENABLED: 'false',
      
      // Reduce animation timings
      NEXT_PUBLIC_ANIMATION_DURATION: '0',
      
      // Enable test mode features
      NEXT_PUBLIC_TEST_MODE: 'true',
    }
  },

  // Global setup and teardown
  globalSetup: require.resolve('./global-setup.ts'),
  globalTeardown: require.resolve('./global-teardown.ts'),
  
  // Setup files
  setupFiles: [require.resolve('../setup/test-env.ts')],
});