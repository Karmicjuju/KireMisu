/**
 * Authentication Setup for E2E Tests
 * Handles login and stores authentication state for reuse across tests
 * Improved version with better React hydration handling and network monitoring
 */

import { test as setup, expect, Response } from '@playwright/test';
import path from 'path';

// Path to store authenticated state
const authFile = path.join(__dirname, '../../.auth/user.json');

// Get test credentials from environment variables
const getTestCredentials = () => {
  const username = process.env.E2E_TEST_USERNAME || process.env.KIREMISU_TEST_USERNAME;
  const password = process.env.E2E_TEST_PASSWORD || process.env.KIREMISU_TEST_PASSWORD;
  
  if (!username) {
    throw new Error(
      'E2E_TEST_USERNAME environment variable is required for authentication setup. ' +
      'Set it before running tests: E2E_TEST_USERNAME=your_username'
    );
  }
  
  if (!password) {
    throw new Error(
      'E2E_TEST_PASSWORD environment variable is required for authentication setup. ' +
      'Set it before running tests: E2E_TEST_PASSWORD=your_password'
    );
  }
  
  console.log(`🔐 Authentication setup using credentials for user: ${username}`);
  return { username, password };
};

const TEST_CREDENTIALS = getTestCredentials();

/**
 * Wait for React hydration to complete and page to be fully interactive
 */
async function waitForPageHydration(page: any, maxRetries = 5) {
  console.log('Waiting for React hydration to complete...');
  
  for (let retry = 0; retry < maxRetries; retry++) {
    try {
      // Wait for the page to load completely
      await page.waitForLoadState('domcontentloaded');
      
      // Try a shorter timeout for networkidle, but don't fail if it doesn't reach it
      try {
        await page.waitForLoadState('networkidle', { timeout: 3000 });
      } catch (e) {
        console.log('Network not idle yet, continuing...');
      }
      
      // Check if we see JavaScript code in the body (hydration issue)
      const bodyText = await page.locator('body').textContent();
      if (bodyText && (bodyText.includes('document.documentElement') || bodyText.includes('function('))) {
        console.log(`Hydration issue detected (attempt ${retry + 1}), retrying...`);
        await page.waitForTimeout(1000 * (retry + 1)); // Exponential backoff
        await page.reload({ waitUntil: 'domcontentloaded' });
        continue;
      }
      
      // Wait for React components to be mounted - either login form or authenticated state
      await page.waitForFunction(() => {
        // Check if React is loaded and components are mounted
        return window.React || 
               document.querySelector('[data-testid="login-form"]') !== null ||
               document.querySelector('[data-testid="sidebar"]') !== null ||
               document.querySelector('main') !== null;
      }, { timeout: 10000 });
      
      console.log('Page hydration complete');
      return;
    } catch (error) {
      console.log(`Hydration check failed (attempt ${retry + 1}):`, error.message);
      if (retry < maxRetries - 1) {
        await page.waitForTimeout(2000);
        await page.reload({ waitUntil: 'domcontentloaded' });
      } else {
        throw new Error('Failed to achieve proper page hydration after retries');
      }
    }
  }
}

/**
 * Wait for login form to be fully ready for interaction
 */
async function waitForLoginFormReady(page: any) {
  console.log('Waiting for login form to be ready...');
  
  // Wait for form element to exist and be visible
  await page.waitForSelector('[data-testid="login-form"]', { 
    state: 'visible',
    timeout: 15000 
  });
  
  // Wait for input fields to be ready
  await page.waitForSelector('[data-testid="username-input"]', { 
    state: 'visible',
    timeout: 5000 
  });
  await page.waitForSelector('[data-testid="password-input"]', { 
    state: 'visible', 
    timeout: 5000 
  });
  await page.waitForSelector('[data-testid="login-button"]', { 
    state: 'visible',
    timeout: 5000 
  });
  
  // Ensure inputs are not disabled
  await expect(page.locator('[data-testid="username-input"]')).toBeEnabled();
  await expect(page.locator('[data-testid="password-input"]')).toBeEnabled();
  await expect(page.locator('[data-testid="login-button"]')).toBeEnabled();
  
  // Wait for any loading spinners to disappear
  await page.locator('.animate-spin').waitFor({ state: 'hidden', timeout: 2000 }).catch(() => {
    // Ignore if no spinners found
  });
  
  console.log('Login form is ready for interaction');
}

/**
 * Fill login form with enhanced reliability
 */
