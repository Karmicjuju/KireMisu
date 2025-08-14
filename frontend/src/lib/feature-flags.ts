/**
 * Feature flags for environment-based functionality
 * Enables secure separation between production and testing code
 */

export type AuthMethod = 'secure_cookies' | 'test_bypass';
export type Environment = 'production' | 'development' | 'test';

/**
 * Get current environment
 */
export function getEnvironment(): Environment {
  if (typeof window === 'undefined') {
    // Server-side
    return (process.env.NODE_ENV as Environment) || 'development';
  }
  
  // Client-side - check for Next.js public env vars
  const publicEnv = process.env.NEXT_PUBLIC_NODE_ENV;
  return (publicEnv as Environment) || (process.env.NODE_ENV as Environment) || 'development';
}

/**
 * Check if we're in test mode
 */
export function isTestMode(): boolean {
  return getEnvironment() === 'test' || 
         process.env.NEXT_PUBLIC_TEST_MODE === 'true';
}

/**
 * Check if we're in production mode
 */
export function isProductionMode(): boolean {
  return getEnvironment() === 'production';
}

/**
 * Check if we're in development mode
 */
export function isDevelopmentMode(): boolean {
  return getEnvironment() === 'development';
}

/**
 * Get the authentication method to use
 */
export function getAuthMethod(): AuthMethod {
  if (isTestMode() || process.env.AUTH_BYPASS_ENABLED === 'true') {
    return 'test_bypass';
  }
  return 'secure_cookies';
}

/**
 * Check if test authentication bypass is enabled
 */
export function useTestAuth(): boolean {
  return getAuthMethod() === 'test_bypass';
}

/**
 * Check if secure cookie authentication should be used
 */
export function useSecureAuth(): boolean {
  return getAuthMethod() === 'secure_cookies';
}

/**
 * Get API URL based on environment
 */
export function getApiUrl(): string {
  // Server-side (SSR, API routes): use internal Docker network URL
  if (typeof window === 'undefined') {
    if (isTestMode()) {
      return process.env.TEST_BACKEND_URL || 'http://backend-test:8000';
    }
    return process.env.BACKEND_URL || 'http://backend:8000';
  }
  
  // Client-side (browser): use public URL
  if (isTestMode()) {
    return process.env.NEXT_PUBLIC_TEST_API_URL || 'http://localhost:8001';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

/**
 * Check if CSRF protection should be enabled
 */
export function useCSRFProtection(): boolean {
  return isProductionMode() || (isDevelopmentMode() && process.env.ENABLE_CSRF === 'true');
}

/**
 * Check if rate limiting should be enabled
 */
export function useRateLimiting(): boolean {
  return !isTestMode() || process.env.ENABLE_RATE_LIMITING_IN_TESTS === 'true';
}

/**
 * Get JWT storage method
 */
export function getJWTStorageMethod(): 'httponly_cookies' | 'test_mode' | 'localStorage' {
  if (isTestMode()) {
    return 'test_mode';
  }
  if (isProductionMode()) {
    return 'httponly_cookies';
  }
  // Development - allow both for migration
  return process.env.JWT_STORAGE as any || 'httponly_cookies';
}

/**
 * Feature flags object for easy access
 */
export const featureFlags = {
  environment: getEnvironment(),
  isTest: isTestMode(),
  isProduction: isProductionMode(),
  isDevelopment: isDevelopmentMode(),
  authMethod: getAuthMethod(),
  useTestAuth: useTestAuth(),
  useSecureAuth: useSecureAuth(),
  apiUrl: getApiUrl(),
  useCSRFProtection: useCSRFProtection(),
  useRateLimiting: useRateLimiting(),
  jwtStorageMethod: getJWTStorageMethod(),
} as const;

/**
 * Runtime feature flag validation
 */
export function validateFeatureFlags(): string[] {
  const errors: string[] = [];
  
  if (isProductionMode() && useTestAuth()) {
    errors.push('Test authentication is enabled in production mode');
  }
  
  if (isProductionMode() && getJWTStorageMethod() !== 'httponly_cookies') {
    errors.push('Insecure JWT storage method in production mode');
  }
  
  if (!isTestMode() && !useRateLimiting()) {
    errors.push('Rate limiting disabled outside of test mode');
  }
  
  return errors;
}