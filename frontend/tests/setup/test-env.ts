/**
 * Test Environment Setup
 * Configures the testing environment for KireMisu E2E tests
 */

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.NEXT_PUBLIC_TEST_MODE = 'true';
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';

// Disable polling and websockets for tests
process.env.NEXT_PUBLIC_POLLING_ENABLED = 'false';
process.env.NEXT_PUBLIC_WEBSOCKET_ENABLED = 'false';

// Reduce animation timings
process.env.NEXT_PUBLIC_ANIMATION_DURATION = '0';

// Configure test timeouts
process.env.PLAYWRIGHT_TEST_TIMEOUT = '30000';
process.env.PLAYWRIGHT_EXPECT_TIMEOUT = '10000';