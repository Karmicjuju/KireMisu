// Simple service worker for KireMisu
// This file prevents 404 errors for service worker requests

self.addEventListener('install', function(event) {
  // Skip waiting to activate immediately
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  // Claim clients to start handling requests immediately
  event.waitUntil(self.clients.claim());
});

// For now, just pass through all requests
self.addEventListener('fetch', function(event) {
  // Let the browser handle all requests normally
  return;
});