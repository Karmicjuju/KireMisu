/**
 * Jest Setup for KireMisu Tests
 * Configures testing environment for unit and integration tests
 */

import '@testing-library/jest-dom';

// Mock useKeyboardNavigation hook
jest.mock('@/components/reader/use-keyboard-navigation', () => ({
  useKeyboardNavigation: jest.fn(() => ({
    shortcuts: {
      'ArrowLeft': jest.fn(),
      'ArrowRight': jest.fn(), 
      'Home': jest.fn(),
      'End': jest.fn(),
      'Escape': jest.fn()
    },
    isActive: true
  }))
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/library',
    query: {},
    asPath: '/library'
  }),
  usePathname: () => '/library',
  useSearchParams: () => new URLSearchParams()
}));

// Mock Next.js link
jest.mock('next/link', () => {
  const React = require('react');
  const Link = ({ children, href, ...props }: any) => {
    return React.createElement('a', { href, ...props }, children);
  };
  Link.displayName = 'Link';
  return Link;
});

// Mock window.matchMedia for responsive design tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

Object.defineProperty(global, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

// Mock ResizeObserver
class MockResizeObserver {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: MockResizeObserver,
});

// Set up test environment variables
process.env.NODE_ENV = 'test';
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_TEST_MODE = 'true';