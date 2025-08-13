/**
 * MSW Setup for KireMisu E2E Tests
 * Configures Mock Service Worker for API mocking
 */

import { setupServer } from 'msw/node';
import { setupWorker } from 'msw/browser';
import apiHandlers from '../mocks/api-handlers';

// Setup for Node.js environment (Jest tests)
export const server = setupServer(...apiHandlers);

// Setup for browser environment (Playwright E2E tests)
export const worker = setupWorker(...apiHandlers);

/**
 * Start MSW server for Node.js tests
 */
export function startMswServer() {
  server.listen({
    onUnhandledRequest: 'warn'
  });
}

/**
 * Stop MSW server
 */
export function stopMswServer() {
  server.close();
}

/**
 * Reset MSW handlers between tests
 */
export function resetMswHandlers() {
  server.resetHandlers();
}

/**
 * Start MSW worker for browser tests
 */
export async function startMswWorker() {
  await worker.start({
    onUnhandledRequest: 'warn'
  });
}

/**
 * Stop MSW worker
 */
export function stopMswWorker() {
  worker.stop();
}