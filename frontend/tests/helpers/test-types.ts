/**
 * Test Type Helpers
 * Utilities to identify and configure different test types
 */

/**
 * Test type identification based on file path
 */
export function getTestType(testPath: string): 'unit' | 'integration' | 'e2e' {
  if (testPath.includes('/tests/unit/')) return 'unit';
  if (testPath.includes('/tests/integration/')) return 'integration';
  if (testPath.includes('/tests/e2e/')) return 'e2e';
  
  // Default fallback based on file location
  if (testPath.includes('src/')) return 'unit';
  return 'integration';
}

/**
 * Check if current test should use Jest mocks (unit tests)
 */
export function shouldUseJestMocks(): boolean {
  const testPath = expect.getState().testPath || '';
  return getTestType(testPath) === 'unit';
}

/**
 * Check if current test should use nock (integration tests)
 */
export function shouldUseNock(): boolean {
  const testPath = expect.getState().testPath || '';
  return getTestType(testPath) === 'integration';
}

/**
 * Environment helper for test debugging
 */
export function getTestEnvironmentInfo() {
  return {
    testPath: expect.getState().testPath || 'unknown',
    testType: getTestType(expect.getState().testPath || ''),
    nodeEnv: process.env.NODE_ENV,
    apiUrl: process.env.NEXT_PUBLIC_API_URL
  };
}