async function fillLoginForm(page: any, credentials: typeof TEST_CREDENTIALS) {
  console.log('Filling login form...');
  
  // Focus and clear username field, then fill it
  const usernameInput = page.locator('[data-testid="username-input"]');
  await usernameInput.focus();
  await usernameInput.fill(''); // Clear any existing value
  await page.waitForTimeout(100);
  await usernameInput.type(credentials.username, { delay: 30 });
  
  // Focus and clear password field, then fill it
  const passwordInput = page.locator('[data-testid="password-input"]');
  await passwordInput.focus();
  await passwordInput.fill(''); // Clear any existing value
  await page.waitForTimeout(100);
  await passwordInput.type(credentials.password, { delay: 30 });
  
  // Wait for values to settle
  await page.waitForTimeout(300);
  
  // Verify form is filled correctly
  const usernameValue = await usernameInput.inputValue();
  const passwordValue = await passwordInput.inputValue();
  
  console.log('Form filled with:', { 
    username: usernameValue, 
    password: passwordValue ? '[REDACTED]' : 'empty',
    usernameLength: usernameValue.length,
    passwordLength: passwordValue.length
  });
  
  if (!usernameValue || !passwordValue) {
    throw new Error(`Form fields not filled properly: username="${usernameValue}", password length=${passwordValue.length}`);
  }
  
  if (usernameValue !== credentials.username) {
    throw new Error(`Username mismatch: expected "${credentials.username}", got "${usernameValue}"`);
  }
}

/**
 * Submit login form and monitor network requests
 */
async function submitLoginForm(page: any) {
  console.log('Submitting login form...');
  
  // Set up network request monitoring
  let loginRequest: Response | null = null;
  let loginResponse: Response | null = null;
  
  // Monitor login API call
  page.on('request', (request: any) => {
    if (request.url().includes('/api/auth/login') && request.method() === 'POST') {
      console.log('Login API request detected:', request.url());
      loginRequest = request;
    }
  });
  
  page.on('response', (response: any) => {
    if (response.url().includes('/api/auth/login') && response.request().method() === 'POST') {
      console.log('Login API response received:', response.status(), response.url());
      loginResponse = response;
    }
  });
  
  // Check for existing errors before submitting
  const existingErrorCount = await page.locator('div.bg-destructive\\/15').count();
  if (existingErrorCount > 0) {
    const errorText = await page.locator('div.bg-destructive\\/15 p').textContent();
    console.log('Pre-existing error found:', errorText);
  }
  
  // Click submit button
  await page.locator('[data-testid="login-button"]').click();
  
  // Wait for login request to be sent and response received
  try {
    await page.waitForResponse(
      (response: any) => response.url().includes('/api/auth/login') && response.request().method() === 'POST',
      { timeout: 10000 }
    );
    console.log('Login API call completed');
  } catch (error) {
    console.error('No login API response received within timeout');
    
    // Check if there's a network error or the form is still visible
    const formStillVisible = await page.locator('[data-testid="login-form"]').isVisible();
    const pageContent = await page.locator('body').textContent();
    
    console.log('Debug info:', {
      formStillVisible,
      pageContentSample: pageContent?.substring(0, 200),
      currentUrl: page.url()
    });
    
    throw new Error('Login API request did not complete within expected timeframe');
  }
  
  // Check for authentication errors
  await page.waitForTimeout(1000); // Allow time for error messages to appear
  
  const errorCount = await page.locator('div.bg-destructive\\/15').count();
  if (errorCount > 0) {
    const errorText = await page.locator('div.bg-destructive\\/15 p').textContent();
    console.log('Login error detected:', errorText);
    throw new Error(`Authentication failed: ${errorText}`);
  }
  
  console.log('Login form submitted successfully');
}

/**
 * Wait for successful authentication and navigation
 */
async function waitForAuthenticationSuccess(page: any) {
  console.log('Waiting for authentication success...');
  
  // Wait for login form to disappear or navigation to occur
  try {
    // Option 1: Wait for login form to become hidden (indicates navigation started)
    await page.waitForSelector('[data-testid="login-form"]', { 
      state: 'hidden', 
      timeout: 10000 
    });
    console.log('Login form hidden - navigation in progress');
  } catch (error) {
    // Option 2: Check if we're still on the same page with form visible
    const loginFormVisible = await page.locator('[data-testid="login-form"]').isVisible();
    const currentUrl = page.url();
    
    if (loginFormVisible && currentUrl.includes('localhost:3000') && !currentUrl.includes('/library')) {
      const pageContent = await page.locator('body').textContent();
      console.log('Authentication failed - still on login page:', {
        url: currentUrl,
        formVisible: loginFormVisible,
        contentSample: pageContent?.substring(0, 200)
      });
      throw new Error('Authentication failed - login form still visible');
    }
  }
  
  // Wait for navigation to complete
  try {
    await page.waitForURL('**/library', { timeout: 8000 });
    console.log('Successfully navigated to library page');
  } catch (error) {
    console.log('URL navigation timeout, checking current state...');
    
    // Check current URL and page state
    const currentUrl = page.url();
    const hasLibraryContent = await page.locator('h1').textContent().then(
      text => text?.includes('Library') || text?.includes('Welcome back')
    ).catch(() => false);
    
    console.log('Current state:', { currentUrl, hasLibraryContent });
    
    // If we're not on library page but have library content, that's still success
    if (!currentUrl.includes('/library') && !hasLibraryContent) {
      throw new Error(`Navigation failed - expected library page, got: ${currentUrl}`);
    }
  }
  
  // Wait for React to re-hydrate after navigation
  await waitForPageHydration(page, 3);
  
  // Wait for authenticated UI elements
  console.log('Waiting for authenticated UI elements...');
  await page.waitForSelector('[data-testid="sidebar"]', { 
    state: 'visible',
    timeout: 10000 
  });
  
  // Verify authentication success
  await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
  
  // Verify we have library content (either "Library" or "Welcome back!")
  const headingText = await page.locator('h1').first().textContent();
  console.log('Main heading:', headingText);
  
  if (!headingText?.includes('Library') && !headingText?.includes('Welcome back')) {
    throw new Error(`Unexpected page content after authentication: "${headingText}"`);
  }
  
  console.log('Authentication and navigation completed successfully');
}

setup('authenticate', async ({ page }) => {
  console.log('🔐 Starting authentication setup...');
  
  try {
    // Navigate to the application
    console.log('Navigating to application...');
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    
    // Wait for React hydration and page to be interactive
    await waitForPageHydration(page);
    
    // Check if user is already authenticated
    console.log('Checking authentication state...');
    const hasLoginForm = await page.locator('[data-testid="login-form"]').isVisible();
    const hasSidebar = await page.locator('[data-testid="sidebar"]').isVisible();
    
    if (hasSidebar && !hasLoginForm) {
      console.log('✅ User is already authenticated');
      
      // Save the existing authenticated state
      console.log('Saving existing authentication state...');
      await page.context().storageState({ path: authFile });
      
      console.log('✅ Authentication setup completed successfully (already authenticated)');
      return;
    }
    
    if (!hasLoginForm && !hasSidebar) {
      console.log('Neither login form nor sidebar found, trying to verify session...');
      
      // Try to manually set auth cookies and verify session
      try {
        await page.context().addCookies([
          {
            name: 'session',
            value: 'admin-session-placeholder',
            domain: 'localhost',
            path: '/',
            httpOnly: true,
            secure: false
          }
        ]);
        
        // Try to verify if we can bypass login
        const response = await page.request.post('http://localhost:8000/api/auth/login', {
          data: {
            username_or_email: TEST_CREDENTIALS.username,
            password: TEST_CREDENTIALS.password
          }
        });
        
        if (response.ok()) {
          const loginData = await response.json();
          console.log('Direct API login successful, auth method:', loginData.auth_method);
          
          // Navigate to library to confirm authentication
          await page.goto('/library', { waitUntil: 'domcontentloaded' });
          await waitForPageHydration(page);
          
          // Check for authenticated UI
          const sidebarVisible = await page.locator('[data-testid="sidebar"]').isVisible();
          if (sidebarVisible) {
            console.log('✅ Authentication successful via API, proceeding...');
            // Save the authentication state
            await page.context().storageState({ path: authFile });
            console.log('✅ Authentication setup completed successfully (API bypass)');
            return;
          }
        }
      } catch (error) {
        console.log('API bypass failed, will try form login:', error.message);
      }
      
      // Fallback: Try navigating to a protected route to force login redirect
      console.log('Forcing navigation to login...');
      await page.goto('/library', { waitUntil: 'domcontentloaded' });
      await waitForPageHydration(page);
    }
    
    // Wait for login form to be ready
    await waitForLoginFormReady(page);
    
    // Fill the login form
    await fillLoginForm(page, TEST_CREDENTIALS);
    
    // Submit the form and monitor network
    await submitLoginForm(page);
    
    // Wait for authentication success
    await waitForAuthenticationSuccess(page);
    
    // Save authenticated state for other tests
    console.log('Saving authentication state...');
    await page.context().storageState({ path: authFile });
    
    console.log('✅ Authentication setup completed successfully');
  } catch (error) {
    console.error('❌ Authentication setup failed:', error.message);
    
    // Capture additional debug information
    const currentUrl = page.url();
    const pageTitle = await page.title();
    const hasLoginForm = await page.locator('[data-testid="login-form"]').isVisible();
    const hasSidebar = await page.locator('[data-testid="sidebar"]').isVisible();
    
    console.error('Debug information:', {
      currentUrl,
      pageTitle,
      hasLoginForm,
      hasSidebar
    });
    
    throw error;
  }
});