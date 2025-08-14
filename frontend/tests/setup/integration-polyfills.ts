/**
 * Polyfills for integration tests using nock
 * Addresses nock's dependency on @mswjs/interceptors
 */

import { TextDecoder, TextEncoder } from 'util';

// CRITICAL: Set polyfills BEFORE any imports that might need them
(global as any).TextEncoder = TextEncoder;
(global as any).TextDecoder = TextDecoder;

// Mock minimal web APIs that nock's dependencies expect
(global as any).Response = class MockResponse {
  constructor(body?: any, init?: any) {
    this.body = body;
    this.status = init?.status || 200;
    this.statusText = init?.statusText || 'OK';
    this.headers = new Map();
  }
  
  async json() {
    return typeof this.body === 'string' ? JSON.parse(this.body) : this.body;
  }
  
  async text() {
    return typeof this.body === 'string' ? this.body : JSON.stringify(this.body);
  }
  
  clone() {
    return new (global as any).Response(this.body, {
      status: this.status,
      statusText: this.statusText
    });
  }
};

(global as any).Request = class MockRequest {
  constructor(input: any, init?: any) {
    this.url = typeof input === 'string' ? input : input.url;
    this.method = init?.method || 'GET';
    this.headers = new Map();
    this.body = init?.body;
  }
  
  clone() {
    return new (global as any).Request(this.url, {
      method: this.method,
      headers: this.headers,
      body: this.body
    });
  }
};

(global as any).Headers = class MockHeaders extends Map {
  constructor(init?: any) {
    super();
    if (init) {
      if (Array.isArray(init)) {
        init.forEach(([key, value]) => this.set(key, value));
      } else if (typeof init === 'object') {
        Object.entries(init).forEach(([key, value]) => this.set(key, value));
      }
    }
  }
  
  get(name: string) {
    return super.get(name.toLowerCase()) || null;
  }
  
  set(name: string, value: string) {
    return super.set(name.toLowerCase(), value);
  }
  
  has(name: string) {
    return super.has(name.toLowerCase());
  }
  
  delete(name: string) {
    return super.delete(name.toLowerCase());
  }
};

// Basic fetch for nock compatibility
if (!global.fetch) {
  (global as any).fetch = jest.fn().mockResolvedValue(
    new (global as any).Response('{}', { status: 200 })
  );
